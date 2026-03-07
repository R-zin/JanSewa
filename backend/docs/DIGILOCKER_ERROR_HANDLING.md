# DigiLocker Error Handling Implementation

## Overview

This document describes the comprehensive error handling implementation for DigiLocker integration, including rate limiting, exponential backoff, partial import handling, and user-friendly error messages.

## Requirements Addressed

- **19.27**: Error logging with specific failure reasons and retry capability
- **19.28**: Service unavailability error messages with retry timing suggestions
- **19.42**: Authentication failure error handling with clear messages and retry instructions
- **19.43**: Graceful handling of DigiLocker API rate limits with request queuing
- **19.44**: Rate limit notifications with estimated retry time
- **19.45**: Partial import support where some documents succeed and others fail

## Architecture

### Error Types

The implementation defines specific error types for different failure scenarios:

1. **AuthenticationError**: OAuth authentication failures, invalid credentials
2. **RateLimitError**: API rate limit exceeded
3. **ServiceUnavailableError**: DigiLocker service temporarily down
4. **DocumentNotFoundError**: Requested document doesn't exist
5. **InvalidTokenError**: Expired or invalid access token

### Retry Strategy

**Exponential Backoff Configuration**:
- Initial delay: 1 second
- Maximum delay: 60 seconds
- Exponential base: 2.0
- Jitter: 10% random variation
- Maximum attempts: 3

**Retry Behavior**:
- Rate limit errors: Always respect `retry_after` from server
- Service unavailable: Use exponential backoff
- Authentication errors: No retry (requires user intervention)
- Other errors: Exponential backoff with jitter

### Rate Limiting

**Client-Side Rate Limiter**:
- Default: 10 requests per 60 seconds
- Prevents exceeding API limits
- Queues requests when limit reached
- Automatic throttling

## Components

### 1. Error Classes (`digilocker_errors.py`)

Custom exception hierarchy for DigiLocker errors:

```python
DigiLockerError (base)
├── AuthenticationError
├── RateLimitError
├── ServiceUnavailableError
├── DocumentNotFoundError
└── InvalidTokenError
```

Each error includes:
- Human-readable message
- Error type enum
- Optional retry_after value
- Additional details dictionary

### 2. Retry Logic (`digilocker_retry.py`)

**RetryStrategy**: Implements exponential backoff with configurable parameters

**RateLimiter**: Client-side rate limiting to prevent API abuse

**@with_retry decorator**: Easy-to-use decorator for adding retry logic to functions

### 3. Enhanced Client (`digilocker_client_enhanced.py`)

**EnhancedDigiLockerClient** extends the base client with:

- `list_documents_with_retry()`: List documents with automatic retry
- `import_document_with_retry()`: Import single document with error handling
- `bulk_import_with_partial_handling()`: Import multiple documents, continue on errors
- `sync_documents_with_error_handling()`: Comprehensive sync with error recovery
- `get_user_friendly_error_message()`: Convert technical errors to user-friendly messages

### 4. API Endpoints (`digilocker.py`)

Updated endpoints with proper HTTP status codes:

- `401 Unauthorized`: Authentication failures
- `429 Too Many Requests`: Rate limit exceeded (includes retry_after)
- `503 Service Unavailable`: DigiLocker service down
- `207 Multi-Status`: Partial success in bulk operations
- `500 Internal Server Error`: Other errors

## Usage Examples

### Basic Document Import with Retry

```python
from backend.app.services.digilocker_client_enhanced import EnhancedDigiLockerClient
from backend.app.services.digilocker_retry import RetryConfig

# Configure retry behavior
retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=60.0
)

# Initialize client
client = EnhancedDigiLockerClient(
    authenticator=authenticator,
    retry_config=retry_config
)

# Import document (automatically retries on failure)
result = await client.import_document_with_retry(user_id, doc_id)

if result.success:
    print(f"Document imported: {result.data}")
else:
    print(f"Import failed: {result.error.message}")
```

### Bulk Import with Partial Success Handling

```python
# Import multiple documents
doc_ids = ["doc1", "doc2", "doc3", "doc4"]

results = await client.bulk_import_with_partial_handling(
    user_id=user_id,
    doc_ids=doc_ids,
    continue_on_error=True  # Continue even if some fail
)

print(f"Total: {results['total']}")
print(f"Successful: {len(results['successful'])}")
print(f"Failed: {len(results['failed'])}")

# Check if partial success
if results['partial_success']:
    print("Some documents imported successfully, others failed")
    
    # Process successful imports
    for success in results['successful']:
        print(f"✓ {success['doc_id']}")
    
    # Handle failures
    for failure in results['failed']:
        print(f"✗ {failure['doc_id']}: {failure['error']['message']}")
```

### Handling Specific Errors

```python
from backend.app.services.digilocker_errors import (
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError
)

try:
    documents = await client.list_documents_with_retry(user_id)
    
except AuthenticationError as e:
    # User needs to reconnect
    print("Please reconnect your DigiLocker account")
    
except RateLimitError as e:
    # Wait before retrying
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
    
except ServiceUnavailableError as e:
    # Service is down
    print("DigiLocker is temporarily unavailable. Try again later")
```

## Error Messages

### User-Friendly Messages

The implementation provides user-friendly error messages for each error type:

**Authentication Failed**:
> "We couldn't connect to your DigiLocker account. Please check your credentials and try reconnecting."

**Rate Limit Exceeded**:
> "You've made too many requests to DigiLocker. Please wait 60 seconds before trying again."

**Service Unavailable**:
> "DigiLocker service is temporarily unavailable. This is usually temporary - please try again in a few minutes."

**Document Not Found**:
> "The requested document could not be found in your DigiLocker account. It may have been removed or you may not have access to it."

**Invalid Token**:
> "Your DigiLocker session has expired. Please reconnect your account to continue."

## API Response Examples

### Successful Import

```json
{
  "doc_id": "dl_aadhaar_001",
  "doc_name": "Aadhaar Card",
  "category": "aadhaar",
  "imported_at": "2024-01-15T10:30:00Z",
  "source": "digilocker"
}
```

### Rate Limit Error (429)

```json
{
  "error": "rate_limit_exceeded",
  "message": "You've made too many requests to DigiLocker. Please wait 60 seconds before trying again.",
  "retry_after": 60
}
```

### Partial Import Success (207)

```json
{
  "status": "partial",
  "total": 4,
  "successful_count": 3,
  "failed_count": 1,
  "successful": [
    {"doc_id": "doc1", "success": true, "data": {...}},
    {"doc_id": "doc2", "success": true, "data": {...}},
    {"doc_id": "doc3", "success": true, "data": {...}}
  ],
  "failed": [
    {
      "doc_id": "doc4",
      "success": false,
      "error": {
        "error": "document_not_found",
        "message": "Document 'doc4' not found in DigiLocker"
      }
    }
  ],
  "message": "Successfully imported 3 of 4 documents. 1 failed."
}
```

### Service Unavailable (503)

```json
{
  "error": "service_unavailable",
  "message": "DigiLocker service is temporarily unavailable. This is usually temporary - please try again in a few minutes."
}
```

## Logging

All operations are logged with appropriate levels:

- **INFO**: Successful operations, retry successes
- **WARNING**: Rate limits, retries in progress
- **ERROR**: Failed operations, authentication failures

Example log output:

```
INFO: Starting bulk import of 5 documents for user user123
INFO: Successfully imported document dl_aadhaar_001
WARNING: Rate limit exceeded. Retrying after 30.00s (attempt 2/3)
INFO: Retry succeeded on attempt 2
ERROR: Failed to import document dl_pan_002: Document not found
INFO: Bulk import completed: 4 successful, 1 failed
```

## Error Statistics

The client tracks error statistics for monitoring:

```python
stats = client.get_error_statistics()

# Returns:
{
  "total_errors": 15,
  "by_type": {
    "rate_limit_exceeded": 8,
    "service_unavailable": 4,
    "document_not_found": 2,
    "authentication_failed": 1
  }
}
```

## Configuration

### Retry Configuration

```python
RetryConfig(
    max_attempts=3,        # Maximum retry attempts
    initial_delay=1.0,     # Initial delay in seconds
    max_delay=60.0,        # Maximum delay in seconds
    exponential_base=2.0,  # Exponential backoff base
    jitter=True            # Add random jitter
)
```

### Rate Limit Configuration

```python
# (max_requests, time_window_seconds)
rate_limit_config = (10, 60.0)  # 10 requests per minute
```

## Testing

The error handling can be tested by:

1. Simulating rate limit responses
2. Temporarily disconnecting network
3. Using invalid credentials
4. Requesting non-existent documents

## Best Practices

1. **Always use retry methods**: Use `*_with_retry()` methods instead of base methods
2. **Handle partial imports**: Check for `partial_success` in bulk operations
3. **Respect retry_after**: Never ignore rate limit retry times
4. **Log errors**: All errors are automatically logged
5. **User feedback**: Use `get_user_friendly_error_message()` for UI display
6. **Monitor statistics**: Regularly check error statistics for patterns

## Future Enhancements

Potential improvements:

1. Circuit breaker pattern for repeated failures
2. Adaptive rate limiting based on server responses
3. Retry queue persistence across restarts
4. Detailed error analytics dashboard
5. Automatic credential refresh on token expiry
