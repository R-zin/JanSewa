from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting documents"""
    
    def __init__(self):
        self.master_key = settings.SECRET_KEY.encode()
    
    def generate_user_key(self, user_id: int, salt: bytes = None) -> bytes:
        """Generate user-specific encryption key"""
        if salt is None:
            salt = base64.urlsafe_b64encode(str(user_id).encode().ljust(16, b'0'))
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return key
    
    def encrypt_document(self, data: bytes, user_id: int) -> bytes:
        """Encrypt document data"""
        try:
            key = self.generate_user_key(user_id)
            f = Fernet(key)
            encrypted_data = f.encrypt(data)
            logger.info(f"Document encrypted for user {user_id}")
            return encrypted_data
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_document(self, encrypted_data: bytes, user_id: int) -> bytes:
        """Decrypt document data"""
        try:
            key = self.generate_user_key(user_id)
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted_data)
            logger.info(f"Document decrypted for user {user_id}")
            return decrypted_data
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_text(self, text: str, user_id: int) -> str:
        """Encrypt text data"""
        encrypted = self.encrypt_document(text.encode(), user_id)
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_text(self, encrypted_text: str, user_id: int) -> str:
        """Decrypt text data"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
        decrypted = self.decrypt_document(encrypted_bytes, user_id)
        return decrypted.decode()


encryption_service = EncryptionService()
