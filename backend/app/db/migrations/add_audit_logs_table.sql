-- Migration: Add audit_logs table for document operation tracking
-- Date: 2024
-- Description: Creates an immutable audit log table for tracking all document operations

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id INTEGER,
    action VARCHAR(50) NOT NULL,
    result VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common query patterns
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_document_id ON audit_logs(document_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp);
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action);
CREATE INDEX idx_audit_logs_document_timestamp ON audit_logs(document_id, timestamp);

-- Add comment to table
COMMENT ON TABLE audit_logs IS 'Immutable audit log for document operations - no updates or deletes allowed';

-- Add comments to columns
COMMENT ON COLUMN audit_logs.timestamp IS 'When the operation occurred';
COMMENT ON COLUMN audit_logs.user_id IS 'User who performed the operation';
COMMENT ON COLUMN audit_logs.document_id IS 'Document affected by the operation (if applicable)';
COMMENT ON COLUMN audit_logs.action IS 'Type of operation: upload, retrieve, delete, update, preview, share, categorize, version_upload';
COMMENT ON COLUMN audit_logs.result IS 'Operation result: success, failure, partial';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP address of the request';
COMMENT ON COLUMN audit_logs.user_agent IS 'User agent string from the request';
COMMENT ON COLUMN audit_logs.details IS 'Additional context as JSON string';

-- Create a function to prevent updates and deletes on audit_logs
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Audit logs cannot be modified';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Audit logs cannot be deleted';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce immutability
CREATE TRIGGER audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();

-- Grant appropriate permissions
-- GRANT SELECT, INSERT ON audit_logs TO application_user;
-- Note: No UPDATE or DELETE permissions should be granted
