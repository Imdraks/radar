"""
Notification handlers for Discord, Slack, and Email
"""
import json
import logging
from typing import List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

from app.core.config import settings
from app.db.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


def format_opportunity_message(opp: Opportunity) -> dict:
    """Format opportunity for notification"""
    deadline_str = ""
    if opp.deadline_at:
        from datetime import datetime
        days_remaining = (opp.deadline_at - datetime.utcnow()).days
        deadline_str = f" | ⏰ Deadline: {opp.deadline_at.strftime('%d/%m/%Y')} ({days_remaining}j)"
    
    budget_str = ""
    if opp.budget_amount:
        budget_str = f" | 💰 {opp.budget_amount:,.0f} €"
    
    return {
        "title": opp.title[:100],
        "score": opp.score,
        "category": opp.category.value,
        "organization": opp.organization or "N/A",
        "deadline": deadline_str,
        "budget": budget_str,
        "url": opp.url_primary or "",
        "app_url": f"{settings.frontend_url}/opportunities/{opp.id}",
    }


def send_discord_notification(opportunities: List[Opportunity]):
    """Send notification to Discord webhook"""
    if not settings.discord_webhook_url:
        return
    
    try:
        embeds = []
        for opp in opportunities[:10]:  # Limit to 10 per message
            data = format_opportunity_message(opp)
            
            embed = {
                "title": f"🎯 {data['title']}",
                "description": f"**Score:** {data['score']}/20\n"
                              f"**Catégorie:** {data['category']}\n"
                              f"**Organisation:** {data['organization']}"
                              f"{data['deadline']}{data['budget']}",
                "color": 0x6366f1 if data['score'] >= 10 else 0x94a3b8,
                "url": data['app_url'],
                "footer": {"text": "Opportunities Radar"},
            }
            embeds.append(embed)
        
        payload = {
            "username": "Opportunities Radar",
            "embeds": embeds,
        }
        
        response = httpx.post(
            settings.discord_webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Discord notification sent for {len(opportunities)} opportunities")
        
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {str(e)}")


def send_slack_notification(opportunities: List[Opportunity]):
    """Send notification to Slack webhook"""
    if not settings.slack_webhook_url:
        return
    
    try:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 {len(opportunities)} nouvelle(s) opportunité(s)",
                }
            }
        ]
        
        for opp in opportunities[:10]:
            data = format_opportunity_message(opp)
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{data['app_url']}|{data['title']}>*\n"
                            f"Score: {data['score']}/20 | {data['category']}\n"
                            f"_{data['organization']}_{data['deadline']}{data['budget']}"
                }
            })
            blocks.append({"type": "divider"})
        
        payload = {"blocks": blocks}
        
        response = httpx.post(
            settings.slack_webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Slack notification sent for {len(opportunities)} opportunities")
        
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")


def send_email_notification(
    opportunities: List[Opportunity], recipients: List[str] = None
):
    """Send notification via email"""
    if not settings.smtp_host or not settings.smtp_user:
        return

    if not recipients:
        recipients = [settings.admin_email]

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 {len(opportunities)} nouvelle(s) opportunité(s) - Radar"
        msg["From"] = settings.smtp_from_email or settings.smtp_user
        msg["To"] = ", ".join(recipients)

        # Text version
        text_parts = ["Nouvelles opportunités détectées:\n"]
        for opp in opportunities:
            data = format_opportunity_message(opp)
            text_parts.append(
                f"- {data['title']} (Score: {data['score']})"
                f"{data['deadline']}{data['budget']}\n"
                f"  {data['app_url']}\n"
            )
        text_content = "\n".join(text_parts)

        from app.services.email_templates import opportunities_detected

        html_content = opportunities_detected(
            [format_opportunity_message(opp) for opp in opportunities]
        )

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], recipients, msg.as_string())

        logger.info(f"Email notification sent for {len(opportunities)} opportunities")

    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")


def send_notifications(opportunities: List[Opportunity]):
    """Send notifications to all configured channels"""
    if not opportunities:
        return
    
    # Discord
    if settings.discord_webhook_url:
        send_discord_notification(opportunities)
    
    # Slack
    if settings.slack_webhook_url:
        send_slack_notification(opportunities)
    
    # Email (to admin by default)
    if settings.smtp_host:
        send_email_notification(opportunities)
