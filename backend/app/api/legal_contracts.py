"""Publication requires a platform operator; acceptance never grants rights or confirms payment."""

import hashlib
import json
import re
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db, get_current_user, get_current_platform_admin
from app.api.subscription import get_workspace_for_user, is_workspace_admin
from app.api.privacy import PrivateJSONResponse
from app.core.config import settings
from app.db.models.legal_contract import LegalBundle, LegalAcceptance

router = APIRouter(
    prefix="/legal-contracts",
    tags=["Legal contracts"],
    default_response_class=PrivateJSONResponse,
)
DOCUMENT_KEYS = {
    "sales_terms",
    "dpa",
    "retention",
    "reversibility",
    "security",
    "subprocessors",
}


class Publisher(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=255)
    legal_form: str = Field(min_length=2, max_length=100)
    siret: str = Field(pattern=r"^\d{14}$")
    registration: str = Field(min_length=3, max_length=300)
    capital: str = Field(default="", max_length=100)
    vat_number: str = Field(default="", max_length=50)
    address: str = Field(min_length=5, max_length=500)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=50)
    publication_director: str = Field(min_length=2, max_length=255)
    hosting_name: str = Field(min_length=2, max_length=255)
    hosting_address: str = Field(min_length=5, max_length=500)
    hosting_contact: str = Field(min_length=5, max_length=255)


class PublishBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    publisher: Publisher
    documents: dict[str, str]
    review_reference: str = Field(min_length=5, max_length=300)
    reviewed_for_publication: Literal[True]


class AcceptBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    bundle_id: int = Field(gt=0)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    plan: Literal["core", "premium", "business"]
    commercial_reference: str = Field(min_length=3, max_length=200)
    accepted: Literal[True]
    authorized_representative: Literal[True]


def publisher_hash(publisher):
    return hashlib.sha256(
        json.dumps(
            publisher, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def bundle_hash(version, publisher, documents):
    raw = json.dumps(
        {"version": version, "publisher": publisher, "documents": documents},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def serialize(bundle):
    return {
        "id": bundle.id,
        "version": bundle.version,
        "content_hash": bundle.content_hash,
        "publisher": bundle.publisher,
        "documents": bundle.documents,
        "published_at": bundle.published_at,
    }


@router.get("/current")
def current_bundle(db: Session = Depends(get_db)):
    bundle = db.query(LegalBundle).order_by(LegalBundle.id.desc()).first()
    if not bundle:
        raise HTTPException(404, "Aucun dossier contractuel de production n’est publié")
    return serialize(bundle)


@router.get("/versions/{bundle_id}")
def get_version(bundle_id: int, db: Session = Depends(get_db)):
    bundle = db.get(LegalBundle, bundle_id)
    if not bundle:
        raise HTTPException(404, "Version introuvable")
    return serialize(bundle)


@router.post("/admin/publish", status_code=201)
def publish(
    data: PublishBundle,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_admin),
):
    if set(data.documents) != DOCUMENT_KEYS or any(
        not 100 <= len(text.strip()) <= 150000 for text in data.documents.values()
    ):
        raise HTTPException(
            422,
            "Six documents complets sont requis, de 100 à 150 000 caractères chacun",
        )
    if any(
        re.search(r"\[\[[^\]]+\]\]", text)
        for text in [*data.documents.values(), *data.publisher.model_dump().values()]
    ):
        raise HTTPException(422, "Remplacer les champs à compléter avant publication")
    db.execute(text("SELECT pg_advisory_xact_lock(724032661)"))
    publisher = data.publisher.model_dump(mode="json")
    if (
        publisher["legal_form"].strip().upper()
        in {"SAS", "SASU", "SARL", "EURL", "SA", "SCA", "SNC"}
        and not publisher["capital"]
    ):
        raise HTTPException(
            422, "Renseigner le capital social déclaré de cette société"
        )
    if not settings.legal_publisher_fingerprint:
        raise HTTPException(
            503,
            "Configurer l’identité publique vérifiée de l’éditeur avant publication",
        )
    if publisher_hash(publisher) != settings.legal_publisher_fingerprint:
        raise HTTPException(
            409,
            "L’identité proposée ne correspond pas à l’identité publique configurée",
        )
    documents = {key: text.strip() for key, text in data.documents.items()}
    digest = bundle_hash(data.version, publisher, documents)
    previous = db.query(LegalBundle).filter_by(version=data.version).first()
    if previous:
        if previous.content_hash != digest:
            raise HTTPException(
                409, "Une version publiée est immuable ; créer une nouvelle version"
            )
        return serialize(previous)
    bundle = LegalBundle(
        version=data.version,
        publisher=publisher,
        documents=documents,
        content_hash=digest,
        review_reference=data.review_reference,
        published_by=admin.id,
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return serialize(bundle)


def require_workspace_admin(db, user, workspace_id):
    workspace = get_workspace_for_user(db, user, workspace_id)
    if not is_workspace_admin(db, user, workspace):
        raise HTTPException(403, "Administrateur de cet espace requis")
    return workspace


@router.post("/acceptances", status_code=201)
def accept(
    data: AcceptBundle,
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    workspace = require_workspace_admin(db, user, workspace_id)
    # Publication and acceptance share a transaction lock to avoid stale-version races.
    db.execute(text("SELECT pg_advisory_xact_lock(724032661)"))
    bundle = (
        db.query(LegalBundle)
        .filter_by(id=data.bundle_id)
        .with_for_update(read=True)
        .first()
    )
    latest = db.query(LegalBundle.id).order_by(LegalBundle.id.desc()).first()
    if (
        not bundle
        or not latest
        or bundle.id != latest.id
        or data.content_hash != bundle.content_hash
    ):
        raise HTTPException(
            409,
            "Les documents ont changé ; consulter la version publiée avant acceptation",
        )
    existing = (
        db.query(LegalAcceptance)
        .filter_by(
            workspace_id=workspace.id,
            bundle_id=bundle.id,
            plan=data.plan,
            commercial_reference=data.commercial_reference,
        )
        .first()
    )
    if not existing:
        existing = LegalAcceptance(
            workspace_id=workspace.id,
            bundle_id=bundle.id,
            accepted_by=user.id,
            representative={
                "email": user.email,
                "name": user.full_name,
                "authority_declared": True,
            },
            workspace_name=workspace.name,
            plan=data.plan,
            commercial_reference=data.commercial_reference,
            content_hash=bundle.content_hash,
            accepted_at=datetime.utcnow(),
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return {
        "id": existing.id,
        "bundle_id": existing.bundle_id,
        "content_hash": existing.content_hash,
        "plan": existing.plan,
        "commercial_reference": existing.commercial_reference,
        "accepted_at": existing.accepted_at,
        "rights_activated": False,
        "payment_confirmed": False,
    }


@router.get("/acceptances")
def list_acceptances(
    workspace_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    workspace = require_workspace_admin(db, user, workspace_id)
    return [
        {
            "id": row.id,
            "bundle_id": row.bundle_id,
            "content_hash": row.content_hash,
            "plan": row.plan,
            "commercial_reference": row.commercial_reference,
            "accepted_at": row.accepted_at,
        }
        for row in db.query(LegalAcceptance)
        .filter_by(workspace_id=workspace.id)
        .order_by(LegalAcceptance.id.desc())
        .limit(100)
    ]


@router.get("/admin/acceptances")
def operator_acceptances(
    workspace_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_admin),
):
    return [
        {
            "id": row.id,
            "bundle_id": row.bundle_id,
            "content_hash": row.content_hash,
            "plan": row.plan,
            "commercial_reference": row.commercial_reference,
            "accepted_at": row.accepted_at,
            "representative": row.representative,
        }
        for row in db.query(LegalAcceptance)
        .filter_by(workspace_id=workspace_id)
        .order_by(LegalAcceptance.id.desc())
        .limit(100)
    ]
