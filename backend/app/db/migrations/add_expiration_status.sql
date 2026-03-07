-- Migration: Add expiration_status field to documents table
-- Date: 2024
-- Description: Adds expiration_status column to track document expiration state

-- Add expiration_status column
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS expiration_status VARCHAR(50) DEFAULT 'no_expiration';

-- Create index for efficient expiration queries
CREATE INDEX IF NOT EXISTS idx_documents_expiration_status 
ON documents(expiration_status);

-- Create index for expiration date queries
CREATE INDEX IF NOT EXISTS idx_documents_expiration_date 
ON documents(expiration_date) 
WHERE expiration_date IS NOT NULL;

-- Update existing records to set appropriate expiration status
UPDATE documents
SET expiration_status = CASE
    WHEN expiration_date IS NULL THEN 'no_expiration'
    WHEN expiration_date < NOW() THEN 'expired'
    WHEN expiration_date < NOW() + INTERVAL '30 days' THEN 'expiring_soon'
    ELSE 'valid'
END
WHERE expiration_status = 'no_expiration';

-- Add comment to column
COMMENT ON COLUMN documents.expiration_status IS 'Document expiration status: no_expiration, valid, expiring_soon, expired, archived';
