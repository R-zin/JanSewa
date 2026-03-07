"""
CAPTCHA Handler Service

Detects and provides instructions for CAPTCHA completion.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel


class CAPTCHAType(str, Enum):
    """Types of CAPTCHA"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    RECAPTCHA = "recaptcha"
    HCAPTCHA = "hcaptcha"
    PUZZLE = "puzzle"
    MATH = "math"
    UNKNOWN = "unknown"


class CAPTCHAStatus(str, Enum):
    """CAPTCHA completion status"""
    DETECTED = "detected"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CAPTCHASession(BaseModel):
    """Represents a CAPTCHA interaction session"""
    captcha_id: str
    automation_session_id: str
    captcha_type: CAPTCHAType
    status: CAPTCHAStatus
    detected_at: datetime
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 120


class CAPTCHAHandler:
    """
    Handles CAPTCHA detection and user guidance.
    Pauses automation and provides instructions for manual completion.
    """
    
    def __init__(self):
        """Initialize CAPTCHA handler"""
        self.captcha_sessions: Dict[str, CAPTCHASession] = {}
    
    def detect_captcha(
        self,
        automation_session_id: str,
        page_content: str
    ) -> Optional[Dict]:
        """
        Detect CAPTCHA on page
        
        Args:
            automation_session_id: Automation session ID
            page_content: HTML content of page
            
        Returns:
            CAPTCHA detection result or None
        """
        # Check for common CAPTCHA indicators
        captcha_type = self._identify_captcha_type(page_content)
        
        if captcha_type == CAPTCHAType.UNKNOWN:
            return None
        
        # Create CAPTCHA session
        captcha_id = f"captcha_{automation_session_id}_{datetime.now().timestamp()}"
        
        captcha_session = CAPTCHASession(
            captcha_id=captcha_id,
            automation_session_id=automation_session_id,
            captcha_type=captcha_type,
            status=CAPTCHAStatus.DETECTED,
            detected_at=datetime.now()
        )
        
        self.captcha_sessions[captcha_id] = captcha_session
        
        return {
            "captcha_id": captcha_id,
            "captcha_type": captcha_type,
            "instructions": self._generate_instructions(captcha_type),
            "timeout_seconds": captcha_session.timeout_seconds
        }
    
    def _identify_captcha_type(self, page_content: str) -> CAPTCHAType:
        """
        Identify CAPTCHA type from page content
        
        Args:
            page_content: HTML content
            
        Returns:
            CAPTCHA type
        """
        content_lower = page_content.lower()
        
        if "recaptcha" in content_lower or "g-recaptcha" in content_lower:
            return CAPTCHAType.RECAPTCHA
        elif "hcaptcha" in content_lower or "h-captcha" in content_lower:
            return CAPTCHAType.HCAPTCHA
        elif "captcha" in content_lower:
            # Try to determine specific type
            if "audio" in content_lower:
                return CAPTCHAType.AUDIO
            elif "puzzle" in content_lower or "slider" in content_lower:
                return CAPTCHAType.PUZZLE
            elif any(word in content_lower for word in ["add", "subtract", "multiply"]):
                return CAPTCHAType.MATH
            elif "image" in content_lower or "picture" in content_lower:
                return CAPTCHAType.IMAGE
            else:
                return CAPTCHAType.TEXT
        
        return CAPTCHAType.UNKNOWN
    
    def _generate_instructions(self, captcha_type: CAPTCHAType) -> Dict[str, str]:
        """
        Generate user instructions for CAPTCHA type
        
        Args:
            captcha_type: Type of CAPTCHA
            
        Returns:
            Instructions dictionary
        """
        instructions = {
            CAPTCHAType.TEXT: {
                "title": "Text CAPTCHA Detected",
                "description": "Please enter the characters shown in the image.",
                "steps": [
                    "Look at the CAPTCHA image on the page",
                    "Type the characters you see in the input field",
                    "Click the submit or verify button",
                    "Click 'Continue' in this app when done"
                ]
            },
            CAPTCHAType.IMAGE: {
                "title": "Image CAPTCHA Detected",
                "description": "Please select the correct images as instructed.",
                "steps": [
                    "Read the instruction (e.g., 'Select all images with traffic lights')",
                    "Click on all images that match the instruction",
                    "Click the verify button",
                    "Click 'Continue' in this app when done"
                ]
            },
            CAPTCHAType.RECAPTCHA: {
                "title": "reCAPTCHA Detected",
                "description": "Please complete the reCAPTCHA verification.",
                "steps": [
                    "Check the 'I'm not a robot' checkbox",
                    "If prompted, complete the image challenge",
                    "Wait for the green checkmark",
                    "Click 'Continue' in this app when done"
                ]
            },
            CAPTCHAType.HCAPTCHA: {
                "title": "hCaptcha Detected",
                "description": "Please complete the hCaptcha verification.",
                "steps": [
                    "Click on the hCaptcha checkbox",
                    "Complete the image challenge if shown",
                    "Wait for verification to complete",
                    "Click 'Continue' in this app when done"
                ]
            },
            CAPTCHAType.PUZZLE: {
                "title": "Puzzle CAPTCHA Detected",
                "description": "Please complete the puzzle verification.",
                "steps": [
                    "Drag the slider or puzzle piece to the correct position",
                    "Release when the pieces align",
                    "Wait for verification",
                    "Click 'Continue' in this app when done"
                ]
            },
            CAPTCHAType.MATH: {
                "title": "Math CAPTCHA Detected",
                "description": "Please solve the math problem.",
                "steps": [
                    "Read the math problem shown",
                    "Calculate the answer",
                    "Enter the answer in the input field",
                    "Click 'Continue' in this app when done"
                ]
            },
            CAPTCHAType.AUDIO: {
                "title": "Audio CAPTCHA Detected",
                "description": "Please complete the audio verification.",
                "steps": [
                    "Click the audio button to play the sound",
                    "Listen carefully to the characters or numbers",
                    "Type what you hear in the input field",
                    "Click 'Continue' in this app when done"
                ]
            }
        }
        
        return instructions.get(captcha_type, {
            "title": "CAPTCHA Detected",
            "description": "Please complete the verification on the page.",
            "steps": [
                "Complete the CAPTCHA challenge on the page",
                "Click 'Continue' in this app when done"
            ]
        })
    
    def mark_waiting(self, captcha_id: str) -> bool:
        """
        Mark CAPTCHA as waiting for user completion
        
        Args:
            captcha_id: CAPTCHA session ID
            
        Returns:
            Success status
        """
        if captcha_id not in self.captcha_sessions:
            return False
        
        captcha_session = self.captcha_sessions[captcha_id]
        captcha_session.status = CAPTCHAStatus.WAITING
        
        return True
    
    def mark_completed(self, captcha_id: str) -> bool:
        """
        Mark CAPTCHA as completed
        
        Args:
            captcha_id: CAPTCHA session ID
            
        Returns:
            Success status
        """
        if captcha_id not in self.captcha_sessions:
            return False
        
        captcha_session = self.captcha_sessions[captcha_id]
        captcha_session.status = CAPTCHAStatus.COMPLETED
        captcha_session.completed_at = datetime.now()
        
        return True
    
    def mark_failed(self, captcha_id: str) -> Dict:
        """
        Mark CAPTCHA attempt as failed
        
        Args:
            captcha_id: CAPTCHA session ID
            
        Returns:
            Retry information
        """
        if captcha_id not in self.captcha_sessions:
            return {"error": "CAPTCHA session not found"}
        
        captcha_session = self.captcha_sessions[captcha_id]
        captcha_session.retry_count += 1
        
        if captcha_session.retry_count >= captcha_session.max_retries:
            captcha_session.status = CAPTCHAStatus.FAILED
            return {
                "can_retry": False,
                "message": "Maximum retry attempts reached. Please try again later."
            }
        
        captcha_session.status = CAPTCHAStatus.DETECTED
        
        return {
            "can_retry": True,
            "retry_count": captcha_session.retry_count,
            "max_retries": captcha_session.max_retries,
            "message": f"CAPTCHA verification failed. Please try again ({captcha_session.retry_count}/{captcha_session.max_retries}).",
            "instructions": self._generate_instructions(captcha_session.captcha_type)
        }
    
    def check_timeout(self, captcha_id: str) -> bool:
        """
        Check if CAPTCHA session has timed out
        
        Args:
            captcha_id: CAPTCHA session ID
            
        Returns:
            True if timed out
        """
        if captcha_id not in self.captcha_sessions:
            return False
        
        captcha_session = self.captcha_sessions[captcha_id]
        
        if captcha_session.status == CAPTCHAStatus.COMPLETED:
            return False
        
        elapsed = datetime.now() - captcha_session.detected_at
        
        if elapsed.total_seconds() > captcha_session.timeout_seconds:
            captcha_session.status = CAPTCHAStatus.TIMEOUT
            return True
        
        return False
    
    def get_remaining_time(self, captcha_id: str) -> Optional[int]:
        """
        Get remaining time before timeout
        
        Args:
            captcha_id: CAPTCHA session ID
            
        Returns:
            Remaining seconds or None
        """
        if captcha_id not in self.captcha_sessions:
            return None
        
        captcha_session = self.captcha_sessions[captcha_id]
        
        elapsed = datetime.now() - captcha_session.detected_at
        remaining = captcha_session.timeout_seconds - elapsed.total_seconds()
        
        return max(0, int(remaining))
    
    def get_captcha_status(self, captcha_id: str) -> Optional[Dict]:
        """
        Get CAPTCHA session status
        
        Args:
            captcha_id: CAPTCHA session ID
            
        Returns:
            Status information
        """
        if captcha_id not in self.captcha_sessions:
            return None
        
        captcha_session = self.captcha_sessions[captcha_id]
        
        return {
            "captcha_id": captcha_session.captcha_id,
            "captcha_type": captcha_session.captcha_type,
            "status": captcha_session.status,
            "detected_at": captcha_session.detected_at.isoformat(),
            "retry_count": captcha_session.retry_count,
            "max_retries": captcha_session.max_retries,
            "remaining_time": self.get_remaining_time(captcha_id)
        }
    
    def highlight_captcha_element(self, captcha_type: CAPTCHAType) -> Dict:
        """
        Get element selectors for highlighting CAPTCHA
        
        Args:
            captcha_type: Type of CAPTCHA
            
        Returns:
            Element selectors
        """
        selectors = {
            CAPTCHAType.RECAPTCHA: {
                "iframe": "iframe[src*='recaptcha']",
                "checkbox": ".recaptcha-checkbox"
            },
            CAPTCHAType.HCAPTCHA: {
                "iframe": "iframe[src*='hcaptcha']",
                "checkbox": ".hcaptcha-checkbox"
            },
            CAPTCHAType.TEXT: {
                "image": "img[alt*='captcha'], img[src*='captcha']",
                "input": "input[name*='captcha'], input[id*='captcha']"
            },
            CAPTCHAType.IMAGE: {
                "container": "div[class*='captcha'], div[id*='captcha']"
            }
        }
        
        return selectors.get(captcha_type, {})
