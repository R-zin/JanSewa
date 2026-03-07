# OCR and Document Parsing API Documentation

## Overview

The OCR API provides endpoints for optical character recognition and document parsing. It enables automatic extraction of structured data from government documents with support for manual corrections and learning from user feedback.

**Base URL**: `/api/v1/ocr`

**Requirements Implemented**:
- Requirement 20.1: Automatic OCR processing
- Requirement 20.15: Status tracking and result retrieval
- Requirement 20.13: Manual correction interface
- Requirement 20.14: Correction history tracking

## Endpoints

### 1. Trigger OCR Processing

**POST** `/api/v1/ocr/process`

Initiates asynchronous OCR processing on a document. Returns immediately with a job ID for tracking progress.

#### Request Body

```json
{
  "document_id": "string",
  "language": "eng",
  "max_retries": 3
}
```

**Parameters**:
- `document_id` (required): ID of the document to process
- `language` (optional): OCR language code. Supported: `eng`, `hin`, `tam`, `tel`. Default: `eng`
- `max_retries` (optional): Maximum retry attempts on failure. Default: `3`

#### Response (202 Accepted)

```json
{
  "job_id": "ocr_doc123_1234567890",
  "document_id": "doc123",
  "status": "queued",
  "message": "OCR processing initiated successfully. Use job_id to check status."
}
```

#### Example

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/process" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc123",
    "language": "eng"
  }'
```

---

### 2. Get OCR Processing Status

**GET** `/api/v1/ocr/{job_id}/status`

Retrieves the current status of an OCR job including progress, timing, and result summary.

#### Path Parameters

- `job_id` (required): Unique job identifier from the process endpoint

#### Response (200 OK)

```json
{
  "job_id": "ocr_doc123_1234567890",
  "document_id": "doc123",
  "status": "processing",
  "progress": 65.0,
  "created_at": "2024-01-01T10:00:00",
  "started_at": "2024-01-01T10:00:05",
  "completed_at": null,
  "processing_time": null,
  "retry_count": 0,
  "error": null,
  "result_summary": null
}
```

**Status Values**:
- `queued`: Job is waiting to be processed
- `processing`: Job is currently being processed
- `completed`: Job completed successfully
- `failed`: Job failed after all retries
- `retrying`: Job is being retried after a failure

#### Example

```bash
curl "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/status"
```

---

### 3. Get Extracted Data

**GET** `/api/v1/ocr/{job_id}/result`

Retrieves the extracted structured data from a completed OCR job with confidence scores and review flags.

#### Path Parameters

- `job_id` (required): Unique job identifier

#### Query Parameters

- `confidence_threshold` (optional): Threshold for flagging fields needing review. Default: `0.85`

#### Response (200 OK)

```json
{
  "job_id": "ocr_doc123_1234567890",
  "document_id": "doc123",
  "document_type": "aadhaar",
  "fields": [
    {
      "field_name": "name",
      "value": "John Doe",
      "confidence": 0.95,
      "normalized_value": "John Doe",
      "needs_review": false,
      "highlight_color": "green"
    },
    {
      "field_name": "aadhaar_number",
      "value": "1234 5678 9012",
      "confidence": 0.98,
      "normalized_value": "123456789012",
      "needs_review": false,
      "highlight_color": "green"
    },
    {
      "field_name": "dob",
      "value": "01/01/1990",
      "confidence": 0.72,
      "normalized_value": "1990-01-01",
      "needs_review": true,
      "highlight_color": "red"
    }
  ],
  "overall_confidence": 0.88,
  "extraction_timestamp": "2024-01-01T10:00:15",
  "fields_needing_review": 1
}
```

**Highlight Colors**:
- `green`: High confidence (≥ 0.90)
- `yellow`: Medium confidence (0.75 - 0.89)
- `red`: Low confidence (< 0.75)

**Document Types**:
- `aadhaar`: Aadhaar card
- `pan`: PAN card
- `driving_license`: Driving License
- `voter_id`: Voter ID card
- `passport`: Passport
- `income_certificate`: Income certificate
- `caste_certificate`: Caste certificate
- `obc_certificate`: OBC certificate
- `educational_certificate`: Educational certificate

#### Example

```bash
curl "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/result?confidence_threshold=0.80"
```

---

### 4. Submit Manual Corrections

**POST** `/api/v1/ocr/{job_id}/corrections`

Submits manual corrections for extracted data. Corrections are stored for learning and improving future extractions.

#### Path Parameters

- `job_id` (required): Unique job identifier

#### Request Body

```json
{
  "corrections": [
    {
      "field_name": "name",
      "original_value": "John Doe",
      "corrected_value": null,
      "action": "confirm",
      "confidence_before": 0.95
    },
    {
      "field_name": "dob",
      "original_value": "01/01/1990",
      "corrected_value": "01/01/1991",
      "action": "edit",
      "confidence_before": 0.72
    },
    {
      "field_name": "invalid_field",
      "original_value": "garbage",
      "corrected_value": null,
      "action": "reject",
      "confidence_before": 0.30
    }
  ]
}
```

**Correction Actions**:
- `confirm`: Field is correct as extracted
- `edit`: Field needs correction (provide `corrected_value`)
- `reject`: Field is invalid and should be removed

#### Response (200 OK)

```json
{
  "session_id": "session_123",
  "corrections_applied": 3,
  "message": "Successfully applied 3 corrections"
}
```

#### Example

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/corrections" \
  -H "Content-Type: application/json" \
  -d '{
    "corrections": [
      {
        "field_name": "dob",
        "original_value": "01/01/1990",
        "corrected_value": "01/01/1991",
        "action": "edit",
        "confidence_before": 0.72
      }
    ]
  }'
```

---

### 5. Get Correction History

**GET** `/api/v1/ocr/{job_id}/corrections`

Retrieves the complete correction history for an OCR job including all actions taken and final values.

#### Path Parameters

- `job_id` (required): Unique job identifier

#### Response (200 OK)

```json
{
  "session_id": "session_123",
  "document_id": "doc123",
  "document_type": "aadhaar",
  "corrections": [
    {
      "field_name": "name",
      "original_value": "John Doe",
      "corrected_value": null,
      "action": "confirm",
      "confidence_before": 0.95,
      "timestamp": "2024-01-01T10:05:00"
    },
    {
      "field_name": "dob",
      "original_value": "01/01/1990",
      "corrected_value": "01/01/1991",
      "action": "edit",
      "confidence_before": 0.72,
      "timestamp": "2024-01-01T10:05:05"
    }
  ],
  "created_at": "2024-01-01T10:05:00",
  "completed_at": "2024-01-01T10:05:10",
  "summary": {
    "total_corrections": 2,
    "confirmed": 1,
    "edited": 1,
    "rejected": 0,
    "duration_seconds": 10.0
  }
}
```

#### Example

```bash
curl "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/corrections"
```

---

### 6. Get Processing Statistics

**GET** `/api/v1/ocr/statistics`

Retrieves aggregate statistics about OCR processing including success rates and performance metrics.

#### Response (200 OK)

```json
{
  "total_tasks": 100,
  "completed": 85,
  "failed": 10,
  "processing": 3,
  "queued": 2,
  "success_rate": 0.85,
  "average_processing_time": 12.5,
  "average_confidence": 0.88
}
```

#### Example

```bash
curl "http://localhost:8000/api/v1/ocr/statistics"
```

---

### 7. Get Extraction History

**GET** `/api/v1/ocr/history`

Retrieves historical OCR extraction records for auditing and tracking.

#### Query Parameters

- `document_id` (optional): Filter by specific document
- `limit` (optional): Maximum records to return. Default: `50`

#### Response (200 OK)

```json
[
  {
    "task_id": "ocr_doc123_1234567890",
    "document_id": "doc123",
    "document_type": "aadhaar",
    "fields_extracted": 5,
    "confidence": 0.92,
    "timestamp": "2024-01-01T10:00:15",
    "processing_time": 10.5
  }
]
```

#### Example

```bash
curl "http://localhost:8000/api/v1/ocr/history?document_id=doc123&limit=10"
```

---

### 8. Retry Failed Job

**POST** `/api/v1/ocr/{job_id}/retry`

Manually retries a failed OCR job. Resets the job status and resubmits for processing.

#### Path Parameters

- `job_id` (required): Job identifier to retry

#### Response (200 OK)

```json
{
  "job_id": "ocr_doc123_1234567890",
  "document_id": "doc123",
  "status": "queued",
  "message": "OCR job retry initiated successfully"
}
```

#### Example

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/retry"
```

---

### 9. Get Learning Insights

**GET** `/api/v1/ocr/learning/insights`

Retrieves insights from correction history to identify areas where OCR accuracy can be improved.

#### Response (200 OK)

```json
{
  "total_corrections": 50,
  "field_error_rates": {
    "name": 0.1,
    "dob": 0.3,
    "address": 0.4
  },
  "fields_needing_improvement": ["address", "dob"],
  "low_confidence_accuracy": 0.65
}
```

#### Example

```bash
curl "http://localhost:8000/api/v1/ocr/learning/insights"
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "detail": "OCR job is processing, not completed yet"
}
```

### 404 Not Found

```json
{
  "detail": "OCR job ocr_doc123_1234567890 not found"
}
```

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "document_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to initiate OCR processing: Document not found"
}
```

---

## Workflow Example

### Complete OCR Processing Workflow

```bash
# 1. Trigger OCR processing
JOB_ID=$(curl -X POST "http://localhost:8000/api/v1/ocr/process" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc123"}' | jq -r '.job_id')

# 2. Poll for status until completed
while true; do
  STATUS=$(curl "http://localhost:8000/api/v1/ocr/$JOB_ID/status" | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 2
done

# 3. Get extracted data
curl "http://localhost:8000/api/v1/ocr/$JOB_ID/result" | jq '.'

# 4. Submit corrections if needed
curl -X POST "http://localhost:8000/api/v1/ocr/$JOB_ID/corrections" \
  -H "Content-Type: application/json" \
  -d '{
    "corrections": [
      {
        "field_name": "dob",
        "original_value": "01/01/1990",
        "corrected_value": "01/01/1991",
        "action": "edit",
        "confidence_before": 0.72
      }
    ]
  }'

# 5. View correction history
curl "http://localhost:8000/api/v1/ocr/$JOB_ID/corrections" | jq '.'
```

---

## Integration with Document Storage

The OCR API integrates seamlessly with the Document Storage API:

```bash
# 1. Upload document with automatic OCR
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@aadhaar.jpg" \
  -F "user_id=user123" \
  -F "category=identity" \
  -F "trigger_ocr=true"

# Response includes ocr_task_id
# {
#   "document_id": "doc123",
#   "ocr_task_id": "ocr_doc123_1234567890",
#   ...
# }

# 2. Check OCR status
curl "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/status"

# 3. Get extracted data
curl "http://localhost:8000/api/v1/ocr/ocr_doc123_1234567890/result"
```

---

## Best Practices

### 1. Polling for Status

When polling for job status, use exponential backoff to reduce server load:

```python
import time
import requests

def wait_for_completion(job_id, max_wait=300):
    """Wait for OCR job to complete with exponential backoff"""
    wait_time = 1
    total_wait = 0
    
    while total_wait < max_wait:
        response = requests.get(f"http://localhost:8000/api/v1/ocr/{job_id}/status")
        status = response.json()["status"]
        
        if status == "completed":
            return True
        elif status == "failed":
            return False
        
        time.sleep(wait_time)
        total_wait += wait_time
        wait_time = min(wait_time * 2, 10)  # Max 10 seconds
    
    return False
```

### 2. Handling Low Confidence Fields

Always review fields with `needs_review: true`:

```python
def review_extraction(result):
    """Identify fields needing manual review"""
    needs_review = [
        field for field in result["fields"]
        if field["needs_review"]
    ]
    
    if needs_review:
        print(f"Please review {len(needs_review)} fields:")
        for field in needs_review:
            print(f"  - {field['field_name']}: {field['value']} (confidence: {field['confidence']})")
```

### 3. Batch Corrections

Submit all corrections in a single request for better performance:

```python
corrections = []
for field in extracted_fields:
    if field["needs_review"]:
        # Get user input
        corrected_value = get_user_correction(field)
        corrections.append({
            "field_name": field["field_name"],
            "original_value": field["value"],
            "corrected_value": corrected_value,
            "action": "edit" if corrected_value else "confirm",
            "confidence_before": field["confidence"]
        })

# Submit all at once
requests.post(
    f"http://localhost:8000/api/v1/ocr/{job_id}/corrections",
    json={"corrections": corrections}
)
```

---

## Performance Considerations

- **Async Processing**: All OCR jobs run asynchronously. Use the status endpoint to track progress.
- **Retry Logic**: Failed jobs automatically retry up to `max_retries` times with exponential backoff.
- **Caching**: Extraction results are cached and remain available after completion.
- **Rate Limiting**: Consider implementing rate limiting for high-volume applications.

---

## Security Notes

- All endpoints require authentication (implementation depends on your auth system)
- Document access is restricted to the owning user
- Sensitive data in corrections is not logged
- All data is encrypted at rest

---

## Support

For issues or questions about the OCR API:
- Check the [main API documentation](../README.md)
- Review the [OCR service implementation](../app/services/ocr_engine.py)
- See [document parser details](../app/services/document_parser.py)
