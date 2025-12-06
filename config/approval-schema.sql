-- Add human-in-the-loop approval workflow to incidents table
-- This migration adds fields to support pre-processing approval

-- Create approval status enum type
DO $$ BEGIN
    CREATE TYPE approval_status AS ENUM (
        'pending',      -- Awaiting human approval
        'approved',     -- Approved by human, ready to process
        'rejected',     -- Rejected by human, will not process
        'processing',   -- Currently being processed by agent
        'completed'     -- Agent processing finished
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add approval_status column to incidents table
ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS approval_status approval_status DEFAULT 'pending';

-- Add approved_by and approved_at columns for audit trail
ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Create index on approval_status for efficient querying of pending incidents
CREATE INDEX IF NOT EXISTS incidents_approval_status_idx ON incidents(approval_status);

-- Create composite index for filtering pending high-priority incidents
CREATE INDEX IF NOT EXISTS incidents_pending_priority_idx 
ON incidents(approval_status, created_at DESC) 
WHERE approval_status = 'pending';

-- Update existing incidents to have 'completed' status (they were processed without approval)
UPDATE incidents 
SET approval_status = 'completed' 
WHERE approval_status = 'pending';

-- Create view for pending approvals
CREATE OR REPLACE VIEW pending_approvals AS
SELECT 
    id,
    incident_id,
    form_data,
    classification,
    severity,
    created_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))/60 AS pending_minutes
FROM incidents
WHERE approval_status = 'pending'
ORDER BY created_at ASC;

-- Create view for approval statistics
CREATE OR REPLACE VIEW approval_statistics AS
SELECT 
    approval_status,
    COUNT(*) AS count,
    AVG(EXTRACT(EPOCH FROM (approved_at - created_at))/60) AS avg_approval_time_minutes
FROM incidents
WHERE approval_status IN ('approved', 'rejected', 'completed')
GROUP BY approval_status;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
