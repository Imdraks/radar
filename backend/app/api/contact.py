"""
Public contact form endpoint (no auth required)
"""

from html import escape
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Literal
from app.services.email_service import EmailService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])


CONTACT_NOTICE_VERSION = "2026-11-13"


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=150, pattern=r"^[^\r\n]+$")
    email: EmailStr
    company: str = Field(default="", max_length=200, pattern=r"^[^\r\n]*$")
    phone: str = Field(default="", max_length=40, pattern=r"^[^\r\n]*$")
    plan: Literal["", "core", "premium", "business", "custom"] = ""
    message: str = Field(min_length=5, max_length=5000)
    privacy_notice_version: Literal["2026-11-13"]


@router.post("")
async def submit_contact(data: ContactRequest):
    """Receive a contact form submission and send notification email."""
    email_service = EmailService()
    if not settings.contact_receiver_email or not email_service.is_configured:
        raise HTTPException(
            503,
            "Le canal de contact n’est pas configuré. Utilisez le contact publié dans les mentions légales.",
        )

    # Escape all user inputs for safe HTML rendering
    safe_name = escape(data.name)
    safe_email = escape(data.email)
    safe_company = escape(data.company) if data.company else "—"
    safe_phone = escape(data.phone) if data.phone else "—"
    safe_plan = escape(data.plan) if data.plan else "—"
    safe_message = escape(data.message)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #7c3aed;">Nouveau message de contact — Radar</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px; font-weight: bold; color: #374151;">Nom</td><td style="padding: 8px;">{safe_name}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #374151;">Email</td><td style="padding: 8px;">{safe_email}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #374151;">Société</td><td style="padding: 8px;">{safe_company}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #374151;">Téléphone</td><td style="padding: 8px;">{safe_phone}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #374151;">Pack intéressé</td><td style="padding: 8px;">{safe_plan}</td></tr>
        </table>
        <div style="margin-top: 16px; padding: 16px; background: #f3f4f6; border-radius: 8px;">
            <p style="font-weight: bold; color: #374151; margin: 0 0 8px;">Message :</p>
            <p style="color: #4b5563; margin: 0; white-space: pre-wrap;">{safe_message}</p>
        </div>
    </div>
    """

    result = await email_service.send_email(
        to=settings.contact_receiver_email,
        subject=f"[Radar Contact] {data.name} — {data.company or 'Contact professionnel'}",
        html=html,
        text=f"Nom: {data.name}\nEmail: {data.email}\nSociété: {data.company}\nTéléphone: {data.phone}\nPack: {data.plan}\n\nMessage:\n{data.message}\nNotice présentée : {data.privacy_notice_version}",
    )

    if result.get("error") or not result.get("id"):
        logger.error(
            "Contact delivery failed; no message body or provider response logged"
        )
        raise HTTPException(status_code=500, detail="Erreur lors de l'envoi du message")

    logger.info(
        "Contact form delivered; notice_version=%s", data.privacy_notice_version
    )
    return {"status": "ok", "message": "Message envoyé avec succès"}
