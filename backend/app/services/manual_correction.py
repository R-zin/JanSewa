"""
Manual Correction Interface Service

Manages manual corrections for OCR-extracted data.
Stores corrections for learning and improvement.
"""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class CorrectionAction(str, Enum):
    """Actions that can be taken on extracted fields"""
    CONFIRM = "confirm"
    EDIT = "edit"
    REJECT = "reject"


class FieldCorrection(BaseModel):
    """Represents a correction made to an extracted field"""
    field_name: str
    original_value: str
    corrected_value: Optional[str]
    action: CorrectionAction
    confidence_before: float
    timestamp: datetime


class CorrectionSession(BaseModel):
    """Represents a manual correction session"""
    session_id: str
    document_id: str
    document_type: str
    corrections: List[FieldCorrection]
    created_at: datetime
    completed_at: Optional[datetime] = None


class ManualCorrectionInterface:
    """
    Manages manual corrections for OCR-extracted data.
    Provides interface for reviewing and correcting extracted fields.
    """
    
    def __init__(self):
        """Initialize manual correction interface"""
        self.correction_history: Dict[str, CorrectionSession] = {}
        self.learning_data: List[FieldCorrection] = []
    
    def create_correction_session(
        self,
        document_id: str,
        document_type: str,
        extracted_fields: List[Dict]
    ) -> str:
        """
        Create a new correction session
        
        Args:
            document_id: ID of the document being corrected
            document_type: Type of document
            extracted_fields: List of extracted fields with confidence scores
            
        Returns:
            Session ID
        """
        session_id = f"correction_{document_id}_{datetime.now().timestamp()}"
        
        session = CorrectionSession(
            session_id=session_id,
            document_id=document_id,
            document_type=document_type,
            corrections=[],
            created_at=datetime.now()
        )
        
        self.correction_history[session_id] = session
        return session_id
    
    def get_fields_for_review(
        self,
        extracted_fields: List[Dict],
        confidence_threshold: float = 0.85
    ) -> List[Dict]:
        """
        Get fields that need manual review based on confidence
        
        Args:
            extracted_fields: List of extracted fields
            confidence_threshold: Minimum confidence for auto-acceptance
            
        Returns:
            List of fields needing review with highlighting info
        """
        fields_for_review = []
        
        for field in extracted_fields:
            field_info = {
                "field_name": field.get("field_name"),
                "value": field.get("value"),
                "confidence": field.get("confidence", 0.0),
                "needs_review": field.get("confidence", 0.0) < confidence_threshold,
                "highlight_color": self._get_highlight_color(field.get("confidence", 0.0))
            }
            fields_for_review.append(field_info)
        
        return fields_for_review
    
    def _get_highlight_color(self, confidence: float) -> str:
        """
        Get highlight color based on confidence level
        
        Args:
            confidence: Confidence score (0-1)
            
        Returns:
            Color code for highlighting
        """
        if confidence >= 0.90:
            return "green"  # High confidence
        elif confidence >= 0.75:
            return "yellow"  # Medium confidence
        else:
            return "red"  # Low confidence
    
    def apply_correction(
        self,
        session_id: str,
        field_name: str,
        original_value: str,
        corrected_value: Optional[str],
        action: CorrectionAction,
        confidence_before: float
    ) -> bool:
        """
        Apply a correction to a field
        
        Args:
            session_id: Correction session ID
            field_name: Name of the field being corrected
            original_value: Original extracted value
            corrected_value: Corrected value (if edited)
            action: Action taken (confirm, edit, reject)
            confidence_before: Original confidence score
            
        Returns:
            Success status
        """
        if session_id not in self.correction_history:
            return False
        
        correction = FieldCorrection(
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            action=action,
            confidence_before=confidence_before,
            timestamp=datetime.now()
        )
        
        self.correction_history[session_id].corrections.append(correction)
        
        # Store for learning if edited or rejected
        if action in [CorrectionAction.EDIT, CorrectionAction.REJECT]:
            self.learning_data.append(correction)
        
        return True
    
    def complete_session(self, session_id: str) -> Dict:
        """
        Complete a correction session and return summary
        
        Args:
            session_id: Session ID to complete
            
        Returns:
            Summary of corrections made
        """
        if session_id not in self.correction_history:
            return {"error": "Session not found"}
        
        session = self.correction_history[session_id]
        session.completed_at = datetime.now()
        
        # Generate summary
        summary = {
            "session_id": session_id,
            "document_id": session.document_id,
            "document_type": session.document_type,
            "total_corrections": len(session.corrections),
            "confirmed": sum(1 for c in session.corrections if c.action == CorrectionAction.CONFIRM),
            "edited": sum(1 for c in session.corrections if c.action == CorrectionAction.EDIT),
            "rejected": sum(1 for c in session.corrections if c.action == CorrectionAction.REJECT),
            "duration_seconds": (session.completed_at - session.created_at).total_seconds()
        }
        
        return summary
    
    def get_corrected_fields(self, session_id: str) -> List[Dict]:
        """
        Get all corrected fields from a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of corrected fields with final values
        """
        if session_id not in self.correction_history:
            return []
        
        session = self.correction_history[session_id]
        corrected_fields = []
        
        for correction in session.corrections:
            if correction.action == CorrectionAction.CONFIRM:
                final_value = correction.original_value
            elif correction.action == CorrectionAction.EDIT:
                final_value = correction.corrected_value
            else:  # REJECT
                final_value = None
            
            corrected_fields.append({
                "field_name": correction.field_name,
                "final_value": final_value,
                "action": correction.action,
                "was_corrected": correction.action != CorrectionAction.CONFIRM
            })
        
        return corrected_fields
    
    def get_learning_insights(self) -> Dict:
        """
        Get insights from correction history for improving OCR
        
        Returns:
            Dictionary with learning insights
        """
        if not self.learning_data:
            return {"message": "No correction data available yet"}
        
        # Analyze common correction patterns
        field_error_rates = {}
        low_confidence_corrections = []
        
        for correction in self.learning_data:
            # Track error rates by field
            if correction.field_name not in field_error_rates:
                field_error_rates[correction.field_name] = {"total": 0, "errors": 0}
            
            field_error_rates[correction.field_name]["total"] += 1
            if correction.action in [CorrectionAction.EDIT, CorrectionAction.REJECT]:
                field_error_rates[correction.field_name]["errors"] += 1
            
            # Track low confidence corrections
            if correction.confidence_before < 0.75:
                low_confidence_corrections.append({
                    "field": correction.field_name,
                    "confidence": correction.confidence_before,
                    "was_correct": correction.action == CorrectionAction.CONFIRM
                })
        
        # Calculate error rates
        error_rates = {}
        for field, stats in field_error_rates.items():
            error_rates[field] = stats["errors"] / stats["total"] if stats["total"] > 0 else 0
        
        return {
            "total_corrections": len(self.learning_data),
            "field_error_rates": error_rates,
            "fields_needing_improvement": [
                field for field, rate in error_rates.items() if rate > 0.3
            ],
            "low_confidence_accuracy": sum(
                1 for c in low_confidence_corrections if c["was_correct"]
            ) / len(low_confidence_corrections) if low_confidence_corrections else 0
        }
    
    def export_training_data(self) -> List[Dict]:
        """
        Export correction data for training/improving OCR models
        
        Returns:
            List of training examples
        """
        training_data = []
        
        for correction in self.learning_data:
            if correction.action == CorrectionAction.EDIT:
                training_data.append({
                    "field_name": correction.field_name,
                    "incorrect_value": correction.original_value,
                    "correct_value": correction.corrected_value,
                    "confidence": correction.confidence_before,
                    "timestamp": correction.timestamp.isoformat()
                })
        
        return training_data
