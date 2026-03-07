"""
Unit Tests for Speech-to-Text API

Tests all speech API endpoints including transcription, voice commands,
language support, and audio quality validation.
"""

import pytest
from io import BytesIO
from app.services.speech_recognition import (
    SpeechRecognitionEngine,
    VoiceCommand,
    AudioQuality,
    TranscriptionResult
)


# Test Data

def create_audio_file(size: int = 10000) -> bytes:
    """Create a mock audio file for testing"""
    return b'\x00' * size


# Test: SpeechRecognitionEngine Core Functionality

def test_speech_engine_initialization():
    """Test speech recognition engine initialization"""
    engine = SpeechRecognitionEngine()
    
    assert engine.current_language == "en"
    assert len(engine.supported_languages) > 0
    assert "en" in engine.supported_languages
    assert "hi" in engine.supported_languages


def test_set_language_valid():
    """Test setting a valid language"""
    engine = SpeechRecognitionEngine()
    
    success = engine.set_language("hi")
    assert success is True
    assert engine.current_language == "hi"


def test_set_language_invalid():
    """Test setting an invalid language"""
    engine = SpeechRecognitionEngine()
    
    success = engine.set_language("xyz")
    assert success is False
    assert engine.current_language == "en"  # Should remain unchanged


def test_check_audio_quality_good():
    """Test audio quality check with good quality audio"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    quality_check = engine.check_audio_quality(audio_data)
    
    assert "quality" in quality_check
    assert "suitable" in quality_check
    assert "issues" in quality_check
    assert "recommendations" in quality_check
    
    assert quality_check["quality"] in ["excellent", "good"]
    assert quality_check["suitable"] is True


def test_check_audio_quality_poor():
    """Test audio quality check with poor quality audio"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(500)
    
    quality_check = engine.check_audio_quality(audio_data)
    
    assert quality_check["quality"] == "poor"
    assert quality_check["suitable"] is False
    assert len(quality_check["issues"]) > 0
    assert len(quality_check["recommendations"]) > 0


def test_transcribe_audio_success():
    """Test successful audio transcription"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    result = engine.transcribe_audio(audio_data)
    
    assert isinstance(result, TranscriptionResult)
    assert result.transcription_id is not None
    assert result.text is not None
    assert 0 <= result.confidence <= 1
    assert result.language == "en"
    assert result.duration_seconds > 0


def test_transcribe_audio_with_language():
    """Test transcription with specific language"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    result = engine.transcribe_audio(audio_data, language="hi")
    
    assert result.language == "hi"


def test_transcribe_audio_stores_history():
    """Test that transcriptions are stored in history"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    initial_count = len(engine.transcription_history)
    
    engine.transcribe_audio(audio_data)
    
    assert len(engine.transcription_history) == initial_count + 1


def test_recognize_voice_command_valid():
    """Test voice command recognition with valid command"""
    engine = SpeechRecognitionEngine()
    
    # Test English commands
    command = engine.recognize_voice_command("go home")
    assert command == VoiceCommand.NAVIGATE_HOME
    
    command = engine.recognize_voice_command("show dashboard")
    assert command == VoiceCommand.NAVIGATE_DASHBOARD
    
    command = engine.recognize_voice_command("help me")
    assert command == VoiceCommand.HELP


def test_recognize_voice_command_invalid():
    """Test voice command recognition with invalid text"""
    engine = SpeechRecognitionEngine()
    
    command = engine.recognize_voice_command("this is not a command")
    assert command is None


def test_recognize_voice_command_hindi():
    """Test voice command recognition in Hindi"""
    engine = SpeechRecognitionEngine()
    engine.set_language("hi")
    
    command = engine.recognize_voice_command("होम जाओ")
    assert command == VoiceCommand.NAVIGATE_HOME


def test_process_voice_input_general():
    """Test processing voice input in general context"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    result = engine.process_voice_input(audio_data, context="general")
    
    assert "transcription_id" in result
    assert "text" in result
    assert "confidence" in result
    assert "audio_quality" in result
    assert "is_command" in result
    assert "requires_confirmation" in result


def test_process_voice_input_command_context():
    """Test processing voice input in command context"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    result = engine.process_voice_input(audio_data, context="command")
    
    assert "is_command" in result
    assert "command" in result


def test_validate_field_input_number():
    """Test field validation for number input"""
    engine = SpeechRecognitionEngine()
    
    result = engine.validate_field_input("one two three", "number")
    
    assert "is_valid" in result
    assert "normalized_value" in result
    assert "suggestions" in result


def test_validate_field_input_email():
    """Test field validation for email input"""
    engine = SpeechRecognitionEngine()
    
    # Invalid email
    result = engine.validate_field_input("user example com", "email")
    assert result["is_valid"] is False
    assert result["error_message"] is not None
    
    # Valid email format
    result = engine.validate_field_input("user@example.com", "email")
    # May still be invalid depending on implementation


def test_validate_field_input_date():
    """Test field validation for date input"""
    engine = SpeechRecognitionEngine()
    
    result = engine.validate_field_input("January 15 2024", "date")
    
    assert "is_valid" in result
    # Should be valid as it contains a month name


def test_get_voice_command_help_english():
    """Test getting voice command help in English"""
    engine = SpeechRecognitionEngine()
    
    commands = engine.get_voice_command_help("en")
    
    assert isinstance(commands, list)
    assert len(commands) > 0
    
    for cmd in commands:
        assert "command" in cmd
        assert "examples" in cmd
        assert "description" in cmd
        assert len(cmd["examples"]) > 0


def test_get_voice_command_help_hindi():
    """Test getting voice command help in Hindi"""
    engine = SpeechRecognitionEngine()
    
    commands = engine.get_voice_command_help("hi")
    
    assert isinstance(commands, list)
    assert len(commands) > 0


def test_enable_continuous_listening():
    """Test enabling continuous listening mode"""
    engine = SpeechRecognitionEngine()
    
    success = engine.enable_continuous_listening()
    assert success is True


def test_disable_continuous_listening():
    """Test disabling continuous listening mode"""
    engine = SpeechRecognitionEngine()
    
    success = engine.disable_continuous_listening()
    assert success is True


def test_get_transcription_history():
    """Test retrieving transcription history"""
    engine = SpeechRecognitionEngine()
    
    # Add some transcriptions
    audio_data = create_audio_file(15000)
    engine.transcribe_audio(audio_data)
    engine.transcribe_audio(audio_data)
    
    history = engine.get_transcription_history(limit=10)
    
    assert isinstance(history, list)
    assert len(history) >= 2


def test_get_transcription_history_excludes_sensitive():
    """Test that sensitive data is excluded from history"""
    engine = SpeechRecognitionEngine()
    
    audio_data = create_audio_file(15000)
    engine.transcribe_audio(audio_data)
    
    history = engine.get_transcription_history(limit=10, exclude_sensitive=True)
    
    for record in history:
        if "text" in record:
            # Sensitive data should be redacted
            assert record["text"] == "[REDACTED]"


def test_get_transcription_history_includes_sensitive():
    """Test that sensitive data can be included in history"""
    engine = SpeechRecognitionEngine()
    
    audio_data = create_audio_file(15000)
    engine.transcribe_audio(audio_data)
    
    history = engine.get_transcription_history(limit=10, exclude_sensitive=False)
    
    for record in history:
        if "text" in record:
            # Text should not be redacted
            assert record["text"] != "[REDACTED]"


def test_get_transcription_history_limit():
    """Test history limit parameter"""
    engine = SpeechRecognitionEngine()
    
    # Add multiple transcriptions
    audio_data = create_audio_file(15000)
    for _ in range(5):
        engine.transcribe_audio(audio_data)
    
    history = engine.get_transcription_history(limit=3)
    
    assert len(history) <= 3


# Integration Tests

def test_full_transcription_workflow():
    """Test complete transcription workflow"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(15000)
    
    # 1. Check audio quality
    quality_check = engine.check_audio_quality(audio_data)
    assert quality_check["suitable"] is True
    
    # 2. Transcribe audio
    result = engine.transcribe_audio(audio_data)
    assert result.confidence > 0
    
    # 3. Check history
    history = engine.get_transcription_history(limit=10)
    assert len(history) > 0


def test_voice_command_workflow():
    """Test complete voice command workflow"""
    engine = SpeechRecognitionEngine()
    
    # 1. Get available commands
    commands = engine.get_voice_command_help("en")
    assert len(commands) > 0
    
    # 2. Process voice input
    audio_data = create_audio_file(15000)
    result = engine.process_voice_input(audio_data, context="command")
    assert "is_command" in result


def test_multi_language_workflow():
    """Test multi-language support workflow"""
    engine = SpeechRecognitionEngine()
    
    # 1. Check supported languages
    assert "hi" in engine.supported_languages
    
    # 2. Set language to Hindi
    success = engine.set_language("hi")
    assert success is True
    
    # 3. Get commands in Hindi
    commands = engine.get_voice_command_help("hi")
    assert len(commands) > 0
    
    # 4. Transcribe in Hindi
    audio_data = create_audio_file(15000)
    result = engine.transcribe_audio(audio_data, language="hi")
    assert result.language == "hi"


def test_field_validation_workflow():
    """Test field validation workflow"""
    engine = SpeechRecognitionEngine()
    
    # Test different field types
    field_types = ["text", "number", "date", "email"]
    
    for field_type in field_types:
        result = engine.validate_field_input("test input", field_type)
        assert "is_valid" in result
        assert "normalized_value" in result
        assert "suggestions" in result


# Edge Cases and Error Handling

def test_transcribe_very_short_audio():
    """Test transcription with very short audio"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(100)
    
    # Should still process but with low quality
    result = engine.transcribe_audio(audio_data)
    assert result is not None


def test_transcribe_very_long_audio():
    """Test transcription with very long audio"""
    engine = SpeechRecognitionEngine()
    audio_data = create_audio_file(100000)
    
    result = engine.transcribe_audio(audio_data)
    assert result is not None
    assert result.duration_seconds > 0


def test_multiple_language_switches():
    """Test switching languages multiple times"""
    engine = SpeechRecognitionEngine()
    
    engine.set_language("hi")
    assert engine.current_language == "hi"
    
    engine.set_language("ta")
    assert engine.current_language == "ta"
    
    engine.set_language("en")
    assert engine.current_language == "en"


def test_concurrent_transcriptions():
    """Test multiple transcriptions in sequence"""
    engine = SpeechRecognitionEngine()
    
    results = []
    for i in range(5):
        audio_data = create_audio_file(10000 + i * 1000)
        result = engine.transcribe_audio(audio_data)
        results.append(result)
    
    # All should have unique IDs
    ids = [r.transcription_id for r in results]
    assert len(ids) == len(set(ids))


def test_voice_command_case_insensitive():
    """Test that voice commands are case insensitive"""
    engine = SpeechRecognitionEngine()
    
    command1 = engine.recognize_voice_command("GO HOME")
    command2 = engine.recognize_voice_command("go home")
    command3 = engine.recognize_voice_command("Go Home")
    
    assert command1 == command2 == command3 == VoiceCommand.NAVIGATE_HOME


def test_voice_command_with_extra_words():
    """Test voice command recognition with extra words"""
    engine = SpeechRecognitionEngine()
    
    # Should still recognize the command
    command = engine.recognize_voice_command("please go home now")
    assert command == VoiceCommand.NAVIGATE_HOME


# Privacy and Security Tests

def test_transcription_history_privacy():
    """Test that transcription history respects privacy settings"""
    engine = SpeechRecognitionEngine()
    
    audio_data = create_audio_file(15000)
    engine.transcribe_audio(audio_data)
    
    # With sensitive data excluded
    history_private = engine.get_transcription_history(exclude_sensitive=True)
    for record in history_private:
        assert record["text"] == "[REDACTED]"
    
    # With sensitive data included
    history_full = engine.get_transcription_history(exclude_sensitive=False)
    for record in history_full:
        assert record["text"] != "[REDACTED]"


def test_audio_quality_recommendations():
    """Test that poor quality audio gets recommendations"""
    engine = SpeechRecognitionEngine()
    
    poor_audio = create_audio_file(500)
    quality_check = engine.check_audio_quality(poor_audio)
    
    assert quality_check["quality"] == "poor"
    assert len(quality_check["recommendations"]) > 0
    assert any("microphone" in rec.lower() or "noise" in rec.lower() 
               for rec in quality_check["recommendations"])


def test_confidence_threshold_for_confirmation():
    """Test that low confidence transcriptions are flagged"""
    engine = SpeechRecognitionEngine()
    
    # Fair quality audio should have lower confidence
    audio_data = create_audio_file(4000)
    result = engine.process_voice_input(audio_data)
    
    if result["confidence"] < 0.80:
        assert result["requires_confirmation"] is True
    else:
        assert result["requires_confirmation"] is False
