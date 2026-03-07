from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    language_preference = Column(String, default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    service_requests = relationship("ServiceRequest", back_populates="user")


class Session(Base):
    """Session model for tracking user sessions"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    context_data = Column(JSON)
    
    user = relationship("User", back_populates="sessions")


class Document(Base):
    """Document storage model"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    document_type = Column(String, nullable=False)
    category = Column(String)
    file_name = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_size = Column(Integer)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    expiration_date = Column(DateTime(timezone=True))
    expiration_status = Column(String, default="no_expiration")  # no_expiration, valid, expiring_soon, expired, archived
    is_digilocker = Column(Boolean, default=False)
    digilocker_metadata = Column(JSON)
    extracted_data = Column(JSON)
    extraction_confidence = Column(Float)
    
    user = relationship("User", back_populates="documents")


class ServiceRequest(Base):
    """Service request tracking model"""
    __tablename__ = "service_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(String, nullable=False)
    service_name = Column(String, nullable=False)
    status = Column(String, default="submitted")
    reference_number = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completion_date = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="service_requests")


class Credential(Base):
    """Encrypted credential storage for portal authentication"""
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    portal_name = Column(String, nullable=False)
    encrypted_username = Column(Text, nullable=False)
    encrypted_password = Column(Text, nullable=False)
    auth_method = Column(String, default="username_password")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AutomationSession(Base):
    """Browser automation session tracking"""
    __tablename__ = "automation_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(String, nullable=False)
    status = Column(String, default="in_progress")
    current_step = Column(Integer, default=0)
    session_state = Column(JSON)
    action_log = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class AuditLogEntry(Base):
    """
    Audit log database model for document operations
    
    This table is append-only - no updates or deletes allowed
    Protected by database triggers for immutability
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False)  # success, failure, partial
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON string with additional context
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_user_action', 'user_id', 'action'),
        Index('idx_document_timestamp', 'document_id', 'timestamp'),
    )
