"""
Speech Recognition Engine Service

Handles speech-to-text conversion with multi-language support.
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class RecognitionStatus(str, Enum):
    """Speech recognition status"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioQuality(str, Enum):
    """Audio quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class TranscriptionResult(BaseModel):
    """Result of speech transcription"""
    transcription_id: str
    text: str
    confidence: float
    language: str
    duration_seconds: float
    timestamp: datetime
    audio_quality: AudioQuality


class VoiceCommand(str, Enum):
    """Supported voice commands"""
    NAVIGATE_HOME = "navigate_home"
    NAVIGATE_DASHBOARD = "navigate_dashboard"
    START_AUTOMATION = "start_automation"
    PAUSE_AUTOMATION = "pause_automation"
    RESUME_AUTOMATION = "resume_automation"
    UPLOAD_DOCUMENT = "upload_document"
    SUBMIT_FORM = "submit_form"
    HELP = "help"
    CANCEL = "cancel"


class SpeechRecognitionEngine:
    """
    Handles speech-to-text conversion with local processing for privacy.
    Supports multiple languages and voice commands.
    """
    
    def __init__(self):
        """Initialize speech recognition engine"""
        self.supported_languages = ["en", "hi", "ta", "te", "bn"]
        self.current_language = "en"
        self.transcription_history: List[TranscriptionResult] = []
        self._init_voice_commands()
    
    def _init_voice_commands(self):
        """Initialize voice command patterns"""
        self.command_patterns = {
            "en": {
                VoiceCommand.NAVIGATE_HOME: ["go home", "home page", "main page"],
                VoiceCommand.NAVIGATE_DASHBOARD: ["go to dashboard", "open dashboard", "show dashboard"],
                VoiceCommand.START_AUTOMATION: ["start automation", "begin automation", "start process"],
                VoiceCommand.PAUSE_AUTOMATION: ["pause", "stop", "wait"],
                VoiceCommand.RESUME_AUTOMATION: ["resume", "continue", "proceed"],
                VoiceCommand.UPLOAD_DOCUMENT: ["upload document", "upload file", "attach document"],
                VoiceCommand.SUBMIT_FORM: ["submit", "submit form", "send"],
                VoiceCommand.HELP: ["help", "help me", "what can I do"],
                VoiceCommand.CANCEL: ["cancel", "go back", "nevermind"]
            },
            "hi": {
                VoiceCommand.NAVIGATE_HOME: ["होम जाओ", "मुख्य पृष्ठ"],
                VoiceCommand.NAVIGATE_DASHBOARD: ["डैशबोर्ड खोलो", "डैशबोर्ड दिखाओ"],
                VoiceCommand.START_AUTOMATION: ["शुरू करो", "प्रक्रिया शुरू करो"],
                VoiceCommand.PAUSE_AUTOMATION: ["रुको", "ठहरो"],
                VoiceCommand.RESUME_AUTOMATION: ["जारी रखो", "आगे बढ़ो"],
                VoiceCommand.HELP: ["मदद", "सहायता"],
                VoiceCommand.CANCEL: ["रद्द करो", "वापस जाओ"]
            }
        }
    
    def set_language(self, language_code: str) -> bool:
        """
        Set recognition language
        
        Args:
            language_code: Language code
            
        Returns:
            Success status
        """
        if language_code not in self.supported_languages:
            return False
        
        self.current_language = language_code
        return True
    
    def check_audio_quality(self, audio_data: bytes) -> Dict:
        """
        Check audio quality before processing
        
        Args:
            audio_data: Audio data bytes
            
        Returns:
            Quality assessment
        """
        # In production, analyze audio properties
        # For now, simulate quality check
        
        audio_length = len(audio_data)
        
        if audio_length < 1000:
            quality = AudioQuality.POOR
            suitable = False
            issues = ["Audio too short", "Insufficient data"]
        elif audio_length < 5000:
            quality = AudioQuality.FAIR
            suitable = True
            issues = ["Background noise detected"]
        elif audio_length < 20000:
            quality = AudioQuality.GOOD
            suitable = True
            issues = []
        else:
            quality = AudioQuality.EXCELLENT
            suitable = True
            issues = []
        
        return {
            "quality": quality,
            "suitable": suitable,
            "issues": issues,
            "recommendations": self._get_quality_recommendations(quality)
        }
    
    def _get_quality_recommendations(self, quality: AudioQuality) -> List[str]:
        """Get recommendations for improving audio quality"""
        recommendations = {
            AudioQuality.POOR: [
                "Speak closer to the microphone",
                "Reduce background noise",
                "Speak more clearly and slowly"
            ],
            AudioQuality.FAIR: [
                "Try to reduce background noise",
                "Speak a bit louder"
            ],
            AudioQuality.GOOD: [],
            AudioQuality.EXCELLENT: []
        }
        
        return recommendations.get(quality, [])
    
    def transcribe_audio(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Audio data bytes
            language: Language code (uses current if not specified)
            
        Returns:
            Transcription result
        """
        if language is None:
            language = self.current_language
        
        # Check audio quality
        quality_check = self.check_audio_quality(audio_data)
        
        # In production, use speech recognition library (e.g., Whisper, Google Speech)
        # For now, simulate transcription
        transcription_id = f"trans_{datetime.now().timestamp()}"
        
        # Simulate transcription
        simulated_text = "[Transcribed speech in " + language + "]"
        confidence = 0.85 if quality_check["suitable"] else 0.60
        
        result = TranscriptionResult(
            transcription_id=transcription_id,
            text=simulated_text,
            confidence=confidence,
            language=language,
            duration_seconds=len(audio_data) / 16000,  # Assuming 16kHz sample rate
            timestamp=datetime.now(),
            audio_quality=quality_check["quality"]
        )
        
        # Store in history (excluding sensitive data)
        self.transcription_history.append(result)
        
        return result
    
    def recognize_voice_command(self, text: str) -> Optional[VoiceCommand]:
        """
        Recognize voice command from text
        
        Args:
            text: Transcribed text
            
        Returns:
            Recognized command or None
        """
        text_lower = text.lower().strip()
        
        # Check command patterns for current language
        if self.current_language in self.command_patterns:
            for command, patterns in self.command_patterns[self.current_language].items():
                if any(pattern in text_lower for pattern in patterns):
                    return command
        
        return None
    
    def process_voice_input(
        self,
        audio_data: bytes,
        context: str = "general"
    ) -> Dict:
        """
        Process voice input and return result
        
        Args:
            audio_data: Audio data
            context: Context of input (general, form_field, command)
            
        Returns:
            Processing result
        """
        # Transcribe audio
        transcription = self.transcribe_audio(audio_data)
        
        # Check for voice command
        command = self.recognize_voice_command(transcription.text)
        
        result = {
            "transcription_id": transcription.transcription_id,
            "text": transcription.text,
            "confidence": transcription.confidence,
            "audio_quality": transcription.audio_quality,
            "is_command": command is not None,
            "command": command,
            "requires_confirmation": transcription.confidence < 0.80
        }
        
        return result
    
    def validate_field_input(
        self,
        transcribed_text: str,
        field_type: str
    ) -> Dict:
        """
        Validate transcribed text for form field
        
        Args:
            transcribed_text: Transcribed text
            field_type: Type of field (text, number, date, etc.)
            
        Returns:
            Validation result
        """
        is_valid = True
        error_message = None
        normalized_value = transcribed_text
        
        if field_type == "number":
            # Check if text contains numbers
            if not any(char.isdigit() for char in transcribed_text):
                is_valid = False
                error_message = "No numbers detected in speech"
            else:
                # Extract numbers
                normalized_value = ''.join(char for char in transcribed_text if char.isdigit())
        
        elif field_type == "date":
            # Check for date patterns
            # In production, use date parsing library
            if not any(word in transcribed_text.lower() for word in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]):
                is_valid = False
                error_message = "Could not detect date in speech"
        
        elif field_type == "email":
            # Check for email patterns
            if "@" not in transcribed_text or "." not in transcribed_text:
                is_valid = False
                error_message = "Invalid email format detected"
        
        return {
            "is_valid": is_valid,
            "normalized_value": normalized_value,
            "error_message": error_message,
            "suggestions": self._get_correction_suggestions(transcribed_text, field_type)
        }
    
    def _get_correction_suggestions(
        self,
        text: str,
        field_type: str
    ) -> List[str]:
        """Get suggestions for correcting voice input"""
        suggestions = []
        
        if field_type == "number":
            suggestions.append("Please speak numbers clearly, one digit at a time")
        elif field_type == "date":
            suggestions.append("Please say the date in format: day, month, year")
        elif field_type == "email":
            suggestions.append("Please say 'at' for @ and 'dot' for .")
        
        return suggestions
    
    def get_voice_command_help(self, language: str = "en") -> List[Dict]:
        """
        Get list of available voice commands
        
        Args:
            language: Language code
            
        Returns:
            List of commands with examples
        """
        if language not in self.command_patterns:
            language = "en"
        
        commands = []
        for command, patterns in self.command_patterns[language].items():
            commands.append({
                "command": command,
                "examples": patterns,
                "description": self._get_command_description(command, language)
            })
        
        return commands
    
    def _get_command_description(
        self,
        command: VoiceCommand,
        language: str
    ) -> str:
        """Get description for voice command"""
        descriptions = {
            "en": {
                VoiceCommand.NAVIGATE_HOME: "Navigate to home page",
                VoiceCommand.NAVIGATE_DASHBOARD: "Open your dashboard",
                VoiceCommand.START_AUTOMATION: "Start browser automation",
                VoiceCommand.PAUSE_AUTOMATION: "Pause current automation",
                VoiceCommand.RESUME_AUTOMATION: "Resume paused automation",
                VoiceCommand.UPLOAD_DOCUMENT: "Upload a document",
                VoiceCommand.SUBMIT_FORM: "Submit the current form",
                VoiceCommand.HELP: "Get help and show available commands",
                VoiceCommand.CANCEL: "Cancel current action"
            }
        }
        
        return descriptions.get(language, {}).get(command, "")
    
    def enable_continuous_listening(self) -> bool:
        """
        Enable continuous voice navigation
        
        Returns:
            Success status
        """
        # In production, start continuous audio capture
        return True
    
    def disable_continuous_listening(self) -> bool:
        """
        Disable continuous voice navigation
        
        Returns:
            Success status
        """
        # In production, stop audio capture
        return True
    
    def get_transcription_history(
        self,
        limit: int = 10,
        exclude_sensitive: bool = True
    ) -> List[Dict]:
        """
        Get transcription history
        
        Args:
            limit: Maximum number of records
            exclude_sensitive: Whether to exclude sensitive data
            
        Returns:
            List of transcription records
        """
        history = self.transcription_history[-limit:]
        
        return [
            {
                "transcription_id": t.transcription_id,
                "text": "[REDACTED]" if exclude_sensitive else t.text,
                "confidence": t.confidence,
                "language": t.language,
                "timestamp": t.timestamp.isoformat(),
                "audio_quality": t.audio_quality
            }
            for t in history
        ]
