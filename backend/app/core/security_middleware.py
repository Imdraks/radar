"""
Security Middleware - Protection contre les attaques
"""
import time
import hashlib
import secrets
import re
from typing import Dict, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# RATE LIMITING - Protection contre brute force et DDoS
# ============================================================================

class RateLimiter:
    """In-memory rate limiter with sliding window"""
    
    # Explicit operational configuration only; no developer IP or loopback bypass.
    WHITELISTED_IPS: Set[str] = set()

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.WHITELISTED_IPS = set()
        self.blocked_ips: Dict[str, datetime] = {}
        # Charger les IPs whitelistées depuis env
        import os
        extra_ips = os.getenv("WHITELISTED_IPS", "")
        if extra_ips:
            for ip in extra_ips.split(","):
                self.WHITELISTED_IPS.add(ip.strip())
        
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, handling proxies"""
        from ipaddress import ip_address, ip_network
        import os
        peer = request.client.host if request.client else "unknown"
        trusted = False
        try:
            peer_address = ip_address(peer)
            for network in os.getenv("TRUSTED_PROXY_IPS", "").split(","):
                if network.strip() and peer_address in ip_network(network.strip()):
                    trusted = True
                    break
        except ValueError:
            pass
        if trusted:
            forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP")
            if forwarded:
                try:
                    return str(ip_address(forwarded.split(",")[0].strip()))
                except ValueError:
                    pass
        return peer

    def _cleanup_old_requests(self, ip: str, window_seconds: int):
        """Remove requests outside the time window"""
        cutoff = time.time() - window_seconds
        self.requests[ip] = [ts for ts in self.requests[ip] if ts > cutoff]
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP is temporarily blocked"""
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False
    
    def block_ip(self, ip: str, duration_minutes: int = 15):
        """Block an IP for a duration"""
        self.blocked_ips[ip] = datetime.now() + timedelta(minutes=duration_minutes)
        logger.warning(f"IP blocked: {ip} for {duration_minutes} minutes")
    
    def check_rate_limit(
        self, 
        request: Request, 
        max_requests: int = 100, 
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is within rate limit.
        Returns True if allowed, False if rate limited.
        """
        ip = self._get_client_ip(request)
        
        # Whitelisted IPs bypass rate limiting
        if ip in self.WHITELISTED_IPS:
            return True
        
        # Check if IP is blocked
        if self.is_blocked(ip):
            return False
        
        # A shared IP budget still protects against requests spread over endpoints.
        global_key = f"{ip}:__all__"
        bucket = request.url.path if request.url.path in RATE_LIMITS else "default"
        key = f"{ip}:{bucket}:{window_seconds}"
        self._cleanup_old_requests(global_key, 60)
        self._cleanup_old_requests(key, window_seconds)
        if len(self.requests[global_key]) >= RATE_LIMITS["default"]["max"] or len(self.requests[key]) >= max_requests:
            self.block_ip(ip, duration_minutes=5)
            return False
        now = time.time()
        self.requests[global_key].append(now)
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


# Specific limits for sensitive endpoints (scaled for 10+ concurrent users)
RATE_LIMITS = {
    "/api/v1/auth/login": {"max": 10, "window": 60},  # 10 attempts per minute (brute force protection)
    "/api/v1/auth/setup": {"max": 5, "window": 60},  # 5 attempts per minute
    "/api/v1/auth/register": {"max": 5, "window": 300},  # 5 per 5 minutes
    "/api/v1/auth/forgot-password": {"max": 5, "window": 300},  # 5 per 5 minutes
    "/api/v1/auth/reset-password": {"max": 5, "window": 300},  # 5 per 5 minutes
    "/api/v1/auth/2fa/verify": {"max": 5, "window": 60},  # 5 per minute (anti brute-force)
    "/api/v1/auth/2fa/disable": {"max": 5, "window": 60},  # 5 per minute
    "/api/v1/auth/me": {"max": 1000, "window": 60},  # 1000 per minute (very frequent polling)
    "/api/v1/auth/refresh": {"max": 300, "window": 60},  # 300 per minute (token refresh)
    "/api/v1/auth/setup-check": {"max": 500, "window": 60},  # 500 per minute (app init)
    "/api/v1/auth/sso/google/init": {"max": 30, "window": 60},  # 30 per minute
    "/api/v1/users": {"max": 300, "window": 60},  # 300 per minute
    "default": {"max": 600, "window": 60},  # 600 per minute default (10 users * 60 requests)
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        path = request.url.path
        if path in ["/health", "/health/detailed"]:
            return await call_next(request)
        
        # Get rate limit for this endpoint (auth endpoints included)
        path = request.url.path
        limits = RATE_LIMITS.get(path, RATE_LIMITS["default"])
        
        # Check rate limit
        if not rate_limiter.check_rate_limit(
            request, 
            max_requests=limits["max"], 
            window_seconds=limits["window"]
        ):
            logger.warning(f"Rate limit exceeded for {path} from {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Réessayez plus tard."},
                headers={"Retry-After": str(limits["window"])}
            )
        
        return await call_next(request)


# ============================================================================
# SECURITY HEADERS - Protection XSS, Clickjacking, etc.
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy - Prevent XSS
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://www.google-analytics.com https://*.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.spotify.com https://www.google-analytics.com https://*.google-analytics.com https://*.googleapis.com https://recherche-entreprises.api.gouv.fr https://www.googletagmanager.com; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS - Force HTTPS (1 year)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        
        return response


# ============================================================================
# INPUT SANITIZATION - Protection SQL Injection & XSS
# ============================================================================

# Patterns that indicate SQL injection attempts
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b)",
    r"(--|\#|/\*|\*/)",  # SQL comments
    r"(\bOR\b.*=.*|1\s*=\s*1|'\s*OR\s*')",  # OR-based injection
    r"(\bUNION\b.*\bSELECT\b)",  # UNION injection
    r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",  # Stacked queries
    r"(\bEXEC\b|\bEXECUTE\b)",  # Execute commands
    r"(\bxp_\w+)",  # SQL Server extended procedures
]

# Patterns that indicate XSS attempts
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript\s*:",
    r"on\w+\s*=",  # Event handlers like onclick, onerror
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"<link[^>]*>",
    r"<meta[^>]*>",
    r"expression\s*\(",  # CSS expression
    r"url\s*\(\s*['\"]?\s*javascript",  # CSS url() with javascript
]


def detect_sql_injection(text: str) -> bool:
    """Detect potential SQL injection in text"""
    if not text:
        return False
    text_upper = text.upper()
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return True
    return False


def detect_xss(text: str) -> bool:
    """Detect potential XSS in text"""
    if not text:
        return False
    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def sanitize_input(text: str) -> str:
    """Sanitize user input by escaping dangerous characters"""
    if not text:
        return text
    
    # HTML escape
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize all inputs"""
    
    # Paths that don't need input validation (file uploads, etc.)
    SKIP_PATHS = ["/api/v1/assets", "/api/v1/drive"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip for certain paths
        path = request.url.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)
        
        # Check query parameters
        for key, value in request.query_params.items():
            if detect_sql_injection(value):
                logger.warning(f"SQL injection attempt detected in query param '{key}' from {request.client.host if request.client else 'unknown'}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Requête invalide"}
                )
            if detect_xss(value):
                logger.warning(f"XSS attempt detected in query param '{key}' from {request.client.host if request.client else 'unknown'}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Requête invalide"}
                )
        
        return await call_next(request)


# ============================================================================
# REQUEST ID - Traçabilité des requêtes
# ============================================================================

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add unique request ID for tracing"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = secrets.token_hex(16)
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


# ============================================================================
# AUDIT LOGGING - Log des actions sensibles
# ============================================================================

class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log sensitive actions for audit trail"""
    
    SENSITIVE_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/setup",
        "/api/v1/users",
        "/api/v1/admin",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Log sensitive endpoints
        path = request.url.path
        method = request.method
        
        is_sensitive = any(path.startswith(sp) for sp in self.SENSITIVE_PATHS)
        
        if is_sensitive and method in ["POST", "PUT", "DELETE", "PATCH"]:
            client_ip = request.headers.get("X-Forwarded-For", 
                        request.headers.get("X-Real-IP",
                        request.client.host if request.client else "unknown"))
            user_agent = request.headers.get("User-Agent", "unknown")
            
            logger.info(
                f"AUDIT: {method} {path} | IP: {client_ip} | UA: {user_agent[:50]}..."
            )
        
        response = await call_next(request)
        
        # Log failed auth attempts
        if path == "/api/v1/auth/login" and response.status_code in [401, 403]:
            logger.warning(
                f"AUDIT: Failed login attempt | IP: {request.client.host if request.client else 'unknown'}"
            )
        
        return response


# ============================================================================
# BLOCKED USER AGENTS - Block known bad bots
# ============================================================================

BLOCKED_USER_AGENTS = [
    "sqlmap",
    "nikto",
    "nmap",
    "masscan",
    "burpsuite",
    "dirbuster",
    "gobuster",
    "wpscan",
    "nuclei",
    "httpx",
]


class BotProtectionMiddleware(BaseHTTPMiddleware):
    """Block known malicious bots and scanners"""
    
    async def dispatch(self, request: Request, call_next):
        user_agent = request.headers.get("User-Agent", "").lower()
        
        for bad_ua in BLOCKED_USER_AGENTS:
            if bad_ua in user_agent:
                logger.warning(f"Blocked malicious bot: {user_agent} from {request.client.host if request.client else 'unknown'}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied"}
                )
        
        return await call_next(request)
