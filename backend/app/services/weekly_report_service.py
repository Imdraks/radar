"""
Service de rapports hebdomadaires automatiques
Génère et envoie des rapports d'activité par email
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from decimal import Decimal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case

from app.db.models.opportunity import Opportunity, OpportunityStatus, OpportunityCategory
from app.db.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WeeklyStats:
    """Statistiques hebdomadaires"""
    period_start: datetime
    period_end: datetime
    
    # Volumes
    total_new: int = 0
    total_qualified: int = 0
    total_submitted: int = 0
    total_won: int = 0
    total_lost: int = 0
    
    # Financier
    budget_won: Decimal = Decimal("0")
    budget_pipeline: Decimal = Decimal("0")
    avg_budget: Decimal = Decimal("0")
    
    # Performance
    conversion_rate: float = 0.0
    avg_score_new: float = 0.0
    avg_time_to_qualify: float = 0.0  # jours
    
    # Par catégorie
    by_category: Dict[str, int] = field(default_factory=dict)
    
    # Par source
    by_source: Dict[str, int] = field(default_factory=dict)
    
    # Top opportunités
    top_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Deadlines urgentes
    urgent_deadlines: List[Dict[str, Any]] = field(default_factory=list)
    
    # Comparaison semaine précédente
    vs_previous_week: Dict[str, float] = field(default_factory=dict)


class WeeklyReportService:
    """Service de génération de rapports hebdomadaires"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_weekly_stats(
        self,
        end_date: Optional[datetime] = None
    ) -> WeeklyStats:
        """Génère les statistiques de la semaine"""
        if not end_date:
            end_date = datetime.utcnow()
        
        start_date = end_date - timedelta(days=7)
        prev_start = start_date - timedelta(days=7)
        
        stats = WeeklyStats(
            period_start=start_date,
            period_end=end_date
        )
        
        # Nouvelles opportunités cette semaine
        stats.total_new = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.created_at >= start_date,
            Opportunity.created_at < end_date
        ).scalar() or 0
        
        # Qualifiées cette semaine
        stats.total_qualified = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.status == OpportunityStatus.QUALIFIED,
            Opportunity.updated_at >= start_date,
            Opportunity.updated_at < end_date
        ).scalar() or 0
        
        # Soumises cette semaine
        stats.total_submitted = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.status == OpportunityStatus.SUBMITTED,
            Opportunity.updated_at >= start_date,
            Opportunity.updated_at < end_date
        ).scalar() or 0
        
        # Gagnées cette semaine
        stats.total_won = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.status == OpportunityStatus.WON,
            Opportunity.updated_at >= start_date,
            Opportunity.updated_at < end_date
        ).scalar() or 0
        
        # Perdues cette semaine
        stats.total_lost = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.status == OpportunityStatus.LOST,
            Opportunity.updated_at >= start_date,
            Opportunity.updated_at < end_date
        ).scalar() or 0
        
        # Budget gagné
        stats.budget_won = self.db.query(func.sum(Opportunity.budget_amount)).filter(
            Opportunity.status == OpportunityStatus.WON,
            Opportunity.updated_at >= start_date,
            Opportunity.updated_at < end_date,
            Opportunity.budget_amount.isnot(None)
        ).scalar() or Decimal("0")
        
        # Budget en pipeline
        stats.budget_pipeline = self.db.query(func.sum(Opportunity.budget_amount)).filter(
            Opportunity.status.in_([
                OpportunityStatus.QUALIFIED,
                OpportunityStatus.IN_PROGRESS,
                OpportunityStatus.SUBMITTED
            ]),
            Opportunity.budget_amount.isnot(None)
        ).scalar() or Decimal("0")
        
        # Budget moyen des nouvelles
        stats.avg_budget = self.db.query(func.avg(Opportunity.budget_amount)).filter(
            Opportunity.created_at >= start_date,
            Opportunity.created_at < end_date,
            Opportunity.budget_amount.isnot(None)
        ).scalar() or Decimal("0")
        
        # Taux de conversion (WON / (WON + LOST))
        total_closed = stats.total_won + stats.total_lost
        stats.conversion_rate = (stats.total_won / total_closed * 100) if total_closed > 0 else 0
        
        # Score moyen des nouvelles
        stats.avg_score_new = self.db.query(func.avg(Opportunity.score)).filter(
            Opportunity.created_at >= start_date,
            Opportunity.created_at < end_date
        ).scalar() or 0
        
        # Par catégorie
        category_counts = self.db.query(
            Opportunity.category,
            func.count(Opportunity.id)
        ).filter(
            Opportunity.created_at >= start_date,
            Opportunity.created_at < end_date
        ).group_by(Opportunity.category).all()
        
        stats.by_category = {cat.value: count for cat, count in category_counts}
        
        # Par source
        source_counts = self.db.query(
            Opportunity.source_name,
            func.count(Opportunity.id)
        ).filter(
            Opportunity.created_at >= start_date,
            Opportunity.created_at < end_date
        ).group_by(Opportunity.source_name).all()
        
        stats.by_source = {name: count for name, count in source_counts}
        
        # Top 5 opportunités (par score)
        top_opps = self.db.query(Opportunity).filter(
            Opportunity.status.in_([
                OpportunityStatus.NEW,
                OpportunityStatus.REVIEW,
                OpportunityStatus.QUALIFIED
            ])
        ).order_by(Opportunity.score.desc()).limit(5).all()
        
        stats.top_opportunities = [
            {
                "id": opp.id,
                "title": opp.title[:80],
                "score": opp.score,
                "budget": float(opp.budget_amount) if opp.budget_amount else None,
                "deadline": opp.deadline_at.isoformat() if opp.deadline_at else None,
                "organization": opp.organization
            }
            for opp in top_opps
        ]
        
        # Deadlines urgentes (7 prochains jours)
        urgent = self.db.query(Opportunity).filter(
            Opportunity.deadline_at >= end_date,
            Opportunity.deadline_at <= end_date + timedelta(days=7),
            Opportunity.status.notin_([
                OpportunityStatus.WON,
                OpportunityStatus.LOST,
                OpportunityStatus.ARCHIVED
            ])
        ).order_by(Opportunity.deadline_at).limit(10).all()
        
        stats.urgent_deadlines = [
            {
                "id": opp.id,
                "title": opp.title[:60],
                "deadline": opp.deadline_at.isoformat(),
                "days_remaining": (opp.deadline_at - end_date).days,
                "status": opp.status.value
            }
            for opp in urgent
        ]
        
        # Comparaison avec semaine précédente
        prev_new = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.created_at >= prev_start,
            Opportunity.created_at < start_date
        ).scalar() or 0
        
        prev_won = self.db.query(func.count(Opportunity.id)).filter(
            Opportunity.status == OpportunityStatus.WON,
            Opportunity.updated_at >= prev_start,
            Opportunity.updated_at < start_date
        ).scalar() or 0
        
        stats.vs_previous_week = {
            "new_change": ((stats.total_new - prev_new) / prev_new * 100) if prev_new > 0 else 0,
            "won_change": ((stats.total_won - prev_won) / prev_won * 100) if prev_won > 0 else 0,
        }
        
        return stats
    
    def generate_html_report(self, stats: WeeklyStats) -> str:
        """Render recorded statistics using Radar’s shared email design."""
        from app.services.email_templates import weekly_stats

        return weekly_stats(stats)
    
    def send_report_email(
        self,
        recipients: List[str],
        stats: WeeklyStats,
        html_content: str
    ) -> bool:
        """Envoie le rapport par email"""
        if not settings.smtp_host or not settings.smtp_user:
            logger.warning("SMTP non configuré, rapport non envoyé")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"📊 Rapport Hebdo Radar - {stats.period_start.strftime('%d/%m')} au {stats.period_end.strftime('%d/%m/%Y')}"
            msg["From"] = settings.smtp_from_email or settings.smtp_user
            msg["To"] = ", ".join(recipients)
            
            # Version texte simple
            text_content = f"""
Rapport Hebdomadaire Radar
{stats.period_start.strftime('%d/%m/%Y')} - {stats.period_end.strftime('%d/%m/%Y')}

📈 RÉSUMÉ
- Nouvelles opportunités: {stats.total_new}
- Qualifiées: {stats.total_qualified}
- Gagnées: {stats.total_won}
- Taux de conversion: {stats.conversion_rate:.1f}%

💰 FINANCIER
- Budget gagné: {float(stats.budget_won):,.0f} €
- Pipeline total: {float(stats.budget_pipeline):,.0f} €

Voir le rapport complet: {settings.frontend_url}
            """
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Envoi
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(
                    settings.smtp_from_email or settings.smtp_user,
                    recipients,
                    msg.as_string()
                )
            
            logger.info(f"Rapport hebdo envoyé à {len(recipients)} destinataires")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi rapport: {e}")
            return False
    
    def generate_and_send(self, recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """Génère et envoie le rapport complet"""
        # Générer les stats
        stats = self.generate_weekly_stats()
        
        # Générer le HTML
        html = self.generate_html_report(stats)
        
        # Récupérer les destinataires (tous les admins si non spécifié)
        if not recipients:
            admins = self.db.query(User).filter(User.role == "admin").all()
            recipients = [u.email for u in admins if u.email]
        
        # Envoyer
        sent = False
        if recipients:
            sent = self.send_report_email(recipients, stats, html)
        
        return {
            "stats": {
                "period": f"{stats.period_start.isoformat()} - {stats.period_end.isoformat()}",
                "total_new": stats.total_new,
                "total_won": stats.total_won,
                "budget_won": float(stats.budget_won),
                "conversion_rate": stats.conversion_rate
            },
            "recipients": recipients,
            "sent": sent,
            "html_preview": html[:500] + "..."
        }
