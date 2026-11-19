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
        
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
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
        
        subject = f"🎯 Invitation à rejoindre {workspace_name} sur Radar"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; margin: 0;">🎯 Radar</h1>
    </div>
    
    <div style="background: #f8fafc; border-radius: 12px; padding: 30px; margin-bottom: 20px;">
        <h2 style="margin-top: 0; color: #1e293b;">Vous êtes invité(e) !</h2>
        
        <p style="font-size: 16px;">
            Vous avez été invité(e){inviter_text} à rejoindre le workspace 
            <strong style="color: #2563eb;">{workspace_name}</strong> sur Radar.
        </p>
        
        <p style="font-size: 14px; color: #64748b;">
            Rôle assigné : <strong>{role.capitalize()}</strong>
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{login_url}" 
               style="display: inline-block; background: #2563eb; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                Accepter l'invitation
            </a>
        </div>
        
        <p style="font-size: 14px; color: #64748b; margin-bottom: 0;">
            Connectez-vous avec Google en utilisant l'adresse <strong>{to_email}</strong>
        </p>
    </div>
    
    <div style="text-align: center; font-size: 12px; color: #94a3b8;">
        <p>
            Radar - Votre cockpit d'opportunités<br>
            <a href="{self.frontend_url}" style="color: #2563eb;">{self.frontend_url}</a>
        </p>
    </div>
</body>
</html>
"""
        
        text = f"""
Vous êtes invité(e) à rejoindre {workspace_name} sur Radar !

Vous avez été invité(e){inviter_text} à rejoindre le workspace "{workspace_name}".
Rôle assigné : {role.capitalize()}

Connectez-vous sur {login_url} avec Google en utilisant l'adresse {to_email}.

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
