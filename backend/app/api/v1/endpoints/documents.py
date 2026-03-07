"""
Document Management API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services.document_storage import DocumentStorage
from app.services.encryption_service import EncryptionService
# from app.services.ocr_workflow import OCRWorkflow  # Temporarily disabled - requires zbar
# from app.services.manual_correction import ManualCorrectionInterface  # Temporarily disabled

router = APIRouter()

# Initialize services
encryption_service = EncryptionService()
document_storage = DocumentStorage()
# ocr_workflow = OCRWorkflow()  # Temporarily disabled
# manual_correction = ManualCorrectionInterface()  # Temporarily disabled


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    category: str
    ocr_task_id: Optional[str] = None


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    user_id: str,
    file: UploadFile = File(...),
    category: str = "other",
    trigger_ocr: bool = True
):
    """
    Upload a document with encryption
    """
    try:
        # Read file content
        content = await file.read()
        
        # Upload document
        result = await document_storage.upload_document(
            user_id=user_id,
            file_content=content,
            filename=file.filename,
            category=category
        )
        
        # Trigger OCR if requested
        ocr_task_id = None
        if trigger_ocr and file.content_type.startswith("image/"):
            ocr_task_id = ocr_workflow.submit_task(
                document_id=result["document_id"],
                image_path=result["s3_key"]
            )
        
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=file.filename,
            size_bytes=len(content),
            category=category,
            ocr_task_id=ocr_task_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_documents(
    user_id: str,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50
):
    """
    List user's documents with optional filtering
    
    Args:
        user_id: User ID
        category: Optional filter by category (identity, address_proof, income, education, vehicle, certificate, other)
        source: Optional filter by source (digilocker, manual, all)
        limit: Maximum number of documents to return
    
    Returns:
        List of documents with DigiLocker indicators
    """
    try:
        documents = document_storage.list_documents(
            user_id=user_id,
            category=category,
            limit=limit
        )
        
        # Filter by source if specified
        if source:
            if source == "digilocker":
                documents = [d for d in documents if d.get("is_digilocker", False)]
            elif source == "manual":
                documents = [d for d in documents if not d.get("is_digilocker", False)]
            # "all" or any other value returns all documents
        
        return {"documents": documents}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(user_id: str, document_id: str):
    """
    Retrieve a document
    """
    try:
        document = await document_storage.retrieve_document(
            user_id=user_id,
            document_id=document_id
        )
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(user_id: str, document_id: str):
    """
    Delete a document
    """
    try:
        success = await document_storage.delete_document(
            user_id=user_id,
            document_id=document_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/status/{task_id}")
async def get_ocr_status(task_id: str):
    """
    Get OCR processing status
    """
    try:
        status = ocr_workflow.get_task_status(task_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/result/{task_id}")
async def get_ocr_result(task_id: str):
    """
    Get OCR extraction result
    """
    try:
        result = ocr_workflow.get_extraction_result(task_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Result not available")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CorrectionRequest(BaseModel):
    session_id: str
    field_name: str
    original_value: str
    corrected_value: Optional[str]
    action: str
    confidence_before: float


@router.post("/ocr/correct")
async def apply_correction(request: CorrectionRequest):
    """
    Apply manual correction to OCR result
    """
    try:
        success = manual_correction.apply_correction(
            session_id=request.session_id,
            field_name=request.field_name,
            original_value=request.original_value,
            corrected_value=request.corrected_value,
            action=request.action,
            confidence_before=request.confidence_before
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to apply correction")
        
        return {"message": "Correction applied successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/usage")
async def get_storage_usage(user_id: str):
    """
    Get storage usage for user
    """
    try:
        usage = document_storage.get_storage_usage(user_id)
        return usage
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
