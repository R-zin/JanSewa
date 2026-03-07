# Audit Logger Service

## Overview

The Audit Logger service provides comprehensive tracking of all document operations for security and compliance purposes. It creates immutable audit logs stored in PostgreSQL that cannot be modified or deleted.

## Features

- **Immutable Logs**: Audit logs are append-only and protected by database triggers
- **Comprehensive Tracking**: Logs all document operations (upload, retrieve, delete, update, preview, share)
- **User Context**: Captures IP address and user agent for each operation
- **Flexible Querying**: Supports filtering by user, document, action type, date range, and result
- **Pagination**: Efficient retrieval of large audit log datasets
- **Security**: Logs are stored securely in PostgreSQL with proper indexing

## Architecture

### Components

1. **AuditLogger Service** (`audit_logger.py`)
   - Core service for creating and querying audit logs
   - Provides methods for logging operations and retrieving logs with filters

2. **Database Model** (`AuditLogEntry`)
   - PostgreSQL table with immutability enforced by triggers
   - Indexed for efficient querying

3. **Integration Layer** (`document_storage_with_audit.py`)
   - Wrapper around DocumentStorage that automatically logs all operations
   - Ensures no operation goes unlogged

4. **API Endpoints** (`api/v1/endpoints/audit.py`)
   - REST API for accessing audit logs
   - Supports various filtering and pagination options

## Database Schema

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    document_id INTEGER,
    action VARCHAR(50) NOT NULL,
    result VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT
);
```

### Indexes

- `idx_audit_logs_timestamp`: For time-based queries
- `idx_audit_logs_user_id`: For user-specific queries
- `idx_audit_logs_document_id`: For document-specific queries
- `idx_audit_logs_action`: For action-type queries
- `idx_audit_logs_user_timestamp`: Composite index for user + time queries
- `idx_audit_logs_user_action`: Composite index for user + action queries
- `idx_audit_logs_document_timestamp`: Composite index for document + time queries

### Immutability

The table is protected by a PostgreSQL trigger that prevents any UPDATE or DELETE operations:

```sql
CREATE TRIGGER audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();
```

## Usage

### Basic Logging

```python
from app.services.audit_logger import create_audit_logger, AuditAction
from app.db.base import get_db

# Create audit logger
db = next(get_db())
audit_logger = create_audit_logger(db)

# Log a document upload
await audit_logger.log_operation(
    user_id=123,
    action=AuditAction.UPLOAD,
    result="success",
    document_id=456,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    details={
        "file_name": "passport.pdf",
        "file_size": 2048000,
        "category": "identity"
    }
)
```

### Querying Logs

```python
from app.services.audit_logger import AuditLogFilters

# Get all logs for a user
logs = await audit_logger.get_user_logs(user_id=123, limit=50)

# Get logs for a specific document
logs = await audit_logger.get_document_logs(document_id=456)

# Get logs by action type
logs = await audit_logger.get_logs_by_action(
    user_id=123,
    action=AuditAction.RETRIEVE
)

# Get logs within a date range
from datetime import datetime, timedelta
start = datetime.utcnow() - timedelta(days=7)
end = datetime.utcnow()
logs = await audit_logger.get_logs_by_date_range(
    user_id=123,
    start_date=start,
    end_date=end
)

# Advanced filtering
filters = AuditLogFilters(
    user_id=123,
    action=AuditAction.UPLOAD,
    result="success",
    start_date=start,
    end_date=end,
    limit=100,
    offset=0
)
logs = await audit_logger.get_logs(filters)

# Count logs
count = await audit_logger.count_logs(filters)
```

### Integration with Document Storage

```python
from app.services.document_storage import document_storage
from app.services.document_storage_with_audit import create_document_storage_with_audit

# Create audited storage service
audited_storage = create_document_storage_with_audit(document_storage, db)

# All operations are automatically logged
metadata = await audited_storage.upload_document(
    user_id=123,
    file_data=file_bytes,
    file_name="passport.pdf",
    document_type="identity",
    category=DocumentCategory.IDENTITY,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)
```

## API Endpoints

### Get Audit Logs

```http
GET /api/v1/audit/logs?user_id=123&action=upload&limit=50
```

Query Parameters:
- `user_id` (optional): Filter by user ID
- `document_id` (optional): Filter by document ID
- `action` (optional): Filter by action type (upload, retrieve, delete, update, preview, share)
- `start_date` (optional): Start date for filtering (ISO 8601)
- `end_date` (optional): End date for filtering (ISO 8601)
- `result` (optional): Filter by result (success, failure, partial)
- `limit` (default: 100, max: 1000): Maximum entries to return
- `offset` (default: 0): Number of entries to skip

### Get User Logs

```http
GET /api/v1/audit/logs/user/123?limit=50&offset=0
```

### Get Document Logs

```http
GET /api/v1/audit/logs/document/456?limit=50&offset=0
```

### Get Logs by Action

```http
GET /api/v1/audit/logs/action/upload?user_id=123&limit=50
```

### Count Logs

```http
GET /api/v1/audit/logs/count?user_id=123&action=upload
```

### Get Logs by Date Range

```http
GET /api/v1/audit/logs/date-range?user_id=123&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z
```

## Action Types

The following action types are tracked:

- `UPLOAD`: Document upload operation
- `RETRIEVE`: Document retrieval/download operation
- `DELETE`: Document deletion operation
- `UPDATE`: Document metadata update operation
- `PREVIEW`: Document preview operation
- `SHARE`: Document sharing with automation agent
- `CATEGORIZE`: Document categorization operation
- `VERSION_UPLOAD`: New version upload operation

## Result Types

Operations can have the following results:

- `success`: Operation completed successfully
- `failure`: Operation failed
- `partial`: Operation partially completed (e.g., bulk operation with some failures)

## Security Considerations

1. **Immutability**: Audit logs cannot be modified or deleted, ensuring integrity
2. **Access Control**: API endpoints should be protected with authentication and authorization
3. **Data Retention**: Consider implementing a data retention policy for old logs
4. **Privacy**: Sensitive information should not be stored in the `details` field
5. **Performance**: Indexes ensure efficient querying even with large datasets

## Compliance

The audit logger helps meet compliance requirements for:

- **GDPR**: Tracking data access and modifications
- **HIPAA**: Audit trails for protected health information
- **SOC 2**: Security monitoring and incident response
- **ISO 27001**: Information security management

## Testing

Run the test suite:

```bash
pytest backend/tests/test_audit_logger.py -v
```

## Migration

To set up the audit logs table:

```bash
psql -U postgres -d govt_services -f backend/app/db/migrations/add_audit_logs_table.sql
```

## Performance Considerations

1. **Indexing**: Multiple indexes ensure fast queries for common patterns
2. **Pagination**: Always use limit/offset to avoid loading large datasets
3. **Archiving**: Consider archiving old logs to a separate table or storage
4. **Async Operations**: All operations are async for better performance

## Future Enhancements

- [ ] Export audit logs to external SIEM systems
- [ ] Real-time alerting for suspicious activities
- [ ] Audit log analytics and reporting dashboard
- [ ] Automated compliance report generation
- [ ] Integration with log aggregation services (ELK, Splunk)
