"""
Credential Store Service

Manages encrypted storage of portal credentials for browser automation.
"""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from .encryption_service import EncryptionService


class AuthMethod(str, Enum):
    """Authentication methods"""
    PASSWORD = "password"
    OTP = "otp"
    BIOMETRIC = "biometric"
    AADHAAR_OTP = "aadhaar_otp"
    MOBILE_OTP = "mobile_otp"


class PortalCredential(BaseModel):
    """Represents credentials for a government portal"""
    credential_id: str
    user_id: str
    portal_name: str
    portal_url: str
    username: str
    encrypted_password: Optional[str] = None
    auth_methods: List[AuthMethod]
    mobile_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None


class CredentialStore:
    """
    Manages encrypted credential storage for government portals.
    Supports multiple authentication methods.
    """
    
    def __init__(self, encryption_service: EncryptionService):
        """
        Initialize credential store
        
        Args:
            encryption_service: Service for encrypting credentials
        """
        self.encryption_service = encryption_service
        self.credentials: Dict[str, PortalCredential] = {}
    
    def store_credential(
        self,
        user_id: str,
        portal_name: str,
        portal_url: str,
        username: str,
        password: Optional[str] = None,
        auth_methods: Optional[List[AuthMethod]] = None,
        mobile_number: Optional[str] = None,
        aadhaar_number: Optional[str] = None
    ) -> str:
        """
        Store portal credentials
        
        Args:
            user_id: User ID
            portal_name: Name of the portal
            portal_url: Portal URL
            username: Username/login ID
            password: Password (will be encrypted)
            auth_methods: List of supported auth methods
            mobile_number: Mobile number for OTP
            aadhaar_number: Aadhaar number for Aadhaar OTP
            
        Returns:
            Credential ID
        """
        credential_id = f"cred_{user_id}_{portal_name}_{datetime.now().timestamp()}"
        
        # Encrypt password if provided
        encrypted_password = None
        if password:
            encrypted_password = self.encryption_service.encrypt(
                password.encode(),
                user_id
            ).decode()
        
        # Default auth methods
        if not auth_methods:
            auth_methods = [AuthMethod.PASSWORD]
        
        credential = PortalCredential(
            credential_id=credential_id,
            user_id=user_id,
            portal_name=portal_name,
            portal_url=portal_url,
            username=username,
            encrypted_password=encrypted_password,
            auth_methods=auth_methods,
            mobile_number=mobile_number,
            aadhaar_number=aadhaar_number,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.credentials[credential_id] = credential
        return credential_id
    
    def get_credential(
        self,
        user_id: str,
        portal_name: str
    ) -> Optional[Dict]:
        """
        Retrieve credentials for a portal
        
        Args:
            user_id: User ID
            portal_name: Portal name
            
        Returns:
            Credential information with decrypted password
        """
        # Find credential for user and portal
        credential = None
        for cred in self.credentials.values():
            if cred.user_id == user_id and cred.portal_name == portal_name:
                credential = cred
                break
        
        if not credential:
            return None
        
        # Decrypt password
        decrypted_password = None
        if credential.encrypted_password:
            decrypted_password = self.encryption_service.decrypt(
                credential.encrypted_password.encode(),
                user_id
            ).decode()
        
        # Update last used
        credential.last_used = datetime.now()
        
        return {
            "credential_id": credential.credential_id,
            "portal_name": credential.portal_name,
            "portal_url": credential.portal_url,
            "username": credential.username,
            "password": decrypted_password,
            "auth_methods": credential.auth_methods,
            "mobile_number": credential.mobile_number,
            "aadhaar_number": credential.aadhaar_number
        }
    
    def update_credential(
        self,
        credential_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        mobile_number: Optional[str] = None,
        aadhaar_number: Optional[str] = None
    ) -> bool:
        """
        Update existing credential
        
        Args:
            credential_id: Credential ID
            username: New username
            password: New password
            mobile_number: New mobile number
            aadhaar_number: New Aadhaar number
            
        Returns:
            Success status
        """
        if credential_id not in self.credentials:
            return False
        
        credential = self.credentials[credential_id]
        
        if username:
            credential.username = username
        
        if password:
            credential.encrypted_password = self.encryption_service.encrypt(
                password.encode(),
                credential.user_id
            ).decode()
        
        if mobile_number:
            credential.mobile_number = mobile_number
        
        if aadhaar_number:
            credential.aadhaar_number = aadhaar_number
        
        credential.updated_at = datetime.now()
        return True
    
    def delete_credential(self, credential_id: str) -> bool:
        """
        Delete credential
        
        Args:
            credential_id: Credential ID
            
        Returns:
            Success status
        """
        if credential_id in self.credentials:
            del self.credentials[credential_id]
            return True
        return False
    
    def list_credentials(self, user_id: str) -> List[Dict]:
        """
        List all credentials for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of credential summaries (without passwords)
        """
        user_credentials = [
            cred for cred in self.credentials.values()
            if cred.user_id == user_id
        ]
        
        return [
            {
                "credential_id": cred.credential_id,
                "portal_name": cred.portal_name,
                "portal_url": cred.portal_url,
                "username": cred.username,
                "auth_methods": cred.auth_methods,
                "created_at": cred.created_at.isoformat(),
                "last_used": cred.last_used.isoformat() if cred.last_used else None
            }
            for cred in user_credentials
        ]
    
    def has_credential(self, user_id: str, portal_name: str) -> bool:
        """
        Check if user has credentials for a portal
        
        Args:
            user_id: User ID
            portal_name: Portal name
            
        Returns:
            True if credentials exist
        """
        return any(
            cred.user_id == user_id and cred.portal_name == portal_name
            for cred in self.credentials.values()
        )
