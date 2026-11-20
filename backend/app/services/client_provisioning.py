"""Delivery of customer invitations. Secrets are created only in the worker transaction."""

from datetime import datetime, timedelta
from app.services.email_templates import workspace_invitation
import secrets
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.security import get_password_hash
from app.core.passwords import invalidate_credentials
from app.db.models.user import User
from app.db.models.workspace import Workspace, WorkspaceMember
from app.db.models.client_admin import ClientInvitation
from app.db.models.activity_log import ActivityLog
from app.services.email_service import EmailService
from app.services.mfa_delivery import availability, smtp_send
from app.services.password_recovery import validate_configuration


async def deliver_invitation(db, invitation_id):
    invitation = db.get(ClientInvitation, invitation_id)
    if not invitation or invitation.status != "pending":
        return {"processed": True}
    # Lock order is always user first, then invitation, matching security mutations.
    user = (
        db.query(User)
        .filter_by(id=invitation.user_id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    invitation = (
        db.query(ClientInvitation)
        .filter_by(id=invitation_id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    if invitation.status != "pending":
        return {"processed": True}
    workspace = db.get(Workspace, invitation.workspace_id)
    if (
        not workspace
        or not user.is_active
        or not (user.is_whitelisted or user.is_superuser)
        or (
            workspace.owner_user_id != user.id
            and not db.query(WorkspaceMember.id)
            .filter_by(workspace_id=workspace.id, user_id=user.id)
            .first()
        )
    ):
        invitation.status, invitation.error_code = "failed", "ACCOUNT_UNAVAILABLE"
        db.commit()
        return {"processed": True}
    try:
        validate_configuration()
    except HTTPException:
        invitation.status, invitation.error_code = "failed", "EMAIL_NOT_CONFIGURED"
        db.commit()
        return {"processed": True}
    temporary = invitation.kind == "account_setup" and user.must_change_password
    password = "Aa1!" + secrets.token_urlsafe(24) if temporary else None
    login_url = settings.frontend_url.rstrip("/") + "/login"
    text = f"Votre espace Radar « {workspace.name} » est prêt.\nAdresse de connexion : {user.email}\nConnexion : {login_url}\n"
    if temporary:
        text += f"\nMot de passe temporaire : {password}\nIl expire dans 24 heures. À la première connexion, vous devrez choisir votre propre mot de passe avant d’accéder à votre espace. Vous pourrez ensuite configurer l’A2F ou une clé d’accès, ou choisir « Plus tard ».\n"
    else:
        text += "\nUtilisez vos identifiants Radar habituels ou votre fournisseur de connexion déjà associé. Votre mot de passe et votre A2F restent inchangés.\n"
    text += "\nNe transmettez pas ce message. Si vous n’attendiez pas cette invitation, contactez votre interlocuteur Radar."
    html = workspace_invitation(user.email, workspace.name, password)
    try:
        if settings.resend_api_key:
            result = await EmailService().send_email(
                user.email, "Votre invitation Radar", html, text
            )
            if not result.get("id"):
                raise RuntimeError("DELIVERY_REFUSED")
        else:
            await run_in_threadpool(
                smtp_send, user.email, text, "Votre invitation Radar", html
            )
    except Exception:
        invitation.status, invitation.error_code = "failed", "DELIVERY_FAILED"
        db.commit()
        return {"processed": True}
    now = datetime.utcnow()
    if temporary:
        user.hashed_password = get_password_hash(password)
        user.temporary_password_expires_at = now + timedelta(hours=24)
        invalidate_credentials(db, user)
        invitation.expires_at = user.temporary_password_expires_at
    invitation.status, invitation.sent_at, invitation.error_code = "sent", now, None
    db.add(
        ActivityLog(
            user_id=invitation.requested_by,
            user_tracking_id="SYSTEM",
            action="client.invitation_sent",
            resource_type="workspace",
            resource_id=str(workspace.id),
            details={
                "invitation_id": str(invitation.id),
                "user_id": user.id,
                "temporary": temporary,
            },
        )
    )
    db.commit()
    return {"processed": True}
