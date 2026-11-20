"""Verified WebAuthn as an account second factor; no arbitrary public-key trust."""

from datetime import datetime, timedelta
import hashlib
import json
import secrets
from uuid import UUID
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers import options_to_json, base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
)
from app.api.deps import get_current_user, security
from app.db import get_db
from app.db.models.user import User
from app.db.models.passkey import PasskeyCredential, PasskeyChallenge
from app.core import mfa
from app.core.config import settings
from app.core.activity_logger import ActivityLogger
from app.core.login_sessions import (
    current_after_security_change,
    authorize_browser,
    set_trust_cookie,
)

router = APIRouter(prefix="/auth/passkeys", tags=["Passkeys"])


def relying_party():
    url = urlsplit(settings.frontend_url)
    if (
        not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
        or (
            url.scheme != "https"
            and not (
                settings.app_env != "production"
                and url.scheme == "http"
                and url.hostname == "localhost"
            )
        )
    ):
        raise HTTPException(
            503,
            "Les clés d’accès nécessitent une origine HTTPS Radar correctement configurée.",
        )
    return url.hostname, f"{url.scheme}://{url.netloc}"


class Enrollment(BaseModel):
    management_token: str = Field(min_length=32, max_length=128)


class Registration(BaseModel):
    challenge_id: UUID
    name: str = Field(min_length=2, max_length=80)
    credential: dict


class AuthStart(BaseModel):
    challenge_token: str = Field(min_length=32, max_length=128)


class AuthFinish(AuthStart):
    challenge_id: UUID
    credential: dict
    trust_device: bool = False


def new_ceremony(db, user, purpose, parent=None):
    now = datetime.utcnow()
    count = (
        db.query(PasskeyChallenge.id)
        .filter(
            PasskeyChallenge.user_id == user.id,
            PasskeyChallenge.created_at > now - timedelta(minutes=5),
        )
        .count()
    )
    if count >= 20:
        raise HTTPException(429, "Trop de demandes. Réessayez dans quelques minutes.")
    row = PasskeyChallenge(
        user_id=user.id,
        purpose=purpose,
        challenge=secrets.token_bytes(32),
        auth_version=user.mfa_version or 0,
        parent_token_hash=parent,
        expires_at=now + timedelta(minutes=5),
    )
    db.add(row)
    db.flush()
    return row


def ceremony(db, user, id, purpose, parent=None):
    row = (
        db.query(PasskeyChallenge)
        .filter_by(id=id, user_id=user.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if (
        not row
        or row.used_at
        or row.expires_at <= datetime.utcnow()
        or row.auth_version != (user.mfa_version or 0)
        or row.purpose != purpose
        or row.parent_token_hash != parent
    ):
        raise HTTPException(401, "Vérification expirée ou déjà utilisée. Recommencez.")
    return row


@router.get("")
def list_keys(user: User = Depends(get_current_user)):
    return [
        dict(
            id=str(k.id),
            name=k.name,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in user.passkeys
        if not k.revoked_at
    ]


@router.post("/register/options")
def registration_options(
    data: Enrollment,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rp, _ = relying_party()
    user, proof = mfa.load_challenge(
        db, data.management_token, {"manage_verified"}, user.id
    )
    if user.must_change_password:
        raise HTTPException(403, "Choisissez d’abord votre nouveau mot de passe.")
    if len([k for k in user.passkeys if not k.revoked_at]) >= 10:
        raise HTTPException(
            409, "Dix clés sont déjà enregistrées. Retirez une ancienne clé."
        )
    row = new_ceremony(db, user, "register")
    proof.used_at = datetime.utcnow()
    options = generate_registration_options(
        rp_id=rp,
        rp_name="Radar",
        user_id=str(user.id).encode(),
        user_name=user.email or str(user.id),
        user_display_name=user.full_name or user.email or "Radar",
        challenge=row.challenge,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.REQUIRED,
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=k.credential_id)
            for k in user.passkeys
            if not k.revoked_at
        ],
    )
    db.commit()
    return {
        "challenge_id": str(row.id),
        "publicKey": json.loads(options_to_json(options)),
    }


@router.post("/register/complete")
def registration_complete(
    data: Registration,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rp, origin = relying_party()
    user = mfa.lock_user(db, user.id)
    row = ceremony(db, user, data.challenge_id, "register")
    row.used_at = datetime.utcnow()
    try:
        result = verify_registration_response(
            credential=data.credential,
            expected_challenge=row.challenge,
            expected_rp_id=rp,
            expected_origin=origin,
            require_user_verification=True,
        )
    except Exception:
        db.commit()
        raise HTTPException(
            400, "La clé d’accès n’a pas pu être vérifiée. Recommencez son ajout."
        ) from None
    if (
        db.query(PasskeyCredential.id)
        .filter_by(credential_id=result.credential_id)
        .first()
    ):
        db.commit()
        raise HTTPException(409, "Cette clé est déjà enregistrée.")
    key = PasskeyCredential(
        credential_id=result.credential_id,
        public_key=result.credential_public_key,
        sign_count=result.sign_count,
        name=data.name.strip(),
    )
    user.passkeys.append(key)
    codes = mfa.new_recovery(user)
    user.mfa_version = (user.mfa_version or 0) + 1
    tokens = mfa.issue_tokens(
        user, session=current_after_security_change(db, user, request)
    )
    try:
        ActivityLogger.log(db, user, "passkey.registered", details={"name": key.name})
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cette clé est déjà enregistrée.") from None
    return {**tokens, "enabled": True, "backup_codes": codes}


def parent_challenge(db, token, credentials):
    user, parent = mfa.load_challenge(db, token, {"login", "manage"})
    if parent.purpose == "manage":
        authenticated = get_current_user(credentials=credentials, db=db)
        if authenticated.id != user.id:
            raise HTTPException(403, "Cette vérification appartient à un autre compte.")
    if "passkey" not in mfa.methods(user):
        raise HTTPException(409, "Aucune clé active pour ce compte.")
    return user, parent


@router.post("/authenticate/options")
def authentication_options(
    data: AuthStart,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    rp, _ = relying_party()
    user, parent = parent_challenge(db, data.challenge_token, credentials)
    row = new_ceremony(db, user, parent.purpose, parent.token_hash)
    options = generate_authentication_options(
        rp_id=rp,
        challenge=row.challenge,
        user_verification=UserVerificationRequirement.REQUIRED,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=k.credential_id)
            for k in user.passkeys
            if not k.revoked_at
        ],
    )
    db.commit()
    return {
        "challenge_id": str(row.id),
        "publicKey": json.loads(options_to_json(options)),
    }


@router.post("/authenticate/complete")
def authentication_complete(
    data: AuthFinish,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    rp, origin = relying_party()
    user, parent = parent_challenge(db, data.challenge_token, credentials)
    row = ceremony(db, user, data.challenge_id, parent.purpose, parent.token_hash)
    row.used_at = datetime.utcnow()
    try:
        raw_id = base64url_to_bytes(data.credential.get("id", ""))
        key = (
            db.query(PasskeyCredential)
            .filter_by(user_id=user.id, credential_id=raw_id, revoked_at=None)
            .with_for_update()
            .first()
        )
        if not key:
            raise ValueError("UNKNOWN_KEY")
        result = verify_authentication_response(
            credential=data.credential,
            expected_challenge=row.challenge,
            expected_rp_id=rp,
            expected_origin=origin,
            credential_public_key=key.public_key,
            credential_current_sign_count=key.sign_count,
            require_user_verification=True,
        )
    except Exception:
        mfa.reject(db, parent, "La clé d’accès n’a pas pu être vérifiée. Recommencez.")
    key.sign_count = result.new_sign_count
    key.last_used_at = datetime.utcnow()
    parent.used_at = datetime.utcnow()
    if parent.purpose == "manage":
        token, _ = mfa.create_challenge(db, user, "manage_verified")
        db.commit()
        return {"management_token": token}
    from app.api.auth import finish_login

    authorization = authorize_browser(db, user, request) if data.trust_device else None
    result = finish_login(db, user, request)
    if authorization:
        set_trust_cookie(response, authorization)
    return result


@router.post("/{key_id}/revoke")
def revoke_key(
    key_id: UUID,
    data: Enrollment,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user, proof = mfa.load_challenge(
        db, data.management_token, {"manage_verified"}, user.id
    )
    key = (
        db.query(PasskeyCredential)
        .filter_by(id=key_id, user_id=user.id, revoked_at=None)
        .first()
    )
    if not key:
        raise HTTPException(404, "Clé introuvable.")
    key.revoked_at = datetime.utcnow()
    proof.used_at = datetime.utcnow()
    if not mfa.methods(user):
        user.backup_codes = []
    user.mfa_version = (user.mfa_version or 0) + 1
    tokens = mfa.issue_tokens(
        user, session=current_after_security_change(db, user, request)
    )
    ActivityLogger.log(db, user, "passkey.revoked", details={"key_id": str(key.id)})
    return {**tokens, "revoked": True}
