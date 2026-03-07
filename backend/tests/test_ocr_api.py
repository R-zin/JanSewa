"""
Unit Tests for OCR API Endpoints

Tests all OCR and document parsing API endpoints including:
- OCR processing initiation
- Status checking
- Result retrieval
- Manual corrections
- Correction history
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the OCR dependencies before importing
sys.modules['pytesseract'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['pyzbar'] = MagicMock()
sys.modules['pyzbar.pyzbar'] = MagicMock()

from app.services.ocr_workflow import OCRWorkflow, ProcessingStatus, OCRTask
from app.services.document_parser import ParsedDocument, ExtractedField, DocumentType
from app.services.manual_correction import ManualCorrectionInterface, CorrectionAction, CorrectionSession, FieldCorrection


# Create a test app without importing main (to avoid import issues)
from fastapi import FastAPI
from app.api.v1.endpoints import ocr

app = FastAPI()
app.include_router(ocr.router, prefix="/api/v1/ocr")

client = TestClient(app)


@pytest.fixture
def mock_ocr_workflow():
    """Mock OCR workflow service"""
    with patch('app.api.v1.endpoints.ocr.ocr_workflow') as mock:
        yield mock


@pytest.fixture
def mock_manual_correction():
    """Mock manual correction service"""
    with patch('app.api.v1.endpoints.ocr.manual_correction') as mock:
        yield mock


@pytest.fixture
def sample_parsed_document():
    """Sample parsed document for testing"""
    return ParsedDocument(
        document_type=DocumentType.AADHAAR,
        fields=[
            ExtractedField(
                field_name="name",
                value="John Doe",
                confidence=0.95,
                normalized_value="John Doe"
            ),
            ExtractedField(
                field_name="aadhaar_number",
                value="1234 5678 9012",
                confidence=0.98,
                normalized_value="123456789012"
            ),
            ExtractedField(
                field_name="dob",
                value="01/01/1990",
                confidence=0.75,
                normalized_value="1990-01-01"
            )
        ],
        confidence=0.89,
        raw_text="Sample OCR text"
    )


@pytest.fixture
def sample_ocr_task():
    """Sample OCR task for testing"""
    return OCRTask(
        task_id="ocr_doc123_1234567890",
        document_id="doc123",
        image_path="documents/doc123",
        status=ProcessingStatus.COMPLETED,
        progress=100.0,
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=datetime.now(),
        retry_count=0,
        max_retries=3
    )


class TestOCRProcessEndpoint:
    """Tests for POST /api/v1/ocr/process"""
    
    def test_trigger_ocr_processing_success(self, mock_ocr_workflow):
        """Test successful OCR processing initiation"""
        # Arrange
        mock_ocr_workflow.submit_task.return_value = "ocr_doc123_1234567890"
        
        # Act
        response = client.post(
            "/api/v1/ocr/process",
            json={
                "document_id": "doc123",
                "language": "eng",
                "max_retries": 3
            }
        )
        
        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == "ocr_doc123_1234567890"
        assert data["document_id"] == "doc123"
        assert data["status"] == "queued"
        assert "initiated successfully" in data["message"]
        
        mock_ocr_workflow.submit_task.assert_called_once()
    
    def test_trigger_ocr_processing_with_defaults(self, mock_ocr_workflow):
        """Test OCR processing with default parameters"""
        # Arrange
        mock_ocr_workflow.submit_task.return_value = "ocr_doc456_1234567890"
        
        # Act
        response = client.post(
            "/api/v1/ocr/process",
            json={"document_id": "doc456"}
        )
        
        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == "ocr_doc456_1234567890"
    
    def test_trigger_ocr_processing_failure(self, mock_ocr_workflow):
        """Test OCR processing initiation failure"""
        # Arrange
        mock_ocr_workflow.submit_task.side_effect = Exception("Document not found")
        
        # Act
        response = client.post(
            "/api/v1/ocr/process",
            json={"document_id": "invalid_doc"}
        )
        
        # Assert
        assert response.status_code == 500
        assert "Failed to initiate OCR processing" in response.json()["detail"]
    
    def test_trigger_ocr_processing_invalid_request(self):
        """Test OCR processing with invalid request data"""
        # Act
        response = client.post(
            "/api/v1/ocr/process",
            json={}  # Missing required document_id
        )
        
        # Assert
        assert response.status_code == 422  # Validation error


class TestOCRStatusEndpoint:
    """Tests for GET /api/v1/ocr/{job_id}/status"""
    
    def test_get_ocr_status_queued(self, mock_ocr_workflow):
        """Test getting status of queued job"""
        # Arrange
        mock_ocr_workflow.get_task_status.return_value = {
            "task_id": "ocr_doc123_1234567890",
            "document_id": "doc123",
            "status": "queued",
            "progress": 0.0,
            "created_at": "2024-01-01T10:00:00",
            "retry_count": 0
        }
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/status")
        
        # Debug
        if response.status_code != 200:
            print(f"Response: {response.json()}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "ocr_doc123_1234567890"
        assert data["status"] == "queued"
        assert data["progress"] == 0.0
    
    def test_get_ocr_status_processing(self, mock_ocr_workflow):
        """Test getting status of processing job"""
        # Arrange
        mock_ocr_workflow.get_task_status.return_value = {
            "task_id": "ocr_doc123_1234567890",
            "document_id": "doc123",
            "status": "processing",
            "progress": 45.0,
            "created_at": "2024-01-01T10:00:00",
            "started_at": "2024-01-01T10:00:05",
            "retry_count": 0
        }
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 45.0
        assert data["started_at"] is not None
    
    def test_get_ocr_status_completed(self, mock_ocr_workflow):
        """Test getting status of completed job"""
        # Arrange
        mock_ocr_workflow.get_task_status.return_value = {
            "task_id": "ocr_doc123_1234567890",
            "document_id": "doc123",
            "status": "completed",
            "progress": 100.0,
            "created_at": "2024-01-01T10:00:00",
            "started_at": "2024-01-01T10:00:05",
            "completed_at": "2024-01-01T10:00:15",
            "processing_time": 10.0,
            "retry_count": 0,
            "result": {
                "document_type": "aadhaar",
                "fields_count": 5,
                "confidence": 0.92
            }
        }
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
        assert data["processing_time"] == 10.0
        assert data["result_summary"] is not None
    
    def test_get_ocr_status_failed(self, mock_ocr_workflow):
        """Test getting status of failed job"""
        # Arrange
        mock_ocr_workflow.get_task_status.return_value = {
            "task_id": "ocr_doc123_1234567890",
            "document_id": "doc123",
            "status": "failed",
            "progress": 30.0,
            "created_at": "2024-01-01T10:00:00",
            "started_at": "2024-01-01T10:00:05",
            "completed_at": "2024-01-01T10:00:10",
            "retry_count": 3,
            "error": "Image quality insufficient"
        }
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Image quality insufficient"
        assert data["retry_count"] == 3
    
    def test_get_ocr_status_not_found(self, mock_ocr_workflow):
        """Test getting status of non-existent job"""
        # Arrange
        mock_ocr_workflow.get_task_status.return_value = None
        
        # Act
        response = client.get("/api/v1/ocr/invalid_job_id/status")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestOCRResultEndpoint:
    """Tests for GET /api/v1/ocr/{job_id}/result"""
    
    def test_get_extracted_data_success(self, mock_ocr_workflow, mock_manual_correction, sample_parsed_document, sample_ocr_task):
        """Test successful extraction result retrieval"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = sample_parsed_document
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        
        mock_manual_correction.get_fields_for_review.return_value = [
            {
                "field_name": "name",
                "value": "John Doe",
                "confidence": 0.95,
                "normalized_value": "John Doe",
                "needs_review": False,
                "highlight_color": "green"
            },
            {
                "field_name": "aadhaar_number",
                "value": "1234 5678 9012",
                "confidence": 0.98,
                "normalized_value": "123456789012",
                "needs_review": False,
                "highlight_color": "green"
            },
            {
                "field_name": "dob",
                "value": "01/01/1990",
                "confidence": 0.75,
                "normalized_value": "1990-01-01",
                "needs_review": True,
                "highlight_color": "red"
            }
        ]
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/result")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "ocr_doc123_1234567890"
        assert data["document_type"] == "aadhaar"
        assert len(data["fields"]) == 3
        assert data["fields_needing_review"] == 1
        assert data["overall_confidence"] == 0.89
        
        # Check field details
        dob_field = next(f for f in data["fields"] if f["field_name"] == "dob")
        assert dob_field["needs_review"] is True
        assert dob_field["highlight_color"] == "red"
    
    def test_get_extracted_data_with_custom_threshold(self, mock_ocr_workflow, mock_manual_correction, sample_parsed_document, sample_ocr_task):
        """Test extraction result with custom confidence threshold"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = sample_parsed_document
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        
        mock_manual_correction.get_fields_for_review.return_value = [
            {
                "field_name": "name",
                "value": "John Doe",
                "confidence": 0.95,
                "needs_review": False,
                "highlight_color": "green"
            }
        ]
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/result?confidence_threshold=0.90")
        
        # Assert
        assert response.status_code == 200
        mock_manual_correction.get_fields_for_review.assert_called_once()
        call_args = mock_manual_correction.get_fields_for_review.call_args
        assert call_args[1]["confidence_threshold"] == 0.90
    
    def test_get_extracted_data_job_not_found(self, mock_ocr_workflow):
        """Test extraction result for non-existent job"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = None
        mock_ocr_workflow.get_task_status.return_value = None
        
        # Act
        response = client.get("/api/v1/ocr/invalid_job_id/result")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_extracted_data_job_not_completed(self, mock_ocr_workflow):
        """Test extraction result for incomplete job"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = None
        mock_ocr_workflow.get_task_status.return_value = {
            "status": "processing",
            "progress": 50.0
        }
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/result")
        
        # Assert
        assert response.status_code == 400
        assert "not completed yet" in response.json()["detail"]


class TestSubmitCorrectionsEndpoint:
    """Tests for POST /api/v1/ocr/{job_id}/corrections"""
    
    def test_submit_corrections_success(self, mock_ocr_workflow, mock_manual_correction, sample_parsed_document, sample_ocr_task):
        """Test successful correction submission"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = sample_parsed_document
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        mock_manual_correction.create_correction_session.return_value = "session_123"
        mock_manual_correction.apply_correction.return_value = True
        mock_manual_correction.complete_session.return_value = {
            "session_id": "session_123",
            "total_corrections": 2,
            "confirmed": 1,
            "edited": 1,
            "rejected": 0
        }
        
        # Act
        response = client.post(
            "/api/v1/ocr/ocr_doc123_1234567890/corrections",
            json={
                "corrections": [
                    {
                        "field_name": "name",
                        "original_value": "John Doe",
                        "corrected_value": None,
                        "action": "confirm",
                        "confidence_before": 0.95
                    },
                    {
                        "field_name": "dob",
                        "original_value": "01/01/1990",
                        "corrected_value": "01/01/1991",
                        "action": "edit",
                        "confidence_before": 0.75
                    }
                ]
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert data["corrections_applied"] == 2
        assert "Successfully applied" in data["message"]
        
        # Verify correction session was created
        mock_manual_correction.create_correction_session.assert_called_once()
        
        # Verify corrections were applied
        assert mock_manual_correction.apply_correction.call_count == 2
    
    def test_submit_corrections_with_reject_action(self, mock_ocr_workflow, mock_manual_correction, sample_parsed_document, sample_ocr_task):
        """Test correction submission with reject action"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = sample_parsed_document
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        mock_manual_correction.create_correction_session.return_value = "session_123"
        mock_manual_correction.apply_correction.return_value = True
        mock_manual_correction.complete_session.return_value = {
            "session_id": "session_123",
            "total_corrections": 1,
            "rejected": 1
        }
        
        # Act
        response = client.post(
            "/api/v1/ocr/ocr_doc123_1234567890/corrections",
            json={
                "corrections": [
                    {
                        "field_name": "invalid_field",
                        "original_value": "garbage",
                        "corrected_value": None,
                        "action": "reject",
                        "confidence_before": 0.30
                    }
                ]
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["corrections_applied"] == 1
    
    def test_submit_corrections_job_not_found(self, mock_ocr_workflow):
        """Test correction submission for non-existent job"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = None
        
        # Act
        response = client.post(
            "/api/v1/ocr/invalid_job_id/corrections",
            json={
                "corrections": [
                    {
                        "field_name": "name",
                        "original_value": "John Doe",
                        "action": "confirm",
                        "confidence_before": 0.95
                    }
                ]
            }
        )
        
        # Assert
        assert response.status_code == 404
        assert "not found or not completed" in response.json()["detail"]
    
    def test_submit_corrections_empty_list(self, mock_ocr_workflow, mock_manual_correction, sample_parsed_document, sample_ocr_task):
        """Test correction submission with empty corrections list"""
        # Arrange
        mock_ocr_workflow.get_extraction_result.return_value = sample_parsed_document
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        mock_manual_correction.create_correction_session.return_value = "session_123"
        mock_manual_correction.complete_session.return_value = {
            "session_id": "session_123",
            "total_corrections": 0
        }
        
        # Act
        response = client.post(
            "/api/v1/ocr/ocr_doc123_1234567890/corrections",
            json={"corrections": []}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["corrections_applied"] == 0


class TestCorrectionHistoryEndpoint:
    """Tests for GET /api/v1/ocr/{job_id}/corrections"""
    
    def test_get_correction_history_success(self, mock_ocr_workflow, mock_manual_correction, sample_ocr_task):
        """Test successful correction history retrieval"""
        # Arrange
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        
        correction_session = CorrectionSession(
            session_id="session_123",
            document_id="doc123",
            document_type="aadhaar",
            corrections=[
                FieldCorrection(
                    field_name="name",
                    original_value="John Doe",
                    corrected_value=None,
                    action=CorrectionAction.CONFIRM,
                    confidence_before=0.95,
                    timestamp=datetime.now()
                ),
                FieldCorrection(
                    field_name="dob",
                    original_value="01/01/1990",
                    corrected_value="01/01/1991",
                    action=CorrectionAction.EDIT,
                    confidence_before=0.75,
                    timestamp=datetime.now()
                )
            ],
            created_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        mock_manual_correction.correction_history = {"session_123": correction_session}
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/corrections")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert data["document_id"] == "doc123"
        assert data["document_type"] == "aadhaar"
        assert len(data["corrections"]) == 2
        assert data["summary"] is not None
        assert data["summary"]["total_corrections"] == 2
    
    def test_get_correction_history_not_found(self, mock_ocr_workflow):
        """Test correction history for non-existent job"""
        # Arrange
        mock_ocr_workflow.tasks = {}
        
        # Act
        response = client.get("/api/v1/ocr/invalid_job_id/corrections")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_correction_history_no_corrections(self, mock_ocr_workflow, mock_manual_correction, sample_ocr_task):
        """Test correction history when no corrections exist"""
        # Arrange
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        mock_manual_correction.correction_history = {}
        
        # Act
        response = client.get("/api/v1/ocr/ocr_doc123_1234567890/corrections")
        
        # Assert
        assert response.status_code == 404
        assert "No correction history found" in response.json()["detail"]


class TestAdditionalEndpoints:
    """Tests for additional utility endpoints"""
    
    def test_get_processing_statistics(self, mock_ocr_workflow):
        """Test getting processing statistics"""
        # Arrange
        mock_ocr_workflow.get_processing_statistics.return_value = {
            "total_tasks": 100,
            "completed": 85,
            "failed": 10,
            "processing": 3,
            "queued": 2,
            "success_rate": 0.85,
            "average_processing_time": 12.5,
            "average_confidence": 0.88
        }
        
        # Act
        response = client.get("/api/v1/ocr/statistics")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 100
        assert data["success_rate"] == 0.85
        assert data["average_confidence"] == 0.88
    
    def test_get_extraction_history(self, mock_ocr_workflow):
        """Test getting extraction history"""
        # Arrange
        mock_ocr_workflow.get_extraction_history.return_value = [
            {
                "task_id": "ocr_doc123_1234567890",
                "document_id": "doc123",
                "document_type": "aadhaar",
                "fields_extracted": 5,
                "confidence": 0.92,
                "timestamp": "2024-01-01T10:00:00",
                "processing_time": 10.5
            }
        ]
        
        # Act
        response = client.get("/api/v1/ocr/history")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_id"] == "doc123"
    
    def test_get_extraction_history_with_filter(self, mock_ocr_workflow):
        """Test getting extraction history with document filter"""
        # Arrange
        mock_ocr_workflow.get_extraction_history.return_value = []
        
        # Act
        response = client.get("/api/v1/ocr/history?document_id=doc123&limit=10")
        
        # Assert
        assert response.status_code == 200
        mock_ocr_workflow.get_extraction_history.assert_called_once_with(
            document_id="doc123",
            limit=10
        )
    
    def test_retry_failed_job_success(self, mock_ocr_workflow, sample_ocr_task):
        """Test successful job retry"""
        # Arrange
        mock_ocr_workflow.retry_failed_task.return_value = True
        mock_ocr_workflow.tasks = {"ocr_doc123_1234567890": sample_ocr_task}
        
        # Act
        response = client.post("/api/v1/ocr/ocr_doc123_1234567890/retry")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "ocr_doc123_1234567890"
        assert data["status"] == "queued"
        assert "retry initiated" in data["message"]
    
    def test_retry_failed_job_not_found(self, mock_ocr_workflow):
        """Test retry for non-existent job"""
        # Arrange
        mock_ocr_workflow.retry_failed_task.return_value = False
        mock_ocr_workflow.get_task_status.return_value = None
        
        # Act
        response = client.post("/api/v1/ocr/invalid_job_id/retry")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_retry_failed_job_wrong_status(self, mock_ocr_workflow):
        """Test retry for job not in failed state"""
        # Arrange
        mock_ocr_workflow.retry_failed_task.return_value = False
        mock_ocr_workflow.get_task_status.return_value = {
            "status": "completed"
        }
        
        # Act
        response = client.post("/api/v1/ocr/ocr_doc123_1234567890/retry")
        
        # Assert
        assert response.status_code == 400
        assert "Cannot retry job" in response.json()["detail"]
    
    def test_get_learning_insights(self, mock_manual_correction):
        """Test getting learning insights"""
        # Arrange
        mock_manual_correction.get_learning_insights.return_value = {
            "total_corrections": 50,
            "field_error_rates": {
                "name": 0.1,
                "dob": 0.3,
                "address": 0.4
            },
            "fields_needing_improvement": ["address", "dob"],
            "low_confidence_accuracy": 0.65
        }
        
        # Act
        response = client.get("/api/v1/ocr/learning/insights")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_corrections"] == 50
        assert "address" in data["fields_needing_improvement"]
        assert data["low_confidence_accuracy"] == 0.65


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
