"""Transactional recovery mail using the same configured providers as Radar MFA."""

from app.services.email_templates import password_reset
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.services.email_service import EmailService
from app.services.mfa_delivery import availability, smtp_send


async def send_reset_link(email, url):
    if not availability()["email"]:
        raise HTTPException(503, "L’envoi des e-mails de sécurité n’est pas configuré.")
    subject = "Réinitialiser votre mot de passe Radar"
    text = f"Pour choisir un nouveau mot de passe Radar, ouvrez ce lien :\n{url}\n\nCe lien expire dans 15 minutes et ne fonctionne qu’une fois. Si vous n’avez pas demandé cette opération, ignorez cet e-mail. Votre A2F reste active."
    html = password_reset(url)
    try:
        if settings.resend_api_key:
            result = await EmailService().send_email(email, subject, html, text)
            if not result.get("id"):
                raise RuntimeError("Delivery refused")
        else:
            await run_in_threadpool(smtp_send, email, text, subject, html)
    except Exception:
        raise HTTPException(
            503, "Le service d’envoi est temporairement indisponible."
        ) from None
