"""
Tests for DigiLocker document validation functionality
"""

import pytest
from datetime import datetime
from app.services.digilocker_client import (
    DigiLockerClient,
    DigiLockerDocument,
    DocumentCategory,
    ValidationStatus,
    ValidationError
)
from app.services.digilocker_auth import DigiLockerAuthenticator
from app.services.encryption_service import EncryptionService


@pytest.fixture
def encryption_service():
    """Create encryption service"""
    return EncryptionService()


@pytest.fixture
def authenticator(encryption_service):
    """Create DigiLocker authenticator"""
    return DigiLockerAuthenticator(
        client_id="test_client",
        client_secret="test_secret",
        redirect_uri="http://localhost/callback",
        encryption_service=encryption_service
    )


@pytest.fixture
def digilocker_client(authenticator):
    """Create DigiLocker client"""
    return DigiLockerClient(authenticator)


class TestDigitalSignatureVerification:
    """Test digital signature verification"""
    
    def test_generate_and_verify_signature(self, digilocker_client):
        """Test signature generation and verification"""
        # Generate test document content
        document_content = b"Test document content"
        
        # Generate signature
        signature = digilocker_client._generate_test_signature(document_content)
        
        # Verify signature
        is_valid = digilocker_client.verify_digital_signature(
            document_content,
            signature,
            "test_doc_001"
        )
        
        assert is_valid is True
    
    def test_verify_invalid_signature(self, digilocker_client):
        """Test verification fails for invalid signature"""
        document_content = b"Test document content"
        invalid_signature = "invalid_signature_base64"
        
        is_valid = digilocker_client.verify_digital_signature(
            document_content,
            invalid_signature,
            "test_doc_001"
        )
        
        assert is_valid is False
    
    def test_verify_tampered_content(self, digilocker_client):
        """Test verification fails for tampered content"""
        original_content = b"Original content"
        tampered_content = b"Tampered content"
        
        # Generate signature for original content
        signature = digilocker_client._generate_test_signature(original_content)
        
        # Try to verify with tampered content
        is_valid = digilocker_client.verify_digital_signature(
            tampered_content,
            signature,
            "test_doc_001"
        )
        
        assert is_valid is False


class TestDocumentAuthenticity:
    """Test document authenticity validation"""
    
    def test_validate_document_with_valid_signature(self, digilocker_client):
        """Test validation succeeds for document with valid signature"""
        document_content = b"Valid document content"
        signature = digilocker_client._generate_test_signature(document_content)
        
        document = DigiLockerDocument(
            doc_id="test_001",
            doc_name="Test Document",
            doc_type="ADHAR",
            issuer="UIDAI",
            issue_date=datetime(2020, 1, 1),
            category=DocumentCategory.AADHAAR,
            size_bytes=1000,
            mime_type="application/pdf",
            uri="test://uri",
            signature=signature
        )
        
        status = digilocker_client.validate_document_authenticity(
            document,
            document_content
        )
        
        assert status == ValidationStatus.VALID
        assert document.validation_status == ValidationStatus.VALID
        assert document.validation_error is None
    
    def test_validate_document_without_signature(self, digilocker_client):
        """Test validation fails for document without signature"""
        document_content = b"Document content"
        
        document = DigiLockerDocument(
            doc_id="test_002",
            doc_name="Test Document",
            doc_type="ADHAR",
            issuer="UIDAI",
            issue_date=datetime(2020, 1, 1),
            category=DocumentCategory.AADHAAR,
            size_bytes=1000,
            mime_type="application/pdf",
            uri="test://uri",
            signature=None
        )
        
        status = digilocker_client.validate_document_authenticity(
            document,
            document_content
        )
        
        assert status == ValidationStatus.INVALID
        assert document.validation_status == ValidationStatus.INVALID
        assert document.validation_error is not None
        assert document.validation_error.error_code == "MISSING_SIGNATURE"
    
    def test_validate_document_with_invalid_signature(self, digilocker_client):
        """Test validation fails for document with invalid signature"""
        document_content = b"Document content"
        
        document = DigiLockerDocument(
            doc_id="test_003",
            doc_name="Test Document",
            doc_type="ADHAR",
            issuer="UIDAI",
            issue_date=datetime(2020, 1, 1),
            category=DocumentCategory.AADHAAR,
            size_bytes=1000,
            mime_type="application/pdf",
            uri="test://uri",
            signature="invalid_signature"
        )
        
        status = digilocker_client.validate_document_authenticity(
            document,
            document_content
        )
        
        assert status == ValidationStatus.INVALID
        assert document.validation_status == ValidationStatus.INVALID
        assert document.validation_error is not None
        assert document.validation_error.error_code == "INVALID_SIGNATURE"
    
    def test_validate_document_with_unrecognized_issuer(self, digilocker_client):
        """Test validation fails for unrecognized issuer"""
        document_content = b"Document content"
        signature = digilocker_client._generate_test_signature(document_content)
        
        document = DigiLockerDocument(
            doc_id="test_004",
            doc_name="Test Document",
            doc_type="ADHAR",
            issuer="Unknown Issuer",
            issue_date=datetime(2020, 1, 1),
            category=DocumentCategory.AADHAAR,
            size_bytes=1000,
            mime_type="application/pdf",
            uri="test://uri",
            signature=signature
        )
        
        status = digilocker_client.validate_document_authenticity(
            document,
            document_content
        )
        
        assert status == ValidationStatus.INVALID
        assert document.validation_status == ValidationStatus.INVALID
        assert document.validation_error is not None
        assert document.validation_error.error_code == "UNRECOGNIZED_ISSUER"
    
    def test_validate_document_with_invalid_type(self, digilocker_client):
        """Test validation fails for invalid document type"""
        document_content = b"Document content"
        signature = digilocker_client._generate_test_signature(document_content)
        
        document = DigiLockerDocument(
            doc_id="test_005",
            doc_name="Test Document",
            doc_type="INVALID_TYPE",
            issuer="UIDAI",
            issue_date=datetime(2020, 1, 1),
            category=DocumentCategory.AADHAAR,
            size_bytes=1000,
            mime_type="application/pdf",
            uri="test://uri",
            signature=signature
        )
        
        status = digilocker_client.validate_document_authenticity(
            document,
            document_content
        )
        
        assert status == ValidationStatus.INVALID
        assert document.validation_status == ValidationStatus.INVALID
        assert document.validation_error is not None
        assert document.validation_error.error_code == "INVALID_DOCUMENT_TYPE"


class TestDocumentImportWithValidation:
    """Test document import with validation"""
    
    @pytest.mark.asyncio
    async def test_import_valid_document(self, digilocker_client):
        """Test importing a valid document succeeds"""
        user_id = "test_user"
        
        # Mock authentication by directly setting a token
        from app.services.digilocker_auth import DigiLockerToken
        from datetime import datetime
        
        digilocker_client.authenticator.user_tokens[user_id] = DigiLockerToken(
            access_token='test_token',
            refresh_token='test_refresh',
            token_type='Bearer',
            expires_at=datetime(2099, 1, 1),
            scope='public'
        )
        
        # Override get_access_token to bypass encryption
        digilocker_client.authenticator.get_access_token = lambda uid: 'test_token' if uid == user_id else None
        
        # List documents to populate cache
        await digilocker_client.list_documents(user_id)
        
        # Import document
        result = await digilocker_client.import_document(user_id, "dl_aadhaar_001")
        
        assert result["doc_id"] == "dl_aadhaar_001"
        assert result["validation_status"] == ValidationStatus.VALID
        assert result["signature_verified"] is True
    
    @pytest.mark.asyncio
    async def test_bulk_import_with_validation(self, digilocker_client):
        """Test bulk import handles validation correctly"""
        user_id = "test_user"
        
        # Mock authentication
        from app.services.digilocker_auth import DigiLockerToken
        from datetime import datetime
        
        digilocker_client.authenticator.user_tokens[user_id] = DigiLockerToken(
            access_token='test_token',
            refresh_token='test_refresh',
            token_type='Bearer',
            expires_at=datetime(2099, 1, 1),
            scope='public'
        )
        
        # Override get_access_token to bypass encryption
        digilocker_client.authenticator.get_access_token = lambda uid: 'test_token' if uid == user_id else None
        
        # List documents to populate cache
        await digilocker_client.list_documents(user_id)
        
        # Bulk import
        doc_ids = ["dl_aadhaar_001", "dl_pan_001", "dl_dl_001"]
        results = await digilocker_client.bulk_import(user_id, doc_ids)
        
        assert results["total"] == 3
        assert len(results["successful"]) == 3
        assert len(results["failed"]) == 0
        
        # Check all have validation status
        for doc in results["successful"]:
            assert doc["validation_status"] == ValidationStatus.VALID
            assert doc["signature_verified"] is True


class TestDocumentMetadataWithValidation:
    """Test document metadata includes validation status"""
    
    @pytest.mark.asyncio
    async def test_metadata_includes_validation_status(self, digilocker_client):
        """Test metadata includes validation information"""
        user_id = "test_user"
        
        # Mock authentication
        from app.services.digilocker_auth import DigiLockerToken
        from datetime import datetime
        
        digilocker_client.authenticator.user_tokens[user_id] = DigiLockerToken(
            access_token='test_token',
            refresh_token='test_refresh',
            token_type='Bearer',
            expires_at=datetime(2099, 1, 1),
            scope='public'
        )
        
        # Override get_access_token to bypass encryption
        digilocker_client.authenticator.get_access_token = lambda uid: 'test_token' if uid == user_id else None
        
        # List documents
        await digilocker_client.list_documents(user_id)
        
        # Get metadata
        metadata = digilocker_client.get_document_metadata(user_id, "dl_aadhaar_001")
        
        assert metadata is not None
        assert "validation_status" in metadata
        assert "has_signature" in metadata
        assert metadata["has_signature"] is True
