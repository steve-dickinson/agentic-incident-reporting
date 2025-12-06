-- Enhanced logging schema for agent execution tracking
-- Run this after init-db.sql

-- Create execution logs table for detailed agent step tracking
CREATE TABLE IF NOT EXISTS execution_logs (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_order INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'started', 'completed', 'failed'
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
);

-- Create index for execution log queries
CREATE INDEX IF NOT EXISTS execution_logs_incident_id_idx ON execution_logs(incident_id);
CREATE INDEX IF NOT EXISTS execution_logs_step_name_idx ON execution_logs(step_name);
CREATE INDEX IF NOT EXISTS execution_logs_status_idx ON execution_logs(status);
CREATE INDEX IF NOT EXISTS execution_logs_created_at_idx ON execution_logs(created_at DESC);

-- Create metrics table for dashboard statistics
CREATE TABLE IF NOT EXISTS incident_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_incidents INTEGER DEFAULT 0,
    p1_critical INTEGER DEFAULT 0,
    p2_high INTEGER DEFAULT 0,
    p3_medium INTEGER DEFAULT 0,
    p4_low INTEGER DEFAULT 0,
    water_pollution INTEGER DEFAULT 0,
    air_pollution INTEGER DEFAULT 0,
    illegal_dumping INTEGER DEFAULT 0,
    noise_pollution INTEGER DEFAULT 0,
    other_incidents INTEGER DEFAULT 0,
    avg_processing_time_ms INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for metrics queries
CREATE INDEX IF NOT EXISTS incident_metrics_date_idx ON incident_metrics(date DESC);

-- Create trigger for metrics updated_at
CREATE TRIGGER update_metrics_updated_at BEFORE UPDATE ON incident_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for dashboard summary
CREATE OR REPLACE VIEW dashboard_summary AS
SELECT 
    COUNT(*) as total_incidents,
    COUNT(CASE WHEN classification->>'priority' = 'P1' THEN 1 END) as p1_incidents,
    COUNT(CASE WHEN classification->>'priority' = 'P2' THEN 1 END) as p2_incidents,
    COUNT(CASE WHEN classification->>'priority' = 'P3' THEN 1 END) as p3_incidents,
    COUNT(CASE WHEN classification->>'priority' = 'P4' THEN 1 END) as p4_incidents,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000)::INTEGER as avg_processing_ms
FROM incidents
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';

-- Create view for recent incidents with execution details
CREATE OR REPLACE VIEW recent_incidents_detail AS
SELECT 
    i.incident_id,
    i.form_data->>'incident_type' as incident_type,
    i.form_data->>'location' as location,
    i.classification->>'severity' as severity,
    i.classification->>'priority' as priority,
    i.status,
    i.created_at,
    i.updated_at,
    EXTRACT(EPOCH FROM (i.updated_at - i.created_at)) * 1000 as processing_time_ms,
    (
        SELECT COUNT(*) 
        FROM execution_logs el 
        WHERE el.incident_id = i.incident_id AND el.status = 'completed'
    ) as completed_steps,
    (
        SELECT COUNT(*) 
        FROM execution_logs el 
        WHERE el.incident_id = i.incident_id AND el.status = 'failed'
    ) as failed_steps
FROM incidents i
ORDER BY i.created_at DESC
LIMIT 100;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO postgres;
