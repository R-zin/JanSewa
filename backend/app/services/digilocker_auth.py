"""
DigiLocker Authentication Service

Handles OAuth 2.0 authentication flow with DigiLocker API.
Manages token storage, refresh, and revocation.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import secrets
from .encryption_service import EncryptionService


class DigiLockerToken(BaseModel):
    """Represents DigiLocker OAuth tokens"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    scope: str


class DigiLockerAuthenticator:
    """
    Manages DigiLocker OAuth 2.0 authentication.
    Handles token lifecycle including storage, refresh, and revocation.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        encryption_service: EncryptionService
    ):
        """
        Initialize DigiLocker authenticator
        
        Args:
            client_id: DigiLocker OAuth client ID
            client_secret: DigiLocker OAuth client secret
            redirect_uri: OAuth redirect URI
            encryption_service: Service for encrypting tokens
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.encryption_service = encryption_service
        
        # DigiLocker OAuth endpoints
        self.auth_url = "https://digilocker.meity.gov.in/public/oauth2/1/authorize"
        self.token_url = "https://digilocker.meity.gov.in/public/oauth2/1/token"
        self.revoke_url = "https://digilocker.meity.gov.in/public/oauth2/1/revoke"
        
        # Token storage (in production, use database)
        self.user_tokens: Dict[str, DigiLockerToken] = {}
        self.state_tokens: Dict[str, str] = {}  # CSRF protection
    
    def generate_auth_url(self, user_id: str, scope: str = "public") -> Dict[str, str]:
        """
        Generate OAuth authorization URL
        
        Args:
            user_id: User ID requesting authorization
            scope: OAuth scope (default: public)
            
        Returns:
            Dictionary with auth_url and state token
        """
        # Generate state token for CSRF protection
        state = secrets.token_urlsafe(32)
        self.state_tokens[state] = user_id
        
        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": scope
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.auth_url}?{query_string}"
        
        return {
            "auth_url": auth_url,
            "state": state
        }
    
    def validate_state(self, state: str) -> Optional[str]:
        """
        Validate state token and return associated user ID
        
        Args:
            state: State token from OAuth callback
            
        Returns:
            User ID if valid, None otherwise
        """
        return self.state_tokens.pop(state, None)
    
    async def exchange_code_for_token(
        self,
        code: str,
        state: str
    ) -> Optional[Dict]:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from OAuth callback
            state: State token for validation
            
        Returns:
            Token information or None if failed
        """
        # Validate state token
        user_id = self.validate_state(state)
        if not user_id:
            return None
        
        # In production, make actual HTTP request to DigiLocker
        # For now, simulate token exchange
        token_data = {
            "access_token": f"dl_access_{secrets.token_urlsafe(32)}",
            "refresh_token": f"dl_refresh_{secrets.token_urlsafe(32)}",
            "token_type": "Bearer",
            "expires_in": 3600,  # 1 hour
            "scope": "public"
        }
        
        # Calculate expiration time
        expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        
        # Create token object
        token = DigiLockerToken(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_at=expires_at,
            scope=token_data["scope"]
        )
        
        # Encrypt and store token
        encrypted_token = self._encrypt_token(user_id, token)
        self.user_tokens[user_id] = encrypted_token
        
        return {
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
            "scope": token_data["scope"]
        }
    
    def _encrypt_token(self, user_id: str, token: DigiLockerToken) -> DigiLockerToken:
        """
        Encrypt token data
        
        Args:
            user_id: User ID for encryption key
            token: Token to encrypt
            
        Returns:
            Token with encrypted values
        """
        # Encrypt sensitive token data
        encrypted_access = self.encryption_service.encrypt(
            token.access_token.encode(),
            user_id
        )
        encrypted_refresh = self.encryption_service.encrypt(
            token.refresh_token.encode(),
            user_id
        )
        
        return DigiLockerToken(
            access_token=encrypted_access.decode(),
            refresh_token=encrypted_refresh.decode(),
            token_type=token.token_type,
            expires_at=token.expires_at,
            scope=token.scope
        )
    
    def _decrypt_token(self, user_id: str, token: DigiLockerToken) -> DigiLockerToken:
        """
        Decrypt token data
        
        Args:
            user_id: User ID for decryption key
            token: Token to decrypt
            
        Returns:
            Token with decrypted values
        """
        # Decrypt token data
        decrypted_access = self.encryption_service.decrypt(
            token.access_token.encode(),
            user_id
        )
        decrypted_refresh = self.encryption_service.decrypt(
            token.refresh_token.encode(),
            user_id
        )
        
        return DigiLockerToken(
            access_token=decrypted_access.decode(),
            refresh_token=decrypted_refresh.decode(),
            token_type=token.token_type,
            expires_at=token.expires_at,
            scope=token.scope
        )
    
    def get_access_token(self, user_id: str) -> Optional[str]:
        """
        Get valid access token for user, refreshing if necessary
        
        Args:
            user_id: User ID
            
        Returns:
            Valid access token or None
        """
        if user_id not in self.user_tokens:
            return None
        
        encrypted_token = self.user_tokens[user_id]
        token = self._decrypt_token(user_id, encrypted_token)
        
        # Check if token is expired
        if datetime.now() >= token.expires_at:
            # Attempt to refresh token
            refreshed = self._refresh_token(user_id, token)
            if not refreshed:
                return None
            token = self._decrypt_token(user_id, self.user_tokens[user_id])
        
        return token.access_token
    
    def _refresh_token(self, user_id: str, token: DigiLockerToken) -> bool:
        """
        Refresh access token using refresh token
        
        Args:
            user_id: User ID
            token: Current token with refresh token
            
        Returns:
            Success status
        """
        # In production, make actual HTTP request to DigiLocker
        # For now, simulate token refresh
        try:
            new_token_data = {
                "access_token": f"dl_access_{secrets.token_urlsafe(32)}",
                "refresh_token": token.refresh_token,  # Reuse refresh token
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": token.scope
            }
            
            expires_at = datetime.now() + timedelta(seconds=new_token_data["expires_in"])
            
            new_token = DigiLockerToken(
                access_token=new_token_data["access_token"],
                refresh_token=new_token_data["refresh_token"],
                token_type=new_token_data["token_type"],
                expires_at=expires_at,
                scope=new_token_data["scope"]
            )
            
            # Encrypt and store new token
            encrypted_token = self._encrypt_token(user_id, new_token)
            self.user_tokens[user_id] = encrypted_token
            
            return True
            
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return False
    
    def is_authenticated(self, user_id: str) -> bool:
        """
        Check if user has valid DigiLocker authentication
        
        Args:
            user_id: User ID
            
        Returns:
            True if authenticated with valid token
        """
        if user_id not in self.user_tokens:
            return False
        
        # Try to get access token (will refresh if needed)
        token = self.get_access_token(user_id)
        return token is not None
    
    async def revoke_token(self, user_id: str) -> bool:
        """
        Revoke DigiLocker access token
        
        Args:
            user_id: User ID
            
        Returns:
            Success status
        """
        if user_id not in self.user_tokens:
            return False
        
        encrypted_token = self.user_tokens[user_id]
        token = self._decrypt_token(user_id, encrypted_token)
        
        # In production, make actual HTTP request to DigiLocker revoke endpoint
        # For now, just remove from storage
        try:
            del self.user_tokens[user_id]
            return True
        except Exception as e:
            print(f"Token revocation failed: {e}")
            return False
    
    def disconnect(self, user_id: str) -> bool:
        """
        Disconnect user from DigiLocker (revoke and remove tokens)
        
        Args:
            user_id: User ID
            
        Returns:
            Success status
        """
        # Revoke token on DigiLocker side
        # In production, this would be an async call
        
        # Remove from local storage
        if user_id in self.user_tokens:
            del self.user_tokens[user_id]
            return True
        
        return False
    
    def get_token_info(self, user_id: str) -> Optional[Dict]:
        """
        Get token information for user
        
        Args:
            user_id: User ID
            
        Returns:
            Token information or None
        """
        if user_id not in self.user_tokens:
            return None
        
        encrypted_token = self.user_tokens[user_id]
        token = self._decrypt_token(user_id, encrypted_token)
        
        return {
            "token_type": token.token_type,
            "expires_at": token.expires_at.isoformat(),
            "scope": token.scope,
            "is_expired": datetime.now() >= token.expires_at
        }
