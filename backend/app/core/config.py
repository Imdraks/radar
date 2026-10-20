"""
Application configuration using Pydantic Settings
"""
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Radar"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    
    # Database
    database_url: str = "postgresql://radar:radar_password@localhost:5432/opportunities_radar"
    
    # Optional free-quota YouTube Data API key; never sent to the frontend.
    youtube_api_key: str = Field(default="", repr=False)

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # JWT Auth
    jwt_secret_key: str = "your-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # IMAP Email
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "NEWSLETTERS"
    imap_use_ssl: bool = True
    imap_poll_interval_minutes: int = 5
    
    # SMTP Notifications
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    
    # Webhook Notifications
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    
    # Spotify API
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    
    # OpenAI API (for extraction and brief generation)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    # Groq API (FREE alternative to OpenAI - https://console.groq.com)
    groq_api_key: Optional[str] = None
    
    # Tavily API (for real-time web search)
    tavily_api_key: Optional[str] = None
    
    # Ticketmaster Discovery API (for real concert/festival events)
    # Get free key at https://developer.ticketmaster.com
    ticketmaster_api_key: Optional[str] = None
    
    # Revolut Business API
    revolut_client_id: str = ""
    revolut_private_key_path: str = ""   # Path to RSA private key PEM file
    revolut_redirect_uri: str = ""       # OAuth redirect URI (e.g. https://radarapp.fr/api/v1/banking/revolut/callback)
    revolut_sandbox: bool = True         # Use sandbox environment
    
    # SSO - Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # SSO - Apple Sign In
    apple_client_id: str = ""  # Apple Service ID
    apple_team_id: str = ""    # Apple Team ID
    apple_key_id: str = ""     # Apple Key ID
    apple_private_key: str = ""  # Apple private key (PEM format)
    
    # Viberate Web Scraping (for enrichment)
    viberate_enabled: bool = True
    viberate_request_delay: float = 1.5  # seconds between requests
    
    # Notification Thresholds
    notification_min_score: int = 10
    notification_urgent_days: int = 7
    notification_urgent_min_score: int = 8
    
    # Ingestion Settings
    ingestion_web_interval_hours: int = 6
    ingestion_email_interval_minutes: int = 5
    ingestion_max_retries: int = 2
    ingestion_timeout_seconds: int = 30
    ingestion_user_agent: str = "OpportunitiesRadar/1.0"
    
    # Scoring defaults
    scoring_urgency_7_days: int = 6
    scoring_urgency_14_days: int = 4
    scoring_urgency_30_days: int = 2
    scoring_event_fit_high: int = 3
    scoring_event_fit_medium: int = 2
    scoring_quality_link: int = 2
    scoring_quality_contact: int = 2
    scoring_value_institution: int = 2
    scoring_value_budget: int = 2
    scoring_penalty_no_info: int = -4
    scoring_penalty_promo: int = -2
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # Default Admin
    admin_email: str = "admin@youragency.com"
    admin_password: str = "change-this-password"
    
    # Security - Registration Whitelist
    # If True, only users with a pending workspace invite can register/login
    require_workspace_invite: bool = True
    # Comma-separated list of always-allowed email domains (e.g., "youragency.com,partner.com")
    allowed_email_domains: str = ""
    # Comma-separated list of always-allowed emails (e.g., "ceo@example.com,admin@example.com")
    allowed_emails: str = ""
    
    # Resend API (for sending invitation emails)
    resend_api_key: str = ""
    resend_from_email: str = "Radar <noreply@radarapp.fr>"
    # Enable/disable sending invitation emails (can be toggled by admins)
    send_invitation_emails: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def validate_security_settings(self) -> list[str]:
        """Validate critical security settings. Returns list of warnings."""
        warnings = []
        
        # Check for default/weak secrets
        if self.secret_key == "change-this-in-production":
            warnings.append("CRITICAL: secret_key is using default value!")
        if self.jwt_secret_key == "your-jwt-secret-key":
            warnings.append("CRITICAL: jwt_secret_key is using default value!")
        if len(self.secret_key) < 32:
            warnings.append("WARNING: secret_key should be at least 32 characters")
        if len(self.jwt_secret_key) < 32:
            warnings.append("WARNING: jwt_secret_key should be at least 32 characters")
        if self.admin_password == "change-this-password":
            warnings.append("CRITICAL: admin_password is using default value!")
            
        # Check for production settings
        if self.app_env == "production":
            if self.debug:
                warnings.append("WARNING: debug=True in production!")
            if "localhost" in self.database_url:
                warnings.append("WARNING: Using localhost database in production!")
                
        return warnings


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

# Log security warnings on startup (only in non-test environments)
import os
if os.environ.get("TESTING") != "true":
    import logging
    _logger = logging.getLogger(__name__)
    _warnings = settings.validate_security_settings()
    _has_critical = False
    for w in _warnings:
        if "CRITICAL" in w:
            _logger.critical(w)
            _has_critical = True
        else:
            _logger.warning(w)
    # Block startup with default secrets in production
    if _has_critical and settings.app_env == "production":
        raise RuntimeError(
            "SECURITY: Cannot start with default secrets in production! "
            "Set SECRET_KEY, JWT_SECRET_KEY, and ADMIN_PASSWORD in .env"
        )
