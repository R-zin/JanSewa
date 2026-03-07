import pytest
from app.core.config import settings


def test_config_loading():
    """Test configuration loading"""
    assert settings.PROJECT_NAME == "Government Services Assistant"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.DATABASE_URL is not None
    assert settings.REDIS_URL is not None


def test_aws_config():
    """Test AWS configuration"""
    assert settings.AWS_REGION is not None
    assert settings.S3_BUCKET_NAME is not None


def test_security_config():
    """Test security configuration"""
    assert settings.SECRET_KEY is not None
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_document_storage_limits():
    """Test document storage configuration"""
    assert settings.MAX_DOCUMENT_SIZE_MB == 10
    assert settings.MAX_STORAGE_PER_USER_MB == 100
