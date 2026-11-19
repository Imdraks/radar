"""Customer-company administration. All endpoints require the explicit platform superuser flag."""

from datetime import datetime
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import func, or_, case, and_, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_current_platform_admin
from app.db import get_db
from app.db.models.user import User, Role
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.db.models.client_admin import ClientInvitation
from app.db.models.activity_log import ActivityLog
from app.db.models.subscription_request import SubscriptionRequest
from app.db.models.legal_contract import LegalAcceptance, LegalBundle
from app.core.subscription import Plan, PLAN_CONFIGS, resolve_plan
from app.api.subscription import serialize_subscription
from app.services.password_recovery import validate_configuration

router = APIRouter(prefix="/admin/clients", tags=["Platform clients"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateClient(Input):
    name: str = Field(min_length=2, max_length=255)
    owner_email: EmailStr
    owner_name: str = Field(min_length=2, max_length=100)


class EditClient(Input):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    legal_address: str | None = Field(default=None, max_length=500)
    legal_city: str | None = Field(default=None, max_length=100)
    legal_postal_code: str | None = Field(default=None, max_length=20)
    legal_country: str | None = Field(default=None, max_length=100)
    legal_phone: str | None = Field(default=None, max_length=50)
    billing_email: EmailStr | None = None
    siret: str | None = Field(default=None, max_length=20)
    vat_number: str | None = Field(default=None, max_length=30)

    @field_validator("billing_email", mode="before")
    @classmethod
    def blank_email(cls, value):
        return None if value == "" else value


class SuspendClient(Input):
    suspended: bool
    reason: str = Field(min_length=5, max_length=1000)


class AddPerson(Input):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    role: Literal["admin", "member", "viewer"] = "member"


class MemberRoleInput(Input):
    role: Literal["admin", "member", "viewer"]


class OwnerInput(Input):
    user_id: int = Field(gt=0)


class CreateOrder(Input):
    kind: Literal["plan", "addon"]
    value: str = Field(min_length=2, max_length=100)


class CapacityInput(Input):
    max_seats: int = Field(gt=0, le=100000)
    authorization_reference: str = Field(min_length=5, max_length=1000)


def company(db, workspace_id, lock=False):
    q = db.query(Workspace).filter_by(id=workspace_id)
    row = (q.with_for_update() if lock else q).first()
    if not row:
        raise HTTPException(404, "Entreprise cliente introuvable.")
    return row


def log(db, admin, workspace_id, action, details=None):
    db.add(
        ActivityLog(
            user_id=admin.id,
            user_tracking_id=admin.tracking_id or "SYSTEM",
            action=action,
            resource_type="workspace",
            resource_id=str(workspace_id),
            details=details or {},
        )
    )


def invite_dict(row):
    return {
        "id": str(row.id),
        "user_id": row.user_id,
        "kind": row.kind,
        "status": row.status,
        "created_at": row.created_at,
        "sent_at": row.sent_at,
        "expires_at": row.expires_at,
        "error_code": row.error_code,
    }


def enqueue(db, row):
    from app.workers.client_tasks import send_client_invitation

    try:
        send_client_invitation.delay(str(row.id))
    except Exception:
        row.status, row.error_code = "failed", "QUEUE_UNAVAILABLE"
        db.commit()
    return invite_dict(row)


def invitation(db, admin, ws, user):
    # Resending never resets a configured existing account or disables its MFA.
    db.query(ClientInvitation).filter_by(
        workspace_id=ws.id, user_id=user.id, status="pending"
    ).update({"status": "superseded"}, synchronize_session=False)
    row = ClientInvitation(
        workspace_id=ws.id,
        user_id=user.id,
        requested_by=admin.id,
        kind="account_setup" if user.must_change_password else "workspace_access",
        status="pending",
    )
    db.add(row)
    db.flush()
    log(
        db,
        admin,
        ws.id,
        "client.invitation_requested",
        {"invitation_id": str(row.id), "user_id": user.id},
    )
    return row


def person(db, email, name):
    user = (
        db.query(User)
        .filter(func.lower(User.email) == email.lower())
        .with_for_update()
        .first()
    )
    if user:
        if not user.is_active:
            raise HTTPException(
                409,
                "Ce compte est inactif. Traitez sa situation dans la gestion des utilisateurs.",
            )
        user.is_whitelisted = True
        return user
    user = User(
        email=email.lower(),
        full_name=name,
        role=Role.VIEWER,
        is_active=True,
        is_whitelisted=True,
        auth_provider="credentials",
        must_change_password=True,
        security_setup_pending=True,
    )
    db.add(user)
    db.flush()
    return user


def summary(ws, owner, seats, pending=0):
    plan = resolve_plan(ws.plan, ws.enabled_packs, ws.addons)
    return {
        "id": ws.id,
        "name": ws.name,
        "owner_user_id": ws.owner_user_id,
        "owner_name": owner.full_name if owner else None,
        "owner_email": owner.email if owner else None,
        "owner_last_login_at": owner.last_login_at if owner else None,
        "plan": plan.value,
        "plan_display_name": PLAN_CONFIGS[plan].display_name,
        "max_seats": ws.max_seats,
        "current_seats": int(seats),
        "is_suspended": ws.is_suspended,
        "suspended_at": ws.suspended_at,
        "suspension_reason": ws.suspension_reason,
        "pending_orders": int(pending),
        "plan_expires_at": ws.plan_expires_at,
        "created_at": ws.created_at,
    }


@router.get("")
def list_clients(
    q: str = Query("", max_length=100),
    state: Literal["all", "active", "suspended"] = "all",
    plan: Plan | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    # Aggregate counts once, rather than two extra SQL queries per client.
    counts = (
        db.query(
            WorkspaceMember.workspace_id, func.count(WorkspaceMember.id).label("n")
        )
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .filter(WorkspaceMember.user_id != Workspace.owner_user_id)
        .group_by(WorkspaceMember.workspace_id)
        .subquery()
    )
    requests = (
        db.query(
            SubscriptionRequest.workspace_id,
            func.count(SubscriptionRequest.id).label("n"),
        )
        .filter(SubscriptionRequest.status == "pending")
        .group_by(SubscriptionRequest.workspace_id)
        .subquery()
    )
    rows = (
        db.query(
            Workspace,
            User,
            (func.coalesce(counts.c.n, 0) + 1).label("seats"),
            func.coalesce(requests.c.n, 0).label("pending"),
        )
        .outerjoin(User, User.id == Workspace.owner_user_id)
        .outerjoin(counts, counts.c.workspace_id == Workspace.id)
        .outerjoin(requests, requests.c.workspace_id == Workspace.id)
    )
    if q.strip():
        needle = (
            "%"
            + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        rows = rows.filter(
            or_(
                Workspace.name.ilike(needle, escape="\\"),
                User.email.ilike(needle, escape="\\"),
                User.full_name.ilike(needle, escape="\\"),
            )
        )
    if state != "all":
        rows = rows.filter(Workspace.is_suspended == (state == "suspended"))
    if plan:
        # Same legacy compatibility as resolve_plan, expressed in SQL for pagination.
        legacy_business = and_(
            Workspace.plan.in_(["mini", "standard"]),
            or_(
                cast(Workspace.enabled_packs, JSONB).contains(["clients"]),
                cast(Workspace.enabled_packs, JSONB).contains(["leads"]),
                cast(Workspace.addons, JSONB).contains(["radar_business"]),
            ),
        )
        normalized = case(
            (or_(Workspace.plan == "business", legacy_business), "business"),
            (Workspace.plan.in_(["premium", "standard"]), "premium"),
            else_="core",
        )
        rows = rows.filter(normalized == plan.value)
    total = rows.count()
    items = (
        rows.order_by(Workspace.created_at.desc(), Workspace.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            summary(ws, owner, seats, pending) for ws, owner, seats, pending in items
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/orders")
def list_orders(
    status: Literal[
        "all", "pending", "approved", "rejected", "commercial_approved"
    ] = "pending",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    rows = db.query(SubscriptionRequest, Workspace.name).join(
        Workspace, Workspace.id == SubscriptionRequest.workspace_id
    )
    if status != "all":
        rows = rows.filter(SubscriptionRequest.status == status)
    total = rows.count()
    return {
        "items": [
            dict(
                id=r.id,
                workspace_id=r.workspace_id,
                workspace_name=name,
                kind=r.kind,
                value=r.requested_value,
                status=r.status,
                created_at=r.created_at,
            )
            for r, name in rows.order_by(SubscriptionRequest.id.desc())
            .offset((page - 1) * 25)
            .limit(25)
        ],
        "total": total,
        "page": page,
    }


@router.post("", status_code=201)
def create_client(
    data: CreateClient,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    validate_configuration()
    try:
        owner = person(db, str(data.owner_email), data.owner_name)
        ws = Workspace(name=data.name, owner_user_id=owner.id)
        db.add(ws)
        db.flush()
        row = invitation(db, admin, ws, owner)
        log(db, admin, ws.id, "client.created", {"name": ws.name, "owner_id": owner.id})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Un compte ou une invitation a changé. Rechargez puis réessayez."
        ) from None
    return {"id": ws.id, "name": ws.name, "invitation": enqueue(db, row)}


@router.get("/{workspace_id}")
def get_client(
    workspace_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id)
    owner = db.get(User, ws.owner_user_id)
    members = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id != ws.owner_user_id,
        )
        .order_by(User.full_name, User.id)
        .all()
    )
    orders = (
        db.query(SubscriptionRequest)
        .filter_by(workspace_id=ws.id)
        .order_by(SubscriptionRequest.id.desc())
        .limit(100)
        .all()
    )
    accepts = (
        db.query(LegalAcceptance, LegalBundle.version)
        .join(LegalBundle, LegalBundle.id == LegalAcceptance.bundle_id)
        .filter(LegalAcceptance.workspace_id == ws.id)
        .order_by(LegalAcceptance.id.desc())
        .limit(100)
        .all()
    )
    invites = (
        db.query(ClientInvitation)
        .filter_by(workspace_id=ws.id)
        .order_by(ClientInvitation.created_at.desc())
        .limit(100)
        .all()
    )
    history = (
        db.query(ActivityLog, User.full_name)
        .outerjoin(User, User.id == ActivityLog.user_id)
        .filter(
            ActivityLog.resource_type == "workspace",
            ActivityLog.resource_id == str(ws.id),
        )
        .order_by(ActivityLog.created_at.desc())
        .limit(100)
        .all()
    )
    from app.db.models.platform_sales import PlatformQuote, ExternalClientContract
    from app.api.platform_sales import serialize_quote, serialize_contract

    quotes = (
        db.query(PlatformQuote)
        .filter_by(workspace_id=ws.id)
        .order_by(PlatformQuote.id.desc())
        .limit(100)
        .all()
    )
    contracts = (
        db.query(ExternalClientContract)
        .filter_by(workspace_id=ws.id)
        .order_by(ExternalClientContract.id.desc())
        .limit(100)
        .all()
    )
    return {
        "quotes": [serialize_quote(r) for r in quotes],
        "external_contracts": [serialize_contract(r) for r in contracts],
        "integrations": {"drive_url": ws.drive_url, "calendar_id": ws.calendar_id},
        **summary(
            ws,
            owner,
            len(members) + 1,
            len([r for r in orders if r.status == "pending"]),
        ),
        "company": {k: getattr(ws, k) for k in EditClient.model_fields},
        "subscription": serialize_subscription(db, ws),
        "owner": (
            {
                "user_id": owner.id,
                "name": owner.full_name,
                "email": owner.email,
                "must_change_password": owner.must_change_password,
                "is_active": owner.is_active,
            }
            if owner
            else None
        ),
        "members": [
            dict(
                id=m.id,
                user_id=u.id,
                name=u.full_name,
                email=u.email,
                role=m.role.value,
                last_login_at=u.last_login_at,
                must_change_password=u.must_change_password,
                is_active=u.is_active,
            )
            for m, u in members
        ],
        "invitations": [invite_dict(r) for r in invites],
        "orders": [
            dict(
                id=r.id,
                kind=r.kind,
                value=r.requested_value,
                status=r.status,
                created_at=r.created_at,
                decided_at=r.decided_at,
                authorization_reference=r.authorization_reference,
                contract_acceptance_id=r.contract_acceptance_id,
                external_contract_id=r.external_contract_id,
            )
            for r in orders
        ],
        "acceptances": [
            dict(
                id=a.id,
                bundle_id=a.bundle_id,
                version=v,
                plan=a.plan,
                reference=a.commercial_reference,
                accepted_at=a.accepted_at,
                representative=a.representative,
                content_hash=a.content_hash,
            )
            for a, v in accepts
        ],
        "history": [
            dict(
                id=str(h.id),
                action=h.action,
                created_at=h.created_at,
                actor=name,
                details=h.details,
            )
            for h, name in history
        ],
    }


@router.patch("/{workspace_id}")
def edit_client(
    workspace_id: int,
    data: EditClient,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(ws, key, value)
    log(db, admin, ws.id, "client.updated", {"fields": list(data.model_fields_set)})
    db.commit()
    return {"updated": True}


@router.post("/{workspace_id}/suspension")
def suspend(
    workspace_id: int,
    data: SuspendClient,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    if ws.is_suspended != data.suspended:
        ws.is_suspended = data.suspended
        ws.suspended_at = datetime.utcnow() if data.suspended else None
        ws.suspended_by = admin.id if data.suspended else None
        ws.suspension_reason = data.reason if data.suspended else None
        log(
            db,
            admin,
            ws.id,
            "client.suspended" if data.suspended else "client.reactivated",
            {"reason": data.reason},
        )
        db.commit()
    return {"is_suspended": ws.is_suspended}


@router.post("/{workspace_id}/members", status_code=201)
def add_person(
    workspace_id: int,
    data: AddPerson,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    validate_configuration()
    ws = company(db, workspace_id, True)
    from app.api.workspace import ensure_seat_available

    user = person(db, str(data.email), data.full_name)
    if (
        user.id == ws.owner_user_id
        or db.query(WorkspaceMember)
        .filter_by(workspace_id=ws.id, user_id=user.id)
        .first()
    ):
        raise HTTPException(409, "Cette personne appartient déjà à cet espace.")
    ensure_seat_available(db, ws.id, user.id)
    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=user.id,
            role=WorkspaceRole(data.role),
            invited_by=admin.id,
        )
    )
    row = invitation(db, admin, ws, user)
    log(
        db, admin, ws.id, "client.member_added", {"user_id": user.id, "role": data.role}
    )
    db.commit()
    return {"user_id": user.id, "invitation": enqueue(db, row)}


@router.patch("/{workspace_id}/members/{member_id}")
def edit_person(
    workspace_id: int,
    member_id: int,
    data: MemberRoleInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    member = (
        db.query(WorkspaceMember).filter_by(id=member_id, workspace_id=ws.id).first()
    )
    if not member or member.user_id == ws.owner_user_id:
        raise HTTPException(404, "Membre modifiable introuvable.")
    member.role = WorkspaceRole(data.role)
    log(
        db,
        admin,
        ws.id,
        "client.member_role_changed",
        {"user_id": member.user_id, "role": data.role},
    )
    db.commit()
    return {"updated": True}


@router.delete("/{workspace_id}/members/{member_id}")
def remove_person(
    workspace_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    member = (
        db.query(WorkspaceMember).filter_by(id=member_id, workspace_id=ws.id).first()
    )
    if not member or member.user_id == ws.owner_user_id:
        raise HTTPException(404, "Membre retirable introuvable.")
    user_id = member.user_id
    db.query(ClientInvitation).filter_by(
        workspace_id=ws.id, user_id=user_id, status="pending"
    ).update({"status": "cancelled"}, synchronize_session=False)
    db.delete(member)
    log(db, admin, ws.id, "client.member_removed", {"user_id": user_id})
    db.commit()
    return {"removed": True}


@router.post("/{workspace_id}/invitations/{user_id}/resend", status_code=202)
def resend(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    validate_configuration()
    ws = company(db, workspace_id, True)
    user = db.get(User, user_id)
    if (
        not user
        or not user.is_active
        or not (user.is_whitelisted or user.is_superuser)
        or (
            user.id != ws.owner_user_id
            and not db.query(WorkspaceMember.id)
            .filter_by(workspace_id=ws.id, user_id=user.id)
            .first()
        )
    ):
        raise HTTPException(404, "Destinataire introuvable dans cet espace.")
    latest = (
        db.query(ClientInvitation)
        .filter_by(workspace_id=ws.id, user_id=user.id)
        .order_by(ClientInvitation.created_at.desc())
        .first()
    )
    if latest and (datetime.utcnow() - latest.created_at).total_seconds() < 60:
        raise HTTPException(
            429, "Attendez une minute avant de renvoyer une invitation."
        )
    row = invitation(db, admin, ws, user)
    db.commit()
    return enqueue(db, row)


@router.post("/{workspace_id}/owner")
def transfer_owner(
    workspace_id: int,
    data: OwnerInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    target = (
        db.query(WorkspaceMember)
        .filter_by(workspace_id=ws.id, user_id=data.user_id)
        .first()
    )
    user = db.get(User, data.user_id)
    if not target or not user or not user.is_active:
        raise HTTPException(409, "Choisissez un membre actif de cet espace.")
    previous = ws.owner_user_id
    if (
        not db.query(WorkspaceMember.id)
        .filter_by(workspace_id=ws.id, user_id=previous)
        .first()
    ):
        db.add(
            WorkspaceMember(
                workspace_id=ws.id,
                user_id=previous,
                role=WorkspaceRole.ADMIN,
                invited_by=admin.id,
            )
        )
    ws.owner_user_id = user.id
    db.delete(target)
    log(
        db,
        admin,
        ws.id,
        "client.owner_transferred",
        {"previous_owner_id": previous, "owner_id": user.id},
    )
    db.commit()
    return {"owner_user_id": ws.owner_user_id}


@router.post("/{workspace_id}/capacity")
def capacity(
    workspace_id: int,
    data: CapacityInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    count = (
        db.query(func.count(WorkspaceMember.id))
        .filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id != ws.owner_user_id,
        )
        .scalar()
        + 1
    )
    if data.max_seats < count:
        raise HTTPException(
            409,
            "La limite ne peut pas être inférieure au nombre de personnes déjà présentes.",
        )
    ws.max_seats = data.max_seats
    log(
        db,
        admin,
        ws.id,
        "client.capacity_authorized",
        {
            "max_seats": data.max_seats,
            "authorization_reference": data.authorization_reference,
        },
    )
    db.commit()
    return {"max_seats": ws.max_seats}


@router.post("/{workspace_id}/orders", status_code=201)
def create_order(
    workspace_id: int,
    data: CreateOrder,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    if data.kind == "plan" and data.value not in {p.value for p in Plan}:
        raise HTTPException(422, "Offre inconnue.")
    if (
        db.query(SubscriptionRequest.id)
        .filter_by(
            workspace_id=ws.id,
            kind=data.kind,
            requested_value=data.value,
            status="pending",
        )
        .first()
    ):
        raise HTTPException(409, "Une demande identique est déjà en attente.")
    row = SubscriptionRequest(
        workspace_id=ws.id,
        requested_by=admin.id,
        kind=data.kind,
        requested_value=data.value,
        status="pending",
    )
    db.add(row)
    db.flush()
    log(
        db,
        admin,
        ws.id,
        "client.order_created",
        {"request_id": row.id, "kind": data.kind, "value": data.value},
    )
    db.commit()
    return {
        "id": row.id,
        "status": row.status,
        "rights_activated": False,
        "payment_confirmed": False,
    }


@router.post("/{workspace_id}/users/{user_id}/password-reset-email", status_code=202)
def reset_by_email(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    validate_configuration()
    ws = company(db, workspace_id)
    user = db.get(User, user_id)
    if not user or (
        user.id != ws.owner_user_id
        and not db.query(WorkspaceMember.id)
        .filter_by(workspace_id=ws.id, user_id=user.id)
        .first()
    ):
        raise HTTPException(404, "Utilisateur introuvable dans cet espace.")
    if not user.is_active or not (user.is_whitelisted or user.is_superuser):
        raise HTTPException(
            409,
            "Ce compte ne peut pas recevoir une demande de récupération dans son état actuel.",
        )
    if user.must_change_password:
        raise HTTPException(
            409,
            "Renvoyez l’invitation pour fournir un nouveau mot de passe temporaire.",
        )
    from app.workers.password_tasks import request_password_reset

    try:
        request_password_reset.delay(user.email)
    except Exception:
        raise HTTPException(
            503, "La demande n’a pas pu être transmise au service d’envoi."
        ) from None
    log(db, admin, ws.id, "client.password_reset_email_requested", {"user_id": user.id})
    db.commit()
    return {
        "queued": True,
        "message": "Demande de récupération transmise au service d’envoi. Aucun mot de passe existant n’a été modifié.",
    }
