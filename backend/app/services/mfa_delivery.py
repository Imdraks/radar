"""Real transactional MFA delivery. No development-code fallback or provider bodies in errors."""

import smtplib
import ssl
from email.message import EmailMessage
import httpx
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.services.email_service import EmailService
from app.services.email_templates import mfa_code


def availability():
    return {
        "email": bool(
            settings.resend_api_key
            or (
                settings.smtp_host
                and settings.smtp_user
                and settings.smtp_password
                and (settings.smtp_use_tls or settings.smtp_port == 465)
            )
        ),
        "sms": bool(
            settings.mfa_sms_provider == "twilio"
            and settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ),
        "totp": True,
    }


def smtp_send(destination, body, subject="Votre code de sécurité Radar", html=None):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email or settings.smtp_user
    message["To"] = destination
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")
    if settings.smtp_port == 465:
        client = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
            context=ssl.create_default_context(),
        )
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    with client:
        if settings.smtp_port != 465:
            client.starttls(context=ssl.create_default_context())
        client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(message)


async def deliver(method, destination, code):
    if not availability().get(method):
        raise HTTPException(
            503,
            "Cette méthode d’envoi n’est pas configurée. Utilisez une autre méthode activée.",
        )
    body = f"Votre code Radar : {code}. Il expire dans 5 minutes au maximum. Ne le communiquez à personne. Si vous n’avez pas demandé ce code, ignorez ce message."
    try:
        if method == "email":
            html = mfa_code(code)
            if settings.resend_api_key:
                result = await EmailService().send_email(
                    destination, "Votre code de sécurité Radar", html, body
                )
                if not result.get("id"):
                    raise RuntimeError("Provider refused delivery")
            else:
                await run_in_threadpool(
                    smtp_send, destination, body, "Votre code de sécurité Radar", html
                )
        else:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                result = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                    data={
                        "To": destination,
                        "From": settings.twilio_from_number,
                        "Body": body,
                    },
                )
                if result.status_code != 201 or not result.json().get("sid"):
                    raise RuntimeError("Provider refused delivery")
    except Exception:
        # Do not disclose response bodies, phone numbers, provider auth or OTPs.
        raise HTTPException(
            503,
            "Le code n’a pas pu être envoyé. Réessayez plus tard ou utilisez une autre méthode.",
        ) from None
