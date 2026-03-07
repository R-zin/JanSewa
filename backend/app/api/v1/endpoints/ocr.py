"""
OCR and Document Parsing API Endpoints

Provides REST API for OCR processing, data extraction, and manual corrections.
Implements Requirements 20.1, 20.15, 20.13, 20.14
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from app.services.ocr_workflow import OCRWorkflow, ProcessingStatus
from app.services.ocr_engine_hybrid import hybrid_ocr_engine
from app.services.document_parser import DocumentParser, DocumentType
from app.services.manual_correction import ManualCorrectionInterface, CorrectionAction

router = APIRouter()

# Initialize services
ocr_workflow = OCRWorkflow()
document_parser = DocumentParser()
manual_correction = ManualCorrectionInterface()


# Request/Response Models

class OCRProcessRequest(BaseModel):
    """Request to process a document with OCR"""
    document_id: str = Field(..., description="ID of the document to process")
    language: str = Field(default="eng", description="OCR language code (eng, hin, tam, tel)")
    max_retries: int = Field(default=3, description="Maximum retry attempts on failure")


class OCRProcessResponse(BaseModel):
    """Response from OCR process initiation"""
    job_id: str = Field(..., description="Unique job ID for tracking")
    document_id: str
    status: str = Field(..., description="Initial status (queued)")
    message: str


class OCRStatusResponse(BaseModel):
    """OCR job status response"""
    job_id: str
    document_id: str
    status: str = Field(..., description="Current status: queued, processing, completed, failed, retrying")
    progress: float = Field(..., description="Progress percentage (0-100)")
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time: Optional[float] = None
    retry_count: int
    error: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None


class ExtractedFieldResponse(BaseModel):
    """Extracted field data"""
    field_name: str
    value: str
    confidence: float
    normalized_value: Optional[str] = None
    needs_review: bool = Field(..., description="True if confidence below threshold")
    highlight_color: str = Field(..., description="Color for UI highlighting: green, yellow, red")


class OCRResultResponse(BaseModel):
    """Complete OCR extraction result"""
    job_id: str
    document_id: str
    document_type: str
    fields: List[ExtractedFieldResponse]
    overall_confidence: float
    extraction_timestamp: str
    fields_needing_review: int = Field(..., description="Count of low-confidence fields")


class CorrectionRequest(BaseModel):
    """Request to apply manual correction"""
    field_name: str
    original_value: str
    corrected_value: Optional[str] = None
    action: CorrectionAction = Field(..., description="Action: confirm, edit, or reject")
    confidence_before: float


class CorrectionBatchRequest(BaseModel):
    """Batch correction request"""
    corrections: List[CorrectionRequest]


class CorrectionResponse(BaseModel):
    """Response from correction submission"""
    session_id: str
    corrections_applied: int
    message: str


class CorrectionHistoryResponse(BaseModel):
    """Correction history for a job"""
    session_id: str
    document_id: str
    document_type: str
    corrections: List[Dict[str, Any]]
    created_at: str
    completed_at: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None


# API Endpoints

@router.post("/process", response_model=OCRProcessResponse, status_code=202)
async def trigger_ocr_processing(
    request: OCRProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger OCR processing on a document (Requirement 20.1)
    
    Initiates asynchronous OCR processing and returns a job ID for tracking.
    The processing happens in the background with progress updates available
    via the status endpoint.
    
    Args:
        request: OCR processing request with document ID and options
        background_tasks: FastAPI background tasks for async processing
    
    Returns:
        Job ID and initial status
    
    Raises:
        HTTPException: If document not found or processing cannot be initiated
    """
    try:
        # Submit OCR task to workflow
        job_id = ocr_workflow.submit_task(
            document_id=request.document_id,
            image_path=f"documents/{request.document_id}",  # Placeholder path
            max_retries=request.max_retries
        )
        
        # Schedule background processing
        background_tasks.add_task(ocr_workflow.process_task, job_id)
        
        return OCRProcessResponse(
            job_id=job_id,
            document_id=request.document_id,
            status="queued",
            message="OCR processing initiated successfully. Use job_id to check status."
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate OCR processing: {str(e)}"
        )


@router.get("/{job_id}/status", response_model=OCRStatusResponse)
async def get_ocr_status(job_id: str):
    """
    Get OCR processing status (Requirement 20.15)
    
    Returns the current status of an OCR job including progress,
    timing information, and result summary if completed.
    
    Args:
        job_id: Unique job identifier returned from /process endpoint
    
    Returns:
        Current job status with progress and timing details
    
    Raises:
        HTTPException: If job not found
    """
    try:
        status = ocr_workflow.get_task_status(job_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"OCR job {job_id} not found"
            )
        
        # Map task_id to job_id for response
        if 'task_id' in status and 'job_id' not in status:
            status['job_id'] = status['task_id']
        
        # Map result to result_summary for response
        if 'result' in status and 'result_summary' not in status:
            status['result_summary'] = status.pop('result')
        
        return OCRStatusResponse(**status)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve status: {str(e)}"
        )


@router.get("/{job_id}/result", response_model=OCRResultResponse)
async def get_extracted_data(job_id: str, confidence_threshold: float = 0.85):
    """
    Get extracted data from completed OCR job (Requirement 20.15)
    
    Returns structured data extracted from the document with confidence
    scores and review flags for low-confidence fields.
    
    Args:
        job_id: Unique job identifier
        confidence_threshold: Threshold for flagging fields needing review (default: 0.85)
    
    Returns:
        Extracted fields with confidence scores and review flags
    
    Raises:
        HTTPException: If job not found or not completed
    """
    try:
        # Get extraction result
        result = ocr_workflow.get_extraction_result(job_id)
        
        if not result:
            # Check if job exists but not completed
            status = ocr_workflow.get_task_status(job_id)
            if not status:
                raise HTTPException(
                    status_code=404,
                    detail=f"OCR job {job_id} not found"
                )
            elif status["status"] != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"OCR job is {status['status']}, not completed yet"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Extraction result not available"
                )
        
        # Get fields for review with highlighting
        fields_with_review = manual_correction.get_fields_for_review(
            extracted_fields=[
                {
                    "field_name": f.field_name,
                    "value": f.value,
                    "confidence": f.confidence,
                    "normalized_value": f.normalized_value
                }
                for f in result.fields
            ],
            confidence_threshold=confidence_threshold
        )
        
        # Convert to response format
        fields_response = [
            ExtractedFieldResponse(
                field_name=f["field_name"],
                value=f["value"],
                confidence=f["confidence"],
                normalized_value=f.get("normalized_value"),
                needs_review=f["needs_review"],
                highlight_color=f["highlight_color"]
            )
            for f in fields_with_review
        ]
        
        fields_needing_review = sum(1 for f in fields_response if f.needs_review)
        
        return OCRResultResponse(
            job_id=job_id,
            document_id=ocr_workflow.tasks[job_id].document_id,
            document_type=result.document_type,
            fields=fields_response,
            overall_confidence=result.confidence,
            extraction_timestamp=datetime.now().isoformat(),
            fields_needing_review=fields_needing_review
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve extraction result: {str(e)}"
        )


@router.post("/{job_id}/corrections", response_model=CorrectionResponse)
async def submit_manual_corrections(
    job_id: str,
    request: CorrectionBatchRequest
):
    """
    Submit manual corrections for extracted data (Requirement 20.13, 20.14)
    
    Allows users to review and correct OCR-extracted fields. Corrections
    are stored for learning and improving future extractions.
    
    Args:
        job_id: OCR job identifier
        request: Batch of corrections to apply
    
    Returns:
        Confirmation with number of corrections applied
    
    Raises:
        HTTPException: If job not found or corrections cannot be applied
    """
    try:
        # Verify job exists and is completed
        result = ocr_workflow.get_extraction_result(job_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"OCR job {job_id} not found or not completed"
            )
        
        # Get document info
        task = ocr_workflow.tasks.get(job_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task information not found for job {job_id}"
            )
        
        # Create correction session
        session_id = manual_correction.create_correction_session(
            document_id=task.document_id,
            document_type=result.document_type,
            extracted_fields=[
                {
                    "field_name": f.field_name,
                    "value": f.value,
                    "confidence": f.confidence
                }
                for f in result.fields
            ]
        )
        
        # Apply each correction
        corrections_applied = 0
        for correction in request.corrections:
            success = manual_correction.apply_correction(
                session_id=session_id,
                field_name=correction.field_name,
                original_value=correction.original_value,
                corrected_value=correction.corrected_value,
                action=correction.action,
                confidence_before=correction.confidence_before
            )
            if success:
                corrections_applied += 1
        
        # Complete the session
        summary = manual_correction.complete_session(session_id)
        
        return CorrectionResponse(
            session_id=session_id,
            corrections_applied=corrections_applied,
            message=f"Successfully applied {corrections_applied} corrections"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply corrections: {str(e)}"
        )


@router.get("/{job_id}/corrections", response_model=CorrectionHistoryResponse)
async def get_correction_history(job_id: str):
    """
    Get correction history for an OCR job (Requirement 20.14)
    
    Returns all manual corrections made for a specific OCR job,
    including the actions taken and final corrected values.
    
    Args:
        job_id: OCR job identifier
    
    Returns:
        Complete correction history with summary
    
    Raises:
        HTTPException: If job not found or no corrections exist
    """
    try:
        # Find correction session for this job
        task = ocr_workflow.tasks.get(job_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"OCR job {job_id} not found"
            )
        
        # Search for correction sessions by document ID
        matching_sessions = [
            session for session in manual_correction.correction_history.values()
            if session.document_id == task.document_id
        ]
        
        if not matching_sessions:
            raise HTTPException(
                status_code=404,
                detail=f"No correction history found for job {job_id}"
            )
        
        # Get the most recent session
        session = max(matching_sessions, key=lambda s: s.created_at)
        
        # Format corrections
        corrections_list = [
            {
                "field_name": c.field_name,
                "original_value": c.original_value,
                "corrected_value": c.corrected_value,
                "action": c.action,
                "confidence_before": c.confidence_before,
                "timestamp": c.timestamp.isoformat()
            }
            for c in session.corrections
        ]
        
        # Get summary if session is completed
        summary = None
        if session.completed_at:
            summary = {
                "total_corrections": len(session.corrections),
                "confirmed": sum(1 for c in session.corrections if c.action == CorrectionAction.CONFIRM),
                "edited": sum(1 for c in session.corrections if c.action == CorrectionAction.EDIT),
                "rejected": sum(1 for c in session.corrections if c.action == CorrectionAction.REJECT),
                "duration_seconds": (session.completed_at - session.created_at).total_seconds()
            }
        
        return CorrectionHistoryResponse(
            session_id=session.session_id,
            document_id=session.document_id,
            document_type=session.document_type,
            corrections=corrections_list,
            created_at=session.created_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            summary=summary
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve correction history: {str(e)}"
        )


# Additional utility endpoints

@router.get("/statistics", response_model=Dict[str, Any])
async def get_processing_statistics():
    """
    Get overall OCR processing statistics
    
    Returns aggregate statistics about OCR processing including
    success rates, average processing time, and confidence scores.
    
    Returns:
        Statistics dictionary with processing metrics
    """
    try:
        stats = ocr_workflow.get_processing_statistics()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_extraction_history(
    document_id: Optional[str] = None,
    limit: int = 50
):
    """
    Get extraction history with optional filtering
    
    Returns historical OCR extraction records for auditing and
    tracking purposes.
    
    Args:
        document_id: Optional filter by specific document
        limit: Maximum number of records to return (default: 50)
    
    Returns:
        List of extraction history records
    """
    try:
        history = ocr_workflow.get_extraction_history(
            document_id=document_id,
            limit=limit
        )
        return history
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.post("/{job_id}/retry", response_model=OCRProcessResponse)
async def retry_failed_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Retry a failed OCR job
    
    Manually retry an OCR job that has failed. Resets the job
    status and resubmits for processing.
    
    Args:
        job_id: Job identifier to retry
        background_tasks: FastAPI background tasks
    
    Returns:
        Updated job status
    
    Raises:
        HTTPException: If job not found or not in failed state
    """
    try:
        success = ocr_workflow.retry_failed_task(job_id)
        
        if not success:
            status = ocr_workflow.get_task_status(job_id)
            if not status:
                raise HTTPException(
                    status_code=404,
                    detail=f"OCR job {job_id} not found"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot retry job in status: {status['status']}"
                )
        
        # Schedule background processing
        background_tasks.add_task(ocr_workflow.process_task, job_id)
        
        task = ocr_workflow.tasks[job_id]
        
        return OCRProcessResponse(
            job_id=job_id,
            document_id=task.document_id,
            status="queued",
            message="OCR job retry initiated successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry job: {str(e)}"
        )


@router.get("/learning/insights", response_model=Dict[str, Any])
async def get_learning_insights():
    """
    Get insights from correction history for OCR improvement
    
    Returns analysis of correction patterns to identify areas
    where OCR accuracy can be improved.
    
    Returns:
        Learning insights including error rates by field
    """
    try:
        insights = manual_correction.get_learning_insights()
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve learning insights: {str(e)}"
        )


# AWS Textract-specific endpoints

@router.post("/analyze-document", response_model=Dict[str, Any])
async def analyze_document_advanced(
    file: UploadFile = File(...),
    extract_forms: bool = True,
    extract_tables: bool = True
):
    """
    Advanced document analysis using AWS Textract
    
    Extracts forms (key-value pairs) and tables from documents.
    Requires AWS Textract to be enabled.
    
    Args:
        file: Document file to analyze
        extract_forms: Extract form fields (key-value pairs)
        extract_tables: Extract table structures
    
    Returns:
        Structured document analysis with forms and tables
    
    Raises:
        HTTPException: If Textract not available or analysis fails
    """
    try:
        # Check if Textract is available
        engine_info = hybrid_ocr_engine.get_engine_info()
        if not engine_info['textract_available']:
            raise HTTPException(
                status_code=503,
                detail="AWS Textract not available. Advanced document analysis requires Textract."
            )
        
        # Read file
        image_data = await file.read()
        
        # Determine feature types
        feature_types = []
        if extract_forms:
            feature_types.append('FORMS')
        if extract_tables:
            feature_types.append('TABLES')
        
        if not feature_types:
            raise HTTPException(
                status_code=400,
                detail="At least one feature type (forms or tables) must be enabled"
            )
        
        # Analyze document
        result = hybrid_ocr_engine.analyze_document(image_data, feature_types)
        
        return {
            "success": True,
            "text": result['text'],
            "forms_count": len(result.get('forms', [])),
            "tables_count": len(result.get('tables', [])),
            "forms": result.get('forms', []),
            "tables": result.get('tables', []),
            "confidence": result['confidence'],
            "engine": "textract"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document analysis failed: {str(e)}"
        )


@router.post("/extract-identity", response_model=Dict[str, Any])
async def extract_identity_document(
    file: UploadFile = File(...)
):
    """
    Extract data from identity documents (Aadhaar, PAN, etc.)
    
    Uses AWS Textract's AnalyzeID API for specialized identity
    document extraction with high accuracy.
    
    Args:
        file: Identity document image
    
    Returns:
        Structured identity document data
    
    Raises:
        HTTPException: If Textract not available or extraction fails
    """
    try:
        # Check if Textract is available
        engine_info = hybrid_ocr_engine.get_engine_info()
        if not engine_info['capabilities']['identity_documents']:
            raise HTTPException(
                status_code=503,
                detail="Identity document extraction requires AWS Textract"
            )
        
        # Read file
        image_data = await file.read()
        
        # Extract identity document
        result = hybrid_ocr_engine.extract_identity_document(image_data)
        
        return {
            "success": True,
            "document_type": result.get('document_type', 'unknown'),
            "fields": result.get('fields', {}),
            "confidence": result['confidence'],
            "engine": "textract"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Identity document extraction failed: {str(e)}"
        )


@router.get("/engine-info", response_model=Dict[str, Any])
async def get_ocr_engine_info():
    """
    Get information about available OCR engines
    
    Returns details about which OCR engines are available,
    their capabilities, and current configuration.
    
    Returns:
        Engine information and capabilities
    """
    try:
        info = hybrid_ocr_engine.get_engine_info()
        return info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve engine info: {str(e)}"
        )


@router.post("/process-s3", response_model=OCRProcessResponse, status_code=202)
async def process_document_from_s3(
    bucket_name: str,
    object_key: str,
    language: str = 'eng',
    background_tasks: BackgroundTasks = None
):
    """
    Process document directly from S3 using AWS Textract
    
    For large documents or async processing, documents can be
    processed directly from S3 without uploading through the API.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        language: Language code
        background_tasks: FastAPI background tasks
    
    Returns:
        Job ID for tracking
    
    Raises:
        HTTPException: If Textract not available or processing fails
    """
    try:
        # Check if Textract is available
        engine_info = hybrid_ocr_engine.get_engine_info()
        if not engine_info['capabilities']['s3_integration']:
            raise HTTPException(
                status_code=503,
                detail="S3 processing requires AWS Textract"
            )
        
        # Create document ID from S3 path
        document_id = f"s3_{bucket_name}_{object_key.replace('/', '_')}"
        
        # Submit task
        job_id = ocr_workflow.submit_task(
            document_id=document_id,
            image_path=f"s3://{bucket_name}/{object_key}",
            max_retries=3
        )
        
        # Schedule background processing
        if background_tasks:
            background_tasks.add_task(ocr_workflow.process_task, job_id)
        
        return OCRProcessResponse(
            job_id=job_id,
            document_id=document_id,
            status="queued",
            message="S3 document processing initiated with AWS Textract"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process S3 document: {str(e)}"
        )
