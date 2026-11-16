"""
SSO Authentication Service
Handles Google and Apple OAuth/OIDC authentication
"""
import httpx
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.user import User, Role
from app.db.models.account import Account
from app.core.security import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


# OIDC Configuration URLs
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"


class SSOService:
    """Service for handling SSO authentication with Google and Apple"""
    
    def __init__(self, db: Session):
        self.db = db
        self._google_config: Optional[Dict] = None
        self._apple_keys: Optional[Dict] = None
    
    async def get_google_config(self) -> Dict:
        """Fetch Google OIDC configuration"""
        if self._google_config:
            return self._google_config
        
        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_DISCOVERY_URL)
            self._google_config = response.json()
            return self._google_config
    
    def get_google_auth_url(self, redirect_uri: str, state: str, nonce: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "access_type": "offline",
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    
    async def exchange_google_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens with Google"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                raise ValueError("Failed to exchange Google authorization code")
            return response.json()
    
    def decode_google_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Decode and verify Google ID token using Google's public keys.
        """
        try:
            # Fetch Google's JWKS for signature verification
            jwks_client = jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.google_client_id,
                issuer=["https://accounts.google.com", "accounts.google.com"],
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
            )
            return claims
        except jwt.exceptions.PyJWKClientError as e:
            logger.error(f"Failed to fetch Google JWKS: {e}")
            raise ValueError("Failed to verify Google ID token")
        except jwt.exceptions.InvalidTokenError as e:
            logger.error(f"Invalid Google ID token: {e}")
            raise ValueError("Invalid Google ID token")
    
    def get_apple_auth_url(self, redirect_uri: str, state: str, nonce: str) -> str:
        """Generate Apple OAuth authorization URL"""
        params = {
            "client_id": settings.apple_client_id,  # Apple Service ID
            "redirect_uri": redirect_uri,
            "response_type": "code id_token",
            "scope": "name email",
            "response_mode": "form_post",
            "state": state,
            "nonce": nonce,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://appleid.apple.com/auth/authorize?{query}"
    
    async def exchange_apple_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens with Apple"""
        # Apple requires a client_secret JWT signed with your private key
        client_secret = self._generate_apple_client_secret()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://appleid.apple.com/auth/token",
                data={
                    "code": code,
                    "client_id": settings.apple_client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            if response.status_code != 200:
                logger.error(f"Apple token exchange failed: {response.text}")
                raise ValueError("Failed to exchange Apple authorization code")
            return response.json()
    
    def _generate_apple_client_secret(self) -> str:
        """Generate Apple client secret JWT"""
        now = datetime.utcnow()
        payload = {
            "iss": settings.apple_team_id,
            "iat": now,
            "exp": now + timedelta(days=180),  # Max 6 months
            "aud": "https://appleid.apple.com",
            "sub": settings.apple_client_id,
        }
        headers = {
            "kid": settings.apple_key_id,
            "alg": "ES256",
        }
        # Sign with Apple private key
        return jwt.encode(
            payload,
            settings.apple_private_key,
            algorithm="ES256",
            headers=headers
        )
    
    def decode_apple_id_token(self, id_token: str) -> Dict[str, Any]:
        """Decode and verify Apple ID token using Apple's public keys."""
        try:
            jwks_client = jwt.PyJWKClient(APPLE_KEYS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=settings.apple_client_id,
                issuer="https://appleid.apple.com",
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
            )
            return claims
        except jwt.exceptions.PyJWKClientError as e:
            logger.error(f"Failed to fetch Apple JWKS: {e}")
            raise ValueError("Failed to verify Apple ID token")
        except jwt.exceptions.InvalidTokenError as e:
            logger.error(f"Invalid Apple ID token: {e}")
            raise ValueError("Invalid Apple ID token")
    
    def find_or_create_user_from_sso(
        self,
        provider: str,
        provider_account_id: str,
        email: Optional[str],
        email_verified: bool,
        name: Optional[str],
        avatar_url: Optional[str],
        tokens: Dict[str, Any]
    ) -> Tuple[User, bool]:
        """
        Find existing user by SSO account or create new one.
        Returns (user, is_new_user)
        
        Account Linking Rules:
        1. If provider_account_id exists → login directly
        2. If email exists and matches existing user → link account
        3. Otherwise → create new user
        """
        # 1. Check if SSO account already exists
        account = self.db.query(Account).filter(
            Account.provider == provider,
            Account.provider_account_id == provider_account_id
        ).first()
        
        if account:
            # Update tokens
            account.access_token = tokens.get("access_token")
            account.refresh_token = tokens.get("refresh_token")
            account.id_token = tokens.get("id_token")
            account.expires_at = tokens.get("expires_at")
            account.updated_at = datetime.utcnow()
            
            # A provider callback proves only the first factor. finish_login
            # records a successful connection after Radar MFA has completed.
            self.db.commit()
            
            logger.info(f"SSO login: existing account {provider}:{provider_account_id}")
            return account.user, False
        
        # 2. Check if email matches existing user (account linking)
        user = None
        if email and email_verified:
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                logger.info(f"SSO linking: {provider} to existing user {email}")
        
        # 3. Create new user if needed
        is_new_user = False
        if not user:
            # Check if this is the first user (make them admin)
            user_count = self.db.query(User).count()
            role = Role.ADMIN if user_count == 0 else Role.VIEWER
            
            user = User(
                email=email,
                full_name=name,
                auth_provider=provider,
                avatar_url=avatar_url,
                role=role,
                is_active=True,
                is_superuser=(user_count == 0),
            )
            self.db.add(user)
            self.db.flush()  # Get user ID
            is_new_user = True
            logger.info(f"SSO signup: new user from {provider} - {email or provider_account_id}")
        
        # Create SSO account link
        account = Account(
            user_id=user.id,
            provider=provider,
            provider_account_id=provider_account_id,
            email=email,
            email_verified=email_verified,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            id_token=tokens.get("id_token"),
            expires_at=tokens.get("expires_at"),
            token_type=tokens.get("token_type"),
            scope=tokens.get("scope"),
        )
        self.db.add(account)
        
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        
        self.db.commit()
        
        return user, is_new_user
    
    def create_session_tokens(self, user: User) -> Dict[str, Any]:
        """Create JWT access and refresh tokens for the user"""
        from app.core import mfa
        user = mfa.lock_user(self.db, user.id)
        if mfa.methods(user):
            token, _ = mfa.create_challenge(self.db, user, 'login')
            self.db.commit()
            return {'requires_2fa': True, 'temp_token': token}
        from app.api.auth import finish_login
        return finish_login(self.db, user, None).model_dump(exclude_none=True)
    

    def get_user_accounts(self, user_id: UUID) -> list:
        """Get all SSO accounts linked to a user"""
        accounts = self.db.query(Account).filter(Account.user_id == user_id).all()
        return [
            {
                "provider": acc.provider,
                "email": acc.email,
                "created_at": acc.created_at.isoformat(),
            }
            for acc in accounts
        ]
    
    def unlink_account(self, user_id: UUID, provider: str) -> bool:
        """Unlink an SSO account from a user (if they have other auth methods)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Check user has another way to login
        accounts = self.db.query(Account).filter(Account.user_id == user_id).all()
        has_password = user.hashed_password is not None
        
        if len(accounts) <= 1 and not has_password:
            raise ValueError("Cannot unlink last authentication method")
        
        # Delete the account
        deleted = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.provider == provider
        ).delete()
        
        self.db.commit()
        return deleted > 0
