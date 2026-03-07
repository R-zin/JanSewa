"""
OCR Processing Workflow Service

Manages asynchronous OCR processing pipeline with progress tracking,
notifications, and retry logic.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import asyncio
from .ocr_engine_hybrid import HybridOCREngine, OCREngineType
from .document_parser import DocumentParser, ParsedDocument
from ..core.config import settings


class ProcessingStatus(str, Enum):
    """OCR processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class OCRTask(BaseModel):
    """Represents an OCR processing task"""
    task_id: str
    document_id: str
    image_path: str
    status: ProcessingStatus
    progress: float  # 0-100
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[ParsedDocument] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class OCRWorkflow:
    """
    Manages OCR processing workflow with async processing,
    progress tracking, and error handling.
    """
    
    def __init__(self):
        """Initialize OCR workflow"""
        # Initialize hybrid OCR engine based on configuration
        engine_type = getattr(settings, 'OCR_ENGINE', 'auto')
        self.ocr_engine = HybridOCREngine(
            preferred_engine=OCREngineType(engine_type),
            aws_region=settings.AWS_REGION
        )
        self.document_parser = DocumentParser()
        self.tasks: Dict[str, OCRTask] = {}
        self.processing_queue: List[str] = []
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.extraction_history: List[Dict] = []
    
    def submit_task(
        self,
        document_id: str,
        image_path: str,
        max_retries: int = 3
    ) -> str:
        """
        Submit a new OCR processing task
        
        Args:
            document_id: ID of the document
            image_path: Path to the image file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Task ID
        """
        task_id = f"ocr_{document_id}_{datetime.now().timestamp()}"
        
        task = OCRTask(
            task_id=task_id,
            document_id=document_id,
            image_path=image_path,
            status=ProcessingStatus.QUEUED,
            progress=0.0,
            created_at=datetime.now(),
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        self.processing_queue.append(task_id)
        
        return task_id
    
    def register_progress_callback(
        self,
        task_id: str,
        callback: Callable[[str, float, str], None]
    ):
        """
        Register a callback for progress updates
        
        Args:
            task_id: Task ID to monitor
            callback: Function to call with (task_id, progress, status)
        """
        if task_id not in self.progress_callbacks:
            self.progress_callbacks[task_id] = []
        self.progress_callbacks[task_id].append(callback)
    
    def _notify_progress(self, task_id: str, progress: float, status: str):
        """
        Notify all registered callbacks of progress update
        
        Args:
            task_id: Task ID
            progress: Progress percentage (0-100)
            status: Status message
        """
        if task_id in self.progress_callbacks:
            for callback in self.progress_callbacks[task_id]:
                try:
                    callback(task_id, progress, status)
                except Exception as e:
                    print(f"Error in progress callback: {e}")
    
    async def process_task(self, task_id: str) -> bool:
        """
        Process an OCR task asynchronously
        
        Args:
            task_id: Task ID to process
            
        Returns:
            Success status
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        try:
            # Update status to processing
            task.status = ProcessingStatus.PROCESSING
            task.started_at = datetime.now()
            task.progress = 0.0
            self._notify_progress(task_id, 0.0, "Starting OCR processing")
            
            # Step 1: Image quality check (10%)
            task.progress = 10.0
            self._notify_progress(task_id, 10.0, "Checking image quality")
            quality_result = self.ocr_engine.check_image_quality(task.image_path)
            
            if not quality_result["suitable"]:
                raise Exception(f"Image quality insufficient: {quality_result['issues']}")
            
            # Step 2: OCR extraction (50%)
            task.progress = 20.0
            self._notify_progress(task_id, 20.0, "Extracting text from image")
            
            ocr_result = self.ocr_engine.extract_text(task.image_path)
            
            task.progress = 50.0
            self._notify_progress(task_id, 50.0, "Text extraction completed")
            
            # Step 3: Document parsing (30%)
            task.progress = 60.0
            self._notify_progress(task_id, 60.0, "Parsing document structure")
            
            parsed_doc = self.document_parser.parse_document(
                ocr_result["text"],
                ocr_result.get("confidence_scores")
            )
            
            task.progress = 90.0
            self._notify_progress(task_id, 90.0, "Finalizing results")
            
            # Step 4: Store results
            task.result = parsed_doc
            task.status = ProcessingStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            
            # Add to extraction history
            self.extraction_history.append({
                "task_id": task_id,
                "document_id": task.document_id,
                "document_type": parsed_doc.document_type,
                "fields_extracted": len(parsed_doc.fields),
                "confidence": parsed_doc.confidence,
                "timestamp": task.completed_at,
                "processing_time": (task.completed_at - task.started_at).total_seconds()
            })
            
            self._notify_progress(task_id, 100.0, "Processing completed successfully")
            return True
            
        except Exception as e:
            task.error_message = str(e)
            
            # Check if we should retry
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = ProcessingStatus.RETRYING
                self._notify_progress(
                    task_id,
                    task.progress,
                    f"Error occurred, retrying ({task.retry_count}/{task.max_retries})"
                )
                
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** task.retry_count)
                
                # Retry the task
                return await self.process_task(task_id)
            else:
                task.status = ProcessingStatus.FAILED
                task.completed_at = datetime.now()
                self._notify_progress(task_id, task.progress, f"Processing failed: {str(e)}")
                return False
    
    async def process_queue(self):
        """
        Process all tasks in the queue asynchronously
        """
        while self.processing_queue:
            task_id = self.processing_queue.pop(0)
            await self.process_task(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get status of a task
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status information
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        status_info = {
            "task_id": task.task_id,
            "document_id": task.document_id,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at.isoformat(),
            "retry_count": task.retry_count
        }
        
        if task.started_at:
            status_info["started_at"] = task.started_at.isoformat()
        
        if task.completed_at:
            status_info["completed_at"] = task.completed_at.isoformat()
            status_info["processing_time"] = (task.completed_at - task.started_at).total_seconds()
        
        if task.error_message:
            status_info["error"] = task.error_message
        
        if task.result:
            status_info["result"] = {
                "document_type": task.result.document_type,
                "fields_count": len(task.result.fields),
                "confidence": task.result.confidence
            }
        
        return status_info
    
    def get_extraction_result(self, task_id: str) -> Optional[ParsedDocument]:
        """
        Get extraction result for a completed task
        
        Args:
            task_id: Task ID
            
        Returns:
            Parsed document or None
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        if task.status == ProcessingStatus.COMPLETED:
            return task.result
        
        return None
    
    def retry_failed_task(self, task_id: str) -> bool:
        """
        Manually retry a failed task
        
        Args:
            task_id: Task ID to retry
            
        Returns:
            Success status
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status != ProcessingStatus.FAILED:
            return False
        
        # Reset task for retry
        task.status = ProcessingStatus.QUEUED
        task.retry_count = 0
        task.error_message = None
        task.progress = 0.0
        
        # Add back to queue
        self.processing_queue.append(task_id)
        
        return True
    
    def get_extraction_history(
        self,
        document_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get extraction history
        
        Args:
            document_id: Optional filter by document ID
            limit: Maximum number of records to return
            
        Returns:
            List of extraction history records
        """
        history = self.extraction_history
        
        if document_id:
            history = [h for h in history if h["document_id"] == document_id]
        
        # Sort by timestamp descending
        history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
        
        return history[:limit]
    
    def get_processing_statistics(self) -> Dict:
        """
        Get overall processing statistics
        
        Returns:
            Statistics dictionary
        """
        total_tasks = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == ProcessingStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == ProcessingStatus.FAILED)
        processing = sum(1 for t in self.tasks.values() if t.status == ProcessingStatus.PROCESSING)
        queued = sum(1 for t in self.tasks.values() if t.status == ProcessingStatus.QUEUED)
        
        # Calculate average processing time
        completed_tasks = [t for t in self.tasks.values() if t.status == ProcessingStatus.COMPLETED and t.started_at and t.completed_at]
        avg_processing_time = sum(
            (t.completed_at - t.started_at).total_seconds() for t in completed_tasks
        ) / len(completed_tasks) if completed_tasks else 0
        
        # Calculate average confidence
        avg_confidence = sum(
            t.result.confidence for t in self.tasks.values() 
            if t.result and t.status == ProcessingStatus.COMPLETED
        ) / completed if completed > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "queued": queued,
            "success_rate": completed / total_tasks if total_tasks > 0 else 0,
            "average_processing_time": avg_processing_time,
            "average_confidence": avg_confidence
        }
