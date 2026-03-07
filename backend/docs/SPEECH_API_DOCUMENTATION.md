# Speech-to-Text API Documentation

## Overview

The Speech-to-Text API provides REST endpoints for speech input processing and voice command execution. It enables users to interact with the Government Services Assistant using voice input, supporting multiple languages and providing privacy-preserving local processing.

## Base URL

```
/api/v1/speech
```

## Features

- **Audio Transcription**: Convert speech to text with confidence scoring
- **Voice Commands**: Execute navigation and automation commands via voice
- **Multi-Language Support**: Support for English, Hindi, Tamil, Telugu, and Bengali
- **Audio Quality Validation**: Check audio quality before transcription
- **Field Validation**: Validate voice input for form fields
- **Privacy-Preserving**: Local processing without external audio transmission
- **Transcription History**: Track transcription history with privacy controls

## Endpoints

### 1. Transcribe Audio

**POST** `/transcribe`

Converts speech input to text with confidence scoring and quality assessment.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `audio` (file, required): Audio file (WAV, MP3, etc.)
  - `language` (query, optional): Language code (en, hi, ta, te, bn)
  - `context` (query, optional): Context (general, form_field, command)

**Response:**
```json
{
  "transcription_id": "trans_1234567890.123",
  "text": "Transcribed speech text",
  "confidence": 0.92,
  "language": "en",
  "audio_quality": "good",
  "duration_seconds": 3.5,
  "requires_confirmation": false,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK`: Transcription successful
- `400 Bad Request`: Empty audio or poor quality
- `500 Internal Server Error`: Processing failed



### 2. Execute Voice Command

**POST** `/command`

Processes audio input to recognize and execute voice commands.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `audio` (file, required): Audio file containing voice command
  - `language` (query, optional): Language code

**Supported Commands:**
- Navigation: "go home", "show dashboard", "open documents"
- Automation: "start automation", "pause", "resume", "cancel"
- Help: "help", "what can I do"

**Response:**
```json
{
  "command": "navigate_dashboard",
  "executed": true,
  "result": {
    "action": "navigate_dashboard",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Opening your dashboard",
  "audio_confirmation": "Opening your dashboard"
}
```

**Status Codes:**
- `200 OK`: Command executed successfully
- `400 Bad Request`: No valid command recognized
- `500 Internal Server Error`: Execution failed

---

### 3. Get Supported Languages

**GET** `/languages`

Returns list of all supported languages for speech recognition.

**Response:**
```json
[
  {
    "code": "en",
    "name": "English",
    "supported": true
  },
  {
    "code": "hi",
    "name": "Hindi",
    "supported": true
  }
]
```

**Status Codes:**
- `200 OK`: Languages retrieved successfully

---

### 4. Validate Audio Quality

**POST** `/validate`

Checks audio quality and provides recommendations for improvement.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `audio` (file, required): Audio file to validate

**Response:**
```json
{
  "quality": "good",
  "suitable": true,
  "issues": [],
  "recommendations": []
}
```

**Quality Levels:**
- `excellent`: Optimal quality for transcription
- `good`: Suitable for transcription
- `fair`: Acceptable but may have lower confidence
- `poor`: Not suitable for reliable transcription

**Status Codes:**
- `200 OK`: Validation successful
- `400 Bad Request`: Empty audio file



### 5. Get Available Commands

**GET** `/commands`

Returns list of all supported voice commands with examples.

**Parameters:**
- `language` (query, optional): Language code (default: en)

**Response:**
```json
[
  {
    "command": "navigate_home",
    "examples": ["go home", "home page", "main page"],
    "description": "Navigate to home page"
  },
  {
    "command": "navigate_dashboard",
    "examples": ["go to dashboard", "open dashboard", "show dashboard"],
    "description": "Open your dashboard"
  }
]
```

**Status Codes:**
- `200 OK`: Commands retrieved successfully

---

### 6. Validate Field Input

**POST** `/validate-field`

Validates transcribed text against form field requirements.

**Request:**
```json
{
  "transcribed_text": "one two three four",
  "field_type": "number"
}
```

**Field Types:**
- `text`: General text input
- `number`: Numeric input
- `date`: Date input
- `email`: Email address

**Response:**
```json
{
  "is_valid": true,
  "normalized_value": "1234",
  "error_message": null,
  "suggestions": []
}
```

**Status Codes:**
- `200 OK`: Validation successful
- `422 Unprocessable Entity`: Invalid request

---

### 7. Set Recognition Language

**POST** `/language`

Changes the active language model for speech recognition.

**Parameters:**
- `language` (query, required): Language code (en, hi, ta, te, bn)

**Response:**
```json
{
  "success": true,
  "language": "hi",
  "message": "Speech recognition language set to hi"
}
```

**Status Codes:**
- `200 OK`: Language set successfully
- `400 Bad Request`: Unsupported language

---

### 8. Get Transcription History

**GET** `/history`

Returns recent transcription history for the user.

**Parameters:**
- `limit` (query, optional): Maximum records (default: 10)
- `exclude_sensitive` (query, optional): Exclude sensitive data (default: true)

**Response:**
```json
[
  {
    "transcription_id": "trans_1234567890.123",
    "text": "[REDACTED]",
    "confidence": 0.92,
    "language": "en",
    "timestamp": "2024-01-15T10:30:00Z",
    "audio_quality": "good"
  }
]
```

**Status Codes:**
- `200 OK`: History retrieved successfully



### 9. Enable Continuous Listening

**POST** `/continuous/enable`

Enables continuous listening mode for voice navigation.

**Response:**
```json
{
  "success": true,
  "mode": "continuous",
  "message": "Continuous voice navigation enabled"
}
```

**Status Codes:**
- `200 OK`: Continuous listening enabled

---

### 10. Disable Continuous Listening

**POST** `/continuous/disable`

Disables continuous listening mode.

**Response:**
```json
{
  "success": true,
  "mode": "manual",
  "message": "Continuous voice navigation disabled"
}
```

**Status Codes:**
- `200 OK`: Continuous listening disabled

---

### 11. Health Check

**GET** `/health`

Returns the current status of the speech recognition service.

**Response:**
```json
{
  "status": "healthy",
  "service": "speech-recognition",
  "current_language": "en",
  "supported_languages": ["en", "hi", "ta", "te", "bn"],
  "transcription_count": 42
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

## Usage Examples

### Example 1: Transcribe Audio File

```bash
curl -X POST "http://localhost:8000/api/v1/speech/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@recording.wav" \
  -F "language=en"
```

### Example 2: Execute Voice Command

```bash
curl -X POST "http://localhost:8000/api/v1/speech/command" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@command.wav"
```

### Example 3: Get Supported Languages

```bash
curl -X GET "http://localhost:8000/api/v1/speech/languages"
```

### Example 4: Validate Audio Quality

```bash
curl -X POST "http://localhost:8000/api/v1/speech/validate" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@test.wav"
```

### Example 5: Get Voice Commands

```bash
curl -X GET "http://localhost:8000/api/v1/speech/commands?language=hi"
```

---

## Privacy and Security

### Local Processing
- All speech recognition is performed locally on the user's device
- Audio data is NOT transmitted to external servers
- Ensures user privacy and data security

### Sensitive Data Handling
- Transcription history excludes sensitive data by default
- Users can control whether sensitive data is included in history
- Voice input containing sensitive information is not logged

### Confidence Scoring
- Low confidence transcriptions (< 0.80) require user confirmation
- Prevents errors from incorrect transcriptions
- Users can review and correct transcriptions before submission

---

## Error Handling

### Common Error Responses

**400 Bad Request - Empty Audio**
```json
{
  "detail": "Empty audio file provided"
}
```

**400 Bad Request - Poor Quality**
```json
{
  "detail": {
    "error": "Audio quality insufficient for transcription",
    "quality": "poor",
    "issues": ["Audio too short", "Insufficient data"],
    "recommendations": [
      "Speak closer to the microphone",
      "Reduce background noise"
    ]
  }
}
```

**400 Bad Request - No Command Recognized**
```json
{
  "detail": {
    "error": "No valid voice command recognized",
    "transcription": "some random text",
    "confidence": 0.85,
    "suggestion": "Try one of the supported commands..."
  }
}
```

**400 Bad Request - Unsupported Language**
```json
{
  "detail": "Language 'xyz' is not supported..."
}
```

---

## Requirements Implemented

This API implements the following requirements from the specification:

- **Requirement 18.1**: Speech input capture and transcription
- **Requirement 18.7**: Voice command processing and execution

---

## Testing

Comprehensive unit tests are available in `backend/tests/test_speech_api.py`:

```bash
# Run all speech API tests
pytest tests/test_speech_api.py -v

# Run specific test
pytest tests/test_speech_api.py::test_transcribe_audio_success -v
```

Test coverage includes:
- Audio transcription with multiple languages
- Voice command recognition
- Audio quality validation
- Field input validation
- Privacy controls
- Error handling
- Integration workflows

---

## Notes

- Audio files should be in common formats (WAV, MP3, etc.)
- Recommended audio quality: 16kHz sample rate or higher
- Maximum audio file size: Determined by server configuration
- Transcription typically completes within 3 seconds
- Voice commands are case-insensitive
- Commands can include extra words and still be recognized
