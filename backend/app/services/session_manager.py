import uuid
import redis
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions with privacy controls"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.session_timeout = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    def create_session(self, user_id: int, language: str = "en") -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": datetime.utcnow().isoformat(),
            "language": language,
            "conversation_history": [],
            "temporary_context": {}
        }
        
        # Store in Redis with expiration
        self.redis_client.setex(
            f"session:{session_id}",
            int(self.session_timeout.total_seconds()),
            json.dumps(session_data)
        )
        
        logger.info(f"Session created: {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            return json.loads(session_data)
        return None
    
    def update_context(self, session_id: str, key: str, value: Any) -> bool:
        """Update session context"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        session_data["temporary_context"][key] = value
        
        # Update in Redis
        self.redis_client.setex(
            f"session:{session_id}",
            int(self.session_timeout.total_seconds()),
            json.dumps(session_data)
        )
        return True

    
    def get_context(self, session_id: str, key: str) -> Optional[Any]:
        """Get value from session context"""
        session_data = self.get_session(session_id)
        if session_data and "temporary_context" in session_data:
            return session_data["temporary_context"].get(key)
        return None
    
    def clear_sensitive_data(self, session_id: str) -> bool:
        """Clear sensitive data from session"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Remove PII from temporary context
        if "temporary_context" in session_data:
            sensitive_keys = ["aadhaar_number", "pan_number", "phone", "address", "personal_info"]
            for key in sensitive_keys:
                session_data["temporary_context"].pop(key, None)
        
        # Update session
        self.redis_client.setex(
            f"session:{session_id}",
            int(self.session_timeout.total_seconds()),
            json.dumps(session_data)
        )
        
        logger.info(f"Sensitive data cleared from session: {session_id}")
        return True
    
    def end_session(self, session_id: str) -> bool:
        """End session and cleanup all data"""
        result = self.redis_client.delete(f"session:{session_id}")
        logger.info(f"Session ended: {session_id}")
        return result > 0
    
    def extend_session(self, session_id: str) -> bool:
        """Extend session timeout"""
        if self.redis_client.exists(f"session:{session_id}"):
            self.redis_client.expire(
                f"session:{session_id}",
                int(self.session_timeout.total_seconds())
            )
            return True
        return False


session_manager = SessionManager()
