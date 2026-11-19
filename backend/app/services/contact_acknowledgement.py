"""Send one opening acknowledgement; do not infer payment or order acceptance."""

from datetime import datetime
from html import escape
from starlette.concurrency import run_in_threadpool
from app.db.models.contact_inquiry import ContactInquiry
from app.services.email_service import EmailService
from app.services.mfa_delivery import availability, smtp_send


async def deliver_open_acknowledgement(db, id):
    row = (
        db.query(ContactInquiry)
        .filter_by(id=id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not row or not row.opened_at or row.acknowledgement_status != "pending":
        return {"processed": True}
    service = EmailService()
    if not availability()["email"]:
        row.acknowledgement_status = "failed"
        row.acknowledgement_error = "EMAIL_NOT_CONFIGURED"
        db.commit()
        return {"processed": True}
    # Claim before contacting the provider: duplicate job delivery never sends twice.
    row.acknowledgement_status = "processing"
    db.commit()
    subject = "Votre demande Radar a été ouverte"
    text = f"Bonjour {row.name},\n\nVotre demande a bien été ouverte par notre équipe. Nous vous contacterons prochainement pour la traiter.\n\nL’équipe Radar\nRéférence : {row.id}"
    html = "<p>" + escape(text).replace("\n", "<br>") + "</p>"
    try:
        if service.is_configured:
            result = await service.send_email(
                row.email,
                subject,
                html,
                text,
                idempotency_key="radar-contact-open-" + str(row.id),
            )
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("id"), str)
                or not result["id"]
            ):
                raise RuntimeError("DELIVERY_REFUSED")
        else:
            await run_in_threadpool(smtp_send, row.email, text, subject)
    except Exception:
        row.acknowledgement_status = "failed"
        row.acknowledgement_error = "DELIVERY_FAILED"
        db.commit()
        return {"processed": True}
    row.acknowledgement_status = "sent"
    row.acknowledgement_sent_at = datetime.utcnow()
    row.acknowledgement_error = None
    db.commit()
    return {"processed": True}
