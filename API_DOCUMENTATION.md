# API Documentation - Government Services Assistant

Complete REST API documentation for the Government Services Assistant.

Base URL: `http://localhost:8000/api/v1`

## Authentication

Currently using user_id for identification. In production, implement JWT tokens.

## Endpoints

### Conversational Agent

#### POST /agent/chat
Send message to AI agent and get response.

**Request:**
```json
{
  "user_id": "string",
  "session_id": "string (optional)",
  "message": "string",
  "language": "en|hi|ta|te",
  "request_type": "string (optional)"
}
```

**Response:**
```json
{
  "session_id": "string",
  "response": "string",
  "request_type": "string",
  "links": ["string"],
  "action_items": ["string"],
  "warnings": ["string"]
}
```

#### GET /agent/services
List available government services.

**Query Parameters:**
- `category` (optional): Filter by category

**Response:**
```json
{
  "services": [
    {
      "service_id": "string",
      "name": "string",
      "category": "string",
      "description": "string"
    }
  ]
}
```

#### GET /agent/services/{service_id}
Get detailed service information.

**Response:**
```json
{
  "service_id": "string",
  "name": "string",
  "category": "string",
  "description": "string",
  "steps": [...],
  "eligibility_criteria": [...],
  "document_requirements": [...],
  "portal_url": "string"
}
```

#### POST /agent/eligibility/check
Check eligibility for a service.

**Request:**
```json
{
  "user_id": "string",
  "service_id": "string",
  "user_data": {
    "age": 25,
    "income": 500000,
    "state": "Maharashtra"
  }
}
```

**Response:**
```json
{
  "eligible": true,
  "met_criteria": [...],
  "failed_criteria": [...],
  "missing_information": [...],
  "alternatives": [...]
}
```

### Document Management

#### POST /documents/upload
Upload a document with optional OCR processing.

**Form Data:**
- `file`: File (required)
- `user_id`: string (required)
- `category`: string (optional)
- `trigger_ocr`: boolean (optional, default: true)

**Response:**
```json
{
  "document_id": "string",
  "filename": "string",
  "size_bytes": 123456,
  "category": "string",
  "ocr_task_id": "string (if OCR triggered)"
}
```

#### GET /documents/list
List user's documents.

**Query Parameters:**
- `user_id` (required)
- `category` (optional)
- `limit` (optional, default: 50)

**Response:**
```json
{
  "documents": [
    {
      "document_id": "string",
      "filename": "string",
      "category": "string",
      "size_bytes": 123456,
      "uploaded_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### GET /documents/{document_id}
Retrieve a document.

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "document_id": "string",
  "filename": "string",
  "content": "base64-encoded-content",
  "metadata": {...}
}
```

#### DELETE /documents/{document_id}
Delete a document.

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

#### GET /documents/ocr/status/{task_id}
Get OCR processing status.

**Response:**
```json
{
  "task_id": "string",
  "status": "queued|processing|completed|failed",
  "progress": 75.0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /documents/ocr/result/{task_id}
Get OCR extraction result.

**Response:**
```json
{
  "document_type": "aadhaar",
  "fields": [
    {
      "field_name": "name",
      "value": "John Doe",
      "confidence": 0.95,
      "normalized_value": "JOHN DOE"
    }
  ],
  "confidence": 0.92,
  "raw_text": "..."
}
```

### Browser Automation

#### POST /automation/start
Start browser automation session.

**Request:**
```json
{
  "user_id": "string",
  "service_id": "string",
  "portal_url": "string",
  "workflow": {
    "workflow_id": "string",
    "steps": [...]
  }
}
```

**Response:**
```json
{
  "session_id": "string",
  "status": "started",
  "message": "Automation session started successfully"
}
```

#### POST /automation/{session_id}/pause
Pause automation session.

**Query Parameters:**
- `reason` (optional)

**Response:**
```json
{
  "message": "Automation paused"
}
```

#### POST /automation/{session_id}/resume
Resume paused session.

**Response:**
```json
{
  "message": "Automation resumed"
}
```

#### GET /automation/{session_id}/status
Get automation status.

**Response:**
```json
{
  "session_id": "string",
  "status": "running|paused|completed|failed",
  "current_step": 2,
  "total_steps": 5,
  "progress_percentage": 40.0,
  "current_url": "string"
}
```

#### GET /automation/{session_id}/logs
Get automation action logs.

**Query Parameters:**
- `limit` (optional, default: 50)

**Response:**
```json
{
  "logs": [
    {
      "action_id": "string",
      "action_type": "navigate|fill_field|click|submit",
      "timestamp": "2024-01-01T00:00:00Z",
      "details": {...},
      "success": true,
      "error": null
    }
  ]
}
```

### Dashboard

#### GET /dashboard/{user_id}
Get complete dashboard data.

**Response:**
```json
{
  "user_id": "string",
  "active_requests": [...],
  "recent_documents": [...],
  "notifications": [...],
  "storage_usage": {
    "used_bytes": 12345678,
    "total_bytes": 104857600,
    "percentage": 11.8
  },
  "quick_links": [...],
  "service_history": [...]
}
```

#### GET /dashboard/{user_id}/summary
Get dashboard summary statistics.

**Response:**
```json
{
  "active_requests": 3,
  "unread_notifications": 5,
  "total_documents": 12,
  "storage_percentage": 11.8,
  "pending_actions": 2
}
```

#### GET /dashboard/{user_id}/notifications
Get user notifications.

**Query Parameters:**
- `unread_only` (optional, default: false)

**Response:**
```json
{
  "notifications": [
    {
      "notification_id": "string",
      "title": "string",
      "message": "string",
      "type": "info|warning|error|success",
      "timestamp": "2024-01-01T00:00:00Z",
      "read": false,
      "action_url": "string (optional)"
    }
  ]
}
```

### DigiLocker Integration

#### GET /digilocker/auth/url
Get OAuth authorization URL.

**Query Parameters:**
- `user_id` (required)
- `scope` (optional, default: "public")

**Response:**
```json
{
  "auth_url": "string",
  "state": "string"
}
```

#### POST /digilocker/auth/callback
Handle OAuth callback.

**Request:**
```json
{
  "code": "string",
  "state": "string"
}
```

**Response:**
```json
{
  "user_id": "string",
  "expires_at": "2024-01-01T00:00:00Z",
  "scope": "public"
}
```

#### GET /digilocker/documents
List documents from DigiLocker.

**Query Parameters:**
- `user_id` (required)
- `category` (optional)

**Response:**
```json
{
  "documents": [
    {
      "doc_id": "string",
      "doc_name": "string",
      "doc_type": "string",
      "issuer": "string",
      "category": "string",
      "size_bytes": 123456
    }
  ]
}
```

#### POST /digilocker/documents/{doc_id}/import
Import document from DigiLocker.

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "doc_id": "string",
  "doc_name": "string",
  "category": "string",
  "imported_at": "2024-01-01T00:00:00Z",
  "source": "digilocker"
}
```

#### POST /digilocker/sync
Sync documents from DigiLocker.

**Query Parameters:**
- `user_id` (required)
- `auto_import` (optional, default: false)

**Response:**
```json
{
  "sync_id": "string"
}
```

### Workflows

#### GET /workflows/
List available workflows.

**Query Parameters:**
- `service_id` (optional)
- `portal_url` (optional)

**Response:**
```json
{
  "workflows": [
    {
      "workflow_id": "string",
      "name": "string",
      "description": "string",
      "service_id": "string",
      "portal_url": "string",
      "total_steps": 4,
      "estimated_duration_minutes": 15,
      "required_documents": ["string"]
    }
  ]
}
```

#### GET /workflows/{workflow_id}
Get workflow definition.

**Response:**
```json
{
  "workflow_id": "string",
  "name": "string",
  "description": "string",
  "steps": [
    {
      "step_number": 1,
      "name": "string",
      "description": "string",
      "page_url": "string",
      "actions": [...],
      "expected_elements": ["string"],
      "success_indicators": ["string"]
    }
  ],
  "form_mappings": [...],
  "required_documents": ["string"]
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message"
}
```

**Status Codes:**
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

## Rate Limiting

- 100 requests per minute per user
- 1000 requests per hour per user
- Exceeded limits return 429 status

## WebSocket Support (Future)

Real-time updates for:
- Automation progress
- OCR processing status
- Notifications
- Dashboard updates

Endpoint: `ws://localhost:8000/ws/{user_id}`

## SDK Examples

### Python
```python
import requests

# Chat with agent
response = requests.post(
    'http://localhost:8000/api/v1/agent/chat',
    json={
        'user_id': 'user123',
        'message': 'How do I change my Aadhaar name?',
        'language': 'en'
    }
)
print(response.json())
```

### JavaScript
```javascript
// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch(
  'http://localhost:8000/api/v1/documents/upload?user_id=user123',
  {
    method: 'POST',
    body: formData
  }
);
const data = await response.json();
```

## Testing

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
