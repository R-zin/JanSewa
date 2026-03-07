# Document Expiration and Archival Implementation

## Overview

This document describes the implementation of document expiration detection, archival, and warning generation for the Government Services Assistant. This functionality automatically tracks document expiration dates, generates warnings for expiring documents, and archives documents that have been expired for 90+ days.

## Implementation Details

### 1. Core Components

#### DocumentStorage Service (`app/services/document_storage.py`)

Enhanced with expiration and archival functionality:

**New Class: ExpirationWarning**
- Represents a document expiration warning
- Contains document ID, name, expiration date, and days until expiration
- Provides `to_dict()` method for serialization

**New Methods:**
- `is_document_expired(expiration_date)` - Check if a document is expired
- `get_days_until_expiration(expiration_date)` - Calculate days until expiration
- `should_show_expiration_warning(expiration_date)` - Check if warning should be shown (within 30 days)
- `should_archive_document(expiration_date)` - Check if document should be archived (expired 90+ days)
- `generate_expiration_warning(document_id, document_name, expiration_date)` - Generate warning object
- `get_expiration_warnings(documents)` - Get warnings for a list of documents
- `archive_expired_document(user_id, document_id, s3_key)` - Archive a single document
- `process_expired_documents(documents)` - Process all expired documents for archival
- `get_document_expiration_status(expiration_date)` - Get status: no_expiration, valid, expiring_soon, expired, archived
- `update_document_metadata_with_expiration_status(metadata)` - Update metadata with current status

**Configuration:**
- `expiration_warning_days = 30` - Show warnings for documents expiring within 30 days
- `archive_after_expiration_days = 90` - Archive documents 90 days after expiration

#### ExpirationScheduler Service (`app/services/expiration_scheduler.py`)

Scheduled task service for automated expiration checking:

**Key Features:**
- Runs daily checks (configurable interval)
- Processes all documents for expiration and archival
- Generates warnings for expiring documents
- Provides user-specific expiration checking

**Methods:**
- `check_and_process_expirations(get_all_documents_func)` - Check and process all documents
- `run_scheduled_checks(get_all_documents_func)` - Run scheduled checks in a loop
- `check_user_document_expirations(user_id, user_documents)` - Check specific user's documents
- `stop()` - Stop the scheduler

### 2. Database Changes

#### Document Model (`app/db/models.py`)

Added new field:
- `expiration_status` - VARCHAR(50) field tracking document status
  - Values: `no_expiration`, `valid`, `expiring_soon`, `expired`, `archived`

#### Migration (`app/db/migrations/add_expiration_status.sql`)

SQL migration to add the expiration_status field:
- Adds column with default value
- Creates indexes for efficient queries
- Updates existing records with appropriate status
- Adds column comment for documentation

### 3. Expiration Status Values

| Status | Description |
|--------|-------------|
| `no_expiration` | Document has no expiration date |
| `valid` | Document is valid (expires in 30+ days) |
| `expiring_soon` | Document expires within 30 days |
| `expired` | Document is expired (less than 90 days) |
| `archived` | Document expired 90+ days ago and has been archived |

### 4. Archival Process

When a document should be archived:
1. Document is downloaded from current S3 location
2. Document is uploaded to archive location (path changes from `/documents/` to `/archived/`)
3. Original document is deleted from active storage
4. Database record is updated with `archived` status

### 5. Integration Points

#### Dashboard Integration

The dashboard can use these methods to display:
- Expiration warnings for documents expiring within 30 days
- List of expired documents
- List of expiring soon documents
- Document expiration status badges

Example usage:
```python
from app.services.expiration_scheduler import expiration_scheduler

# Get user's document expiration info
result = await expiration_scheduler.check_user_document_expirations(
    user_id=user_id,
    user_documents=user_documents
)

# result contains:
# - warnings: List of ExpirationWarning objects
# - expired_documents: List of expired documents
# - expiring_soon_documents: List of documents expiring soon
# - total_warnings: Count of warnings
```

#### Document Upload Integration

When uploading a document, the expiration status is automatically set:
```python
metadata = await document_storage.upload_document(
    user_id=user_id,
    file_data=file_data,
    file_name=file_name,
    document_type=document_type,
    category=category,
    expiration_date=expiration_date  # Optional
)
# metadata includes 'expiration_status' field
```

#### Scheduled Task Integration

To run the scheduler in the background:
```python
from app.services.expiration_scheduler import expiration_scheduler

# Define function to get all documents from database
async def get_all_documents():
    # Query database for all documents
    return documents

# Start scheduler (runs in background)
asyncio.create_task(
    expiration_scheduler.run_scheduled_checks(get_all_documents)
)

# Stop scheduler when shutting down
expiration_scheduler.stop()
```

## Testing

Comprehensive unit tests in `tests/test_document_expiration.py`:

### Test Coverage

**DocumentStorage Tests:**
- Expiration detection (expired, future, none)
- Days until expiration calculation
- Warning generation logic
- Archival eligibility checking
- Status determination
- Metadata updates
- Warning filtering

**ExpirationScheduler Tests:**
- User-specific expiration checking
- Warning generation
- Expired and expiring document identification

### Running Tests

```bash
cd backend
python -m pytest tests/test_document_expiration.py -v
```

All 21 tests pass successfully.

## Usage Examples

### Check if Document is Expired

```python
from app.services.document_storage import document_storage
from datetime import datetime

expiration_date = datetime(2024, 1, 1)
is_expired = document_storage.is_document_expired(expiration_date)
```

### Get Expiration Warnings for User

```python
from app.services.expiration_scheduler import expiration_scheduler

user_documents = [
    {
        "id": 1,
        "file_name": "passport.pdf",
        "expiration_date": datetime(2024, 12, 31)
    },
    # ... more documents
]

result = await expiration_scheduler.check_user_document_expirations(
    user_id=123,
    user_documents=user_documents
)

for warning in result["warnings"]:
    print(f"Document {warning['document_name']} expires in {warning['days_until_expiration']} days")
```

### Process Expired Documents for Archival

```python
from app.services.document_storage import document_storage

all_documents = await get_all_documents_from_db()
result = await document_storage.process_expired_documents(all_documents)

print(f"Archived: {result['archived_count']}")
print(f"Failed: {result['failed_count']}")
```

### Get Document Status

```python
from app.services.document_storage import document_storage

status = document_storage.get_document_expiration_status(expiration_date)
# Returns: 'no_expiration', 'valid', 'expiring_soon', 'expired', or 'archived'
```

## Configuration

Key configuration values in `DocumentStorage`:

```python
self.expiration_warning_days = 30  # Warn when expires within 30 days
self.archive_after_expiration_days = 90  # Archive 90 days after expiration
```

Scheduler configuration in `ExpirationScheduler`:

```python
self.check_interval_hours = 24  # Check daily
```

## Future Enhancements

Potential improvements for future iterations:

1. **Email Notifications**: Send email alerts for expiring documents
2. **Configurable Thresholds**: Allow users to set custom warning periods
3. **Bulk Operations**: Batch archival for better performance
4. **Archive Retrieval**: Allow users to retrieve archived documents
5. **Expiration Reminders**: Multiple reminder notifications (30, 14, 7 days)
6. **Auto-Renewal Suggestions**: Suggest renewal processes for expiring documents
7. **Analytics**: Track expiration patterns and document lifecycle metrics

## Requirement Mapping

This implementation satisfies **Requirement 15.12**:

> "WHEN a Stored_Document has an expiration date, THE Document_Storage SHALL automatically archive expired documents after 90 days"

Additional features implemented:
- Expiration detection logic
- Archival process for expired documents
- Expiration warning generation (30-day threshold)
- Scheduled task for checking expirations
- Document metadata tracking for expiration status

## Notes

- The implementation uses UTC timestamps for all date comparisons
- Archived documents are moved to a separate S3 path but remain encrypted
- The scheduler runs asynchronously and can be started/stopped independently
- All expiration logic is timezone-aware and handles edge cases (null dates, past dates)
- Tests include timing tolerance to handle execution delays
