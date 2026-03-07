"""
Speech-to-Text API Endpoints

Provides REST API for speech input processing and voice command execution.
Implements Requirements 18.1, 18.7
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from app.services.speech_recognition import (
    SpeechRecognitionEngine,
    TranscriptionResult,
    VoiceCommand,
    RecognitionStatus,
    AudioQuality
)

router = APIRouter()

# Initialize speech recognition engine
speech_engine = SpeechRecognitionEngine()


# Request/Response Models

class TranscribeRequest(BaseModel):
    """Request to transcribe audio"""
    language: Optional[str] = Field(None, description="Language code (en, hi, ta, te, bn)")
    context: str = Field(default="general", description="Context: general, form_field, command")


class TranscribeResponse(BaseModel):
    """Response from audio transcription"""
    transcription_id: str = Field(..., description="Unique transcription ID")
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    language: str = Field(..., description="Language used for transcription")
    audio_quality: AudioQuality = Field(..., description="Audio quality assessment")
    duration_seconds: float = Field(..., description="Audio duration in seconds")
    requires_confirmation: bool = Field(..., description="True if confidence below threshold")
    timestamp: str = Field(..., description="Transcription timestamp")


class VoiceCommandRequest(BaseModel):
    """Request to execute voice command"""
    command: VoiceCommand = Field(..., description="Voice command to execute")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for command execution")


class VoiceCommandResponse(BaseModel):
    """Response from voice command execution"""
    command: VoiceCommand
    executed: bool = Field(..., description="Whether command was executed successfully")
    result: Optional[Dict[str, Any]] = Field(None, description="Command execution result")
    message: str = Field(..., description="Human-readable message")
    audio_confirmation: Optional[str] = Field(None, description="Audio confirmation message")


class AudioQualityResponse(BaseModel):
    """Response from audio quality validation"""
    quality: AudioQuality = Field(..., description="Quality level: excellent, good, fair, poor")
    suitable: bool = Field(..., description="Whether audio is suitable for transcription")
    issues: List[str] = Field(..., description="List of detected issues")
    recommendations: List[str] = Field(..., description="Recommendations for improvement")


class LanguageInfo(BaseModel):
    """Language information"""
    code: str = Field(..., description="Language code")
    name: str = Field(..., description="Language name")
    supported: bool = Field(..., description="Whether language is supported")


class VoiceCommandInfo(BaseModel):
    """Voice command information"""
    command: str = Field(..., description="Command identifier")
    examples: List[str] = Field(..., description="Example phrases")
    description: str = Field(..., description="Command description")


class FieldValidationRequest(BaseModel):
    """Request to validate voice input for form field"""
    transcribed_text: str = Field(..., description="Transcribed text to validate")
    field_type: str = Field(..., description="Field type: text, number, date, email, etc.")


class FieldValidationResponse(BaseModel):
    """Response from field validation"""
    is_valid: bool = Field(..., description="Whether input is valid for field type")
    normalized_value: str = Field(..., description="Normalized/formatted value")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    suggestions: List[str] = Field(..., description="Suggestions for correction")


# API Endpoints

@router.post("/transcribe", response_model=TranscribeResponse, status_code=200)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, etc.)"),
    language: Optional[str] = Query(None, description="Language code for transcription"),
    context: str = Query("general", description="Context: general, form_field, command")
):
    """
    Transcribe audio to text (Requirement 18.1)
    
    Converts speech input to text with confidence scoring and quality assessment.
    Supports multiple languages and provides recommendations for low-quality audio.
    
    Args:
        audio: Audio file upload
        language: Optional language code (uses engine default if not specified)
        context: Context of transcription (general, form_field, command)
    
    Returns:
        Transcription result with confidence score and quality assessment
    
    Raises:
        HTTPException: If audio processing fails or format is unsupported
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )
        
        # Check audio quality first
        quality_check = speech_engine.check_audio_quality(audio_data)
        
        if not quality_check["suitable"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Audio quality insufficient for transcription",
                    "quality": quality_check["quality"],
                    "issues": quality_check["issues"],
                    "recommendations": quality_check["recommendations"]
                }
            )
        
        # Transcribe audio
        result = speech_engine.transcribe_audio(
            audio_data=audio_data,
            language=language
        )
        
        return TranscribeResponse(
            transcription_id=result.transcription_id,
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            audio_quality=result.audio_quality,
            duration_seconds=result.duration_seconds,
            requires_confirmation=result.confidence < 0.80,
            timestamp=result.timestamp.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@router.post("/command", response_model=VoiceCommandResponse, status_code=200)
async def execute_voice_command(
    audio: UploadFile = File(..., description="Audio file containing voice command"),
    language: Optional[str] = Query(None, description="Language code")
):
    """
    Execute voice command (Requirement 18.7)
    
    Processes audio input to recognize and execute voice commands for navigation
    and automation control. Provides audio confirmation of executed commands.
    
    Supported commands:
    - Navigation: "go home", "show dashboard", "open documents"
    - Automation: "start automation", "pause", "resume", "cancel"
    - Help: "help", "what can I do"
    
    Args:
        audio: Audio file with voice command
        language: Optional language code
    
    Returns:
        Command execution result with confirmation message
    
    Raises:
        HTTPException: If command cannot be recognized or executed
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )
        
        # Process voice input
        result = speech_engine.process_voice_input(
            audio_data=audio_data,
            context="command"
        )
        
        if not result["is_command"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No valid voice command recognized",
                    "transcription": result["text"],
                    "confidence": result["confidence"],
                    "suggestion": "Try one of the supported commands. Use GET /speech/commands to see available commands."
                }
            )
        
        command = result["command"]
        
        # Execute command (in production, this would trigger actual actions)
        execution_result = {
            "action": command.value,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate confirmation message
        confirmation_messages = {
            VoiceCommand.NAVIGATE_HOME: "Navigating to home page",
            VoiceCommand.NAVIGATE_DASHBOARD: "Opening your dashboard",
            VoiceCommand.START_AUTOMATION: "Starting browser automation",
            VoiceCommand.PAUSE_AUTOMATION: "Pausing automation",
            VoiceCommand.RESUME_AUTOMATION: "Resuming automation",
            VoiceCommand.UPLOAD_DOCUMENT: "Opening document upload",
            VoiceCommand.SUBMIT_FORM: "Submitting form",
            VoiceCommand.HELP: "Showing help information",
            VoiceCommand.CANCEL: "Canceling current action"
        }
        
        message = confirmation_messages.get(command, "Command executed")
        
        return VoiceCommandResponse(
            command=command,
            executed=True,
            result=execution_result,
            message=message,
            audio_confirmation=message  # In production, this would be audio URL
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute voice command: {str(e)}"
        )


@router.get("/languages", response_model=List[LanguageInfo])
async def get_supported_languages():
    """
    Get supported languages for speech recognition
    
    Returns list of all languages supported by the speech recognition engine
    with their codes and names.
    
    Returns:
        List of supported languages with details
    """
    try:
        language_names = {
            "en": "English",
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "bn": "Bengali"
        }
        
        languages = [
            LanguageInfo(
                code=code,
                name=language_names.get(code, code.upper()),
                supported=True
            )
            for code in speech_engine.supported_languages
        ]
        
        return languages
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve supported languages: {str(e)}"
        )


@router.post("/validate", response_model=AudioQualityResponse)
async def validate_audio_quality(
    audio: UploadFile = File(..., description="Audio file to validate")
):
    """
    Validate audio quality before transcription
    
    Checks audio quality and provides recommendations for improvement
    if quality is insufficient for reliable transcription.
    
    Args:
        audio: Audio file to validate
    
    Returns:
        Quality assessment with issues and recommendations
    
    Raises:
        HTTPException: If audio validation fails
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )
        
        # Check audio quality
        quality_check = speech_engine.check_audio_quality(audio_data)
        
        return AudioQualityResponse(
            quality=quality_check["quality"],
            suitable=quality_check["suitable"],
            issues=quality_check["issues"],
            recommendations=quality_check["recommendations"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate audio quality: {str(e)}"
        )


@router.get("/commands", response_model=List[VoiceCommandInfo])
async def get_available_commands(
    language: str = Query("en", description="Language code for command examples")
):
    """
    Get available voice commands
    
    Returns list of all supported voice commands with example phrases
    and descriptions in the specified language.
    
    Args:
        language: Language code for examples (default: en)
    
    Returns:
        List of voice commands with examples and descriptions
    """
    try:
        commands = speech_engine.get_voice_command_help(language=language)
        
        return [
            VoiceCommandInfo(
                command=cmd["command"].value,
                examples=cmd["examples"],
                description=cmd["description"]
            )
            for cmd in commands
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve voice commands: {str(e)}"
        )


@router.post("/validate-field", response_model=FieldValidationResponse)
async def validate_field_input(request: FieldValidationRequest):
    """
    Validate voice input for form field
    
    Validates transcribed text against form field requirements and provides
    normalized values and correction suggestions.
    
    Args:
        request: Validation request with transcribed text and field type
    
    Returns:
        Validation result with normalized value and suggestions
    """
    try:
        validation = speech_engine.validate_field_input(
            transcribed_text=request.transcribed_text,
            field_type=request.field_type
        )
        
        return FieldValidationResponse(
            is_valid=validation["is_valid"],
            normalized_value=validation["normalized_value"],
            error_message=validation["error_message"],
            suggestions=validation["suggestions"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate field input: {str(e)}"
        )


@router.post("/language", response_model=Dict[str, Any])
async def set_recognition_language(
    language: str = Query(..., description="Language code to set")
):
    """
    Set speech recognition language
    
    Changes the active language model for speech recognition.
    
    Args:
        language: Language code (en, hi, ta, te, bn)
    
    Returns:
        Confirmation of language change
    
    Raises:
        HTTPException: If language is not supported
    """
    try:
        success = speech_engine.set_language(language)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Language '{language}' is not supported. Use GET /speech/languages to see supported languages."
            )
        
        return {
            "success": True,
            "language": language,
            "message": f"Speech recognition language set to {language}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set language: {str(e)}"
        )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_transcription_history(
    limit: int = Query(10, description="Maximum number of records to return"),
    exclude_sensitive: bool = Query(True, description="Exclude sensitive data from history")
):
    """
    Get transcription history
    
    Returns recent transcription history for the user. Sensitive data
    is excluded by default for privacy.
    
    Args:
        limit: Maximum number of records (default: 10)
        exclude_sensitive: Whether to exclude sensitive data (default: true)
    
    Returns:
        List of transcription records
    """
    try:
        history = speech_engine.get_transcription_history(
            limit=limit,
            exclude_sensitive=exclude_sensitive
        )
        
        return history
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcription history: {str(e)}"
        )


@router.post("/continuous/enable", response_model=Dict[str, Any])
async def enable_continuous_listening():
    """
    Enable continuous voice navigation
    
    Enables continuous listening mode where the system listens for
    voice commands without requiring repeated activation.
    
    Returns:
        Confirmation of continuous listening activation
    """
    try:
        success = speech_engine.enable_continuous_listening()
        
        return {
            "success": success,
            "mode": "continuous",
            "message": "Continuous voice navigation enabled"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable continuous listening: {str(e)}"
        )


@router.post("/continuous/disable", response_model=Dict[str, Any])
async def disable_continuous_listening():
    """
    Disable continuous voice navigation
    
    Disables continuous listening mode and returns to manual activation.
    
    Returns:
        Confirmation of continuous listening deactivation
    """
    try:
        success = speech_engine.disable_continuous_listening()
        
        return {
            "success": success,
            "mode": "manual",
            "message": "Continuous voice navigation disabled"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable continuous listening: {str(e)}"
        )


# Health check endpoint
@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Health check for speech recognition service
    
    Returns the current status and configuration of the speech recognition engine.
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "speech-recognition",
        "current_language": speech_engine.current_language,
        "supported_languages": speech_engine.supported_languages,
        "transcription_count": len(speech_engine.transcription_history)
    }
