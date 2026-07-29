from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Government Services Assistant"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@db:5432/govservices"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # AWS Configuration
    AWS_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "gov-services-documents"
    
    # Google AI
    GOOGLE_API_KEY: str = ""
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Document Storage
    MAX_DOCUMENT_SIZE_MB: int = 10
    MAX_STORAGE_PER_USER_MB: int = 100
    
    # DigiLocker
    DIGILOCKER_CLIENT_ID: str = ""
    DIGILOCKER_CLIENT_SECRET: str = ""
    DIGILOCKER_REDIRECT_URI: str = "http://localhost:8000/api/v1/digilocker/callback"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_ROTATION_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_ROTATION_BACKUP_COUNT: int = 5
    
    # OCR Configuration
    OCR_ENGINE: str = "auto"  # Options: auto, textract, tesseract
    OCR_USE_TEXTRACT: bool = True  # Enable AWS Textract for production
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
