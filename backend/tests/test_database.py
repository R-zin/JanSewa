import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base, get_db
from app.core.config import settings


def test_database_connection():
    """Test database connection"""
    # Use test database URL
    test_db_url = settings.DATABASE_URL.replace("/govservices", "/test_govservices")
    engine = create_engine(test_db_url)
    
    try:
        # Test connection
        with engine.connect() as conn:
            assert conn is not None
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_get_db_dependency():
    """Test database session dependency"""
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    db.close()
