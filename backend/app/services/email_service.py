"""
Email Service using Resend API
https://resend.com/docs/api-reference/emails/send-email
"""

import httpx
from typing import Optional, List
from app.core.config import settings


class EmailService:
    """Service for sending emails via Resend API"""

    BASE_URL = "https://api.resend.com"

    def __init__(self):
        self.api_key = settings.resend_api_key
        self.from_email = settings.resend_from_email
        self.frontend_url = settings.frontend_url

    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.api_key)

    async def send_email(
        self,
        to: str | List[str],
        subject: str,
        html: str,
        text: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Send an email via Resend API

        Args:
            to: Recipient email(s)
            subject: Email subject
            html: HTML content
            text: Plain text content (optional)

        Returns:
            API response dict with 'id' on success
        """
        if not self.is_configured:
            return {"error": "Email service not configured", "id": None}

        payload = {
            "from": self.from_email,
            "to": [to] if isinstance(to, str) else to,
            "subject": subject,
            "html": html,
        }

        if text:
            payload["text"] = text

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/emails",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": response.text,
                    "status_code": response.status_code,
                    "id": None,
                }

    async def send_workspace_invite(
        self,
        to_email: str,
        workspace_name: str,
        inviter_name: Optional[str] = None,
        role: str = "member",
    ) -> dict:
        """
        Send a workspace invitation email

        Args:
            to_email: Recipient email
            workspace_name: Name of the workspace
            inviter_name: Name of person who sent the invite
            role: Role being granted (member, admin, etc.)
        """
        inviter_text = f" par {inviter_name}" if inviter_name else ""
        login_url = f"{self.frontend_url}/login"

        subject = f"Invitation à rejoindre {workspace_name} sur Radar"

        from app.services.email_templates import workspace_invite

        html = workspace_invite(to_email, workspace_name, inviter_name, role)

        text = f"""
Vous êtes invité(e) à rejoindre {workspace_name} sur Radar !

Vous avez été invité(e){inviter_text} à rejoindre le workspace "{workspace_name}".
Rôle assigné : {role.capitalize()}

Connectez-vous sur {login_url} avec votre méthode de connexion habituelle en utilisant l'adresse {to_email}.

---
Radar - Votre cockpit d'opportunités
{self.frontend_url}
"""

        return await self.send_email(
            to=to_email,
            subject=subject,
            html=html,
            text=text,
        )


# Singleton instance
email_service = EmailService()
