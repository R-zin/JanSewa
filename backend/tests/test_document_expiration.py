"""
Unit tests for document expiration and archival functionality
"""

import pytest
from datetime import datetime, timedelta
from app.services.document_storage import DocumentStorage, ExpirationWarning


class TestDocumentExpiration:
    """Test document expiration detection and archival"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.storage = DocumentStorage()
    
    def test_is_document_expired_with_expired_date(self):
        """Test expired document detection"""
        expired_date = datetime.utcnow() - timedelta(days=10)
        assert self.storage.is_document_expired(expired_date) is True
    
    def test_is_document_expired_with_future_date(self):
        """Test non-expired document detection"""
        future_date = datetime.utcnow() + timedelta(days=10)
        assert self.storage.is_document_expired(future_date) is False
    
    def test_is_document_expired_with_none(self):
        """Test document with no expiration date"""
        assert self.storage.is_document_expired(None) is False
    
    def test_get_days_until_expiration(self):
        """Test days until expiration calculation"""
        future_date = datetime.utcnow() + timedelta(days=15)
        days = self.storage.get_days_until_expiration(future_date)
        # Allow for slight timing differences
        assert 14 <= days <= 15
    
    def test_get_days_until_expiration_with_none(self):
        """Test days calculation with no expiration date"""
        assert self.storage.get_days_until_expiration(None) is None
    
    def test_should_show_expiration_warning_within_30_days(self):
        """Test warning shown for documents expiring within 30 days"""
        expiring_date = datetime.utcnow() + timedelta(days=20)
        assert self.storage.should_show_expiration_warning(expiring_date) is True
    
    def test_should_show_expiration_warning_beyond_30_days(self):
        """Test no warning for documents expiring beyond 30 days"""
        future_date = datetime.utcnow() + timedelta(days=40)
        assert self.storage.should_show_expiration_warning(future_date) is False
    
    def test_should_show_expiration_warning_already_expired(self):
        """Test no warning for already expired documents"""
        expired_date = datetime.utcnow() - timedelta(days=5)
        assert self.storage.should_show_expiration_warning(expired_date) is False
    
    def test_should_archive_document_expired_90_days(self):
        """Test archival for documents expired 90+ days"""
        old_expired_date = datetime.utcnow() - timedelta(days=100)
        assert self.storage.should_archive_document(old_expired_date) is True
    
    def test_should_archive_document_recently_expired(self):
        """Test no archival for recently expired documents"""
        recent_expired_date = datetime.utcnow() - timedelta(days=30)
        assert self.storage.should_archive_document(recent_expired_date) is False
    
    def test_should_archive_document_with_none(self):
        """Test archival check with no expiration date"""
        assert self.storage.should_archive_document(None) is False
    
    def test_generate_expiration_warning(self):
        """Test expiration warning generation"""
        expiration_date = datetime.utcnow() + timedelta(days=15)
        warning = self.storage.generate_expiration_warning(
            document_id=123,
            document_name="test_doc.pdf",
            expiration_date=expiration_date
        )
        
        assert isinstance(warning, ExpirationWarning)
        assert warning.document_id == 123
        assert warning.document_name == "test_doc.pdf"
        # Allow for slight timing differences
        assert 14 <= warning.days_until_expiration <= 15
    
    def test_get_expiration_warnings_filters_correctly(self):
        """Test expiration warnings are generated only for expiring documents"""
        documents = [
            {
                "id": 1,
                "file_name": "expiring_soon.pdf",
                "expiration_date": datetime.utcnow() + timedelta(days=20)
            },
            {
                "id": 2,
                "file_name": "valid.pdf",
                "expiration_date": datetime.utcnow() + timedelta(days=60)
            },
            {
                "id": 3,
                "file_name": "expired.pdf",
                "expiration_date": datetime.utcnow() - timedelta(days=10)
            },
            {
                "id": 4,
                "file_name": "no_expiration.pdf",
                "expiration_date": None
            }
        ]
        
        warnings = self.storage.get_expiration_warnings(documents)
        
        # Only the first document should generate a warning
        assert len(warnings) == 1
        assert warnings[0].document_id == 1
    
    def test_get_document_expiration_status_no_expiration(self):
        """Test status for document with no expiration date"""
        status = self.storage.get_document_expiration_status(None)
        assert status == "no_expiration"
    
    def test_get_document_expiration_status_valid(self):
        """Test status for valid document"""
        future_date = datetime.utcnow() + timedelta(days=60)
        status = self.storage.get_document_expiration_status(future_date)
        assert status == "valid"
    
    def test_get_document_expiration_status_expiring_soon(self):
        """Test status for document expiring soon"""
        expiring_date = datetime.utcnow() + timedelta(days=20)
        status = self.storage.get_document_expiration_status(expiring_date)
        assert status == "expiring_soon"
    
    def test_get_document_expiration_status_expired(self):
        """Test status for expired document"""
        expired_date = datetime.utcnow() - timedelta(days=30)
        status = self.storage.get_document_expiration_status(expired_date)
        assert status == "expired"
    
    def test_get_document_expiration_status_archived(self):
        """Test status for document that should be archived"""
        old_expired_date = datetime.utcnow() - timedelta(days=100)
        status = self.storage.get_document_expiration_status(old_expired_date)
        assert status == "archived"
    
    def test_update_document_metadata_with_expiration_status(self):
        """Test metadata update with expiration status"""
        expiration_date = datetime.utcnow() + timedelta(days=20)
        metadata = {
            "document_type": "passport",
            "file_name": "passport.pdf",
            "expiration_date": expiration_date
        }
        
        updated = self.storage.update_document_metadata_with_expiration_status(metadata)
        
        assert "expiration_status" in updated
        assert updated["expiration_status"] == "expiring_soon"
    
    def test_expiration_warning_to_dict(self):
        """Test ExpirationWarning serialization"""
        expiration_date = datetime.utcnow() + timedelta(days=15)
        warning = ExpirationWarning(
            document_id=123,
            document_name="test.pdf",
            expiration_date=expiration_date,
            days_until_expiration=15
        )
        
        result = warning.to_dict()
        
        assert result["document_id"] == 123
        assert result["document_name"] == "test.pdf"
        assert result["days_until_expiration"] == 15
        assert "expiration_date" in result


class TestExpirationScheduler:
    """Test expiration scheduler functionality"""
    
    @pytest.mark.asyncio
    async def test_check_user_document_expirations(self):
        """Test user-specific expiration checking"""
        from app.services.expiration_scheduler import expiration_scheduler
        
        user_documents = [
            {
                "id": 1,
                "file_name": "expiring.pdf",
                "expiration_date": datetime.utcnow() + timedelta(days=20)
            },
            {
                "id": 2,
                "file_name": "expired.pdf",
                "expiration_date": datetime.utcnow() - timedelta(days=10)
            }
        ]
        
        result = await expiration_scheduler.check_user_document_expirations(
            user_id=1,
            user_documents=user_documents
        )
        
        assert result["user_id"] == 1
        assert result["total_warnings"] == 1
        assert len(result["expiring_soon_documents"]) == 1
        assert len(result["expired_documents"]) == 1
