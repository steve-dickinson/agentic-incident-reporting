"""Structured logging for agent execution tracking."""

import json
import logging
from typing import Any

import asyncpg

from app.models.config import settings

logger = logging.getLogger(__name__)


class AgentLogger:
    """Tracks agent execution steps and metrics in PostgreSQL."""
    
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
    
    async def init_pool(self):
        """Initialize database connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=2,
                max_size=10
            )
    
    async def close_pool(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def log_step(
        self,
        incident_id: str,
        step_name: str,
        step_order: int,
        status: str,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None
    ):
        """Log an agent execution step."""
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO execution_logs 
                    (incident_id, step_name, step_order, status, input_data, output_data, error_message, duration_ms)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8)
                """, incident_id, step_name, step_order, status, 
                json.dumps(input_data) if input_data else None, 
                json.dumps(output_data) if output_data else None, 
                error_message, duration_ms)
                
                logger.info(f"Logged step: {incident_id} - {step_name} - {status}")
        
        except Exception as e:
            logger.error(f"Failed to log step: {e}")
    
    async def update_incident_status(
        self,
        incident_id: str,
        status: str,
        agent_actions: dict[str, Any] | None = None
    ):
        """Update incident status in database."""
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE incidents 
                    SET status = $1, agent_actions = $2::jsonb, updated_at = NOW()
                    WHERE incident_id = $3
                """, status, json.dumps(agent_actions) if agent_actions else None, incident_id)
                
                logger.info(f"Updated incident {incident_id} status to {status}")
        
        except Exception as e:
            logger.error(f"Failed to update incident status: {e}")
    
    async def log_incident_creation(
        self,
        incident_id: str,
        form_data: dict[str, Any],
        classification: dict[str, Any] | None = None,
        severity: str | None = None,
        approval_status: str = "approved"
    ):
        """Log initial incident creation.
        
        Args:
            incident_id: Unique incident identifier
            form_data: Original form submission data
            classification: Classification results from agent
            severity: Severity level (critical, high, medium, low)
            approval_status: Approval workflow status (pending, approved, rejected, processing, completed)
        """
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO incidents 
                    (incident_id, form_data, classification, severity, status, approval_status)
                    VALUES ($1, $2::jsonb, $3::jsonb, $4, 'processing', $5::approval_status)
                    ON CONFLICT (incident_id) DO UPDATE
                    SET form_data = $2::jsonb, 
                        classification = $3::jsonb, 
                        severity = $4, 
                        status = 'processing',
                        approval_status = $5::approval_status
                """, incident_id, 
                json.dumps(form_data), 
                json.dumps(classification) if classification else None, 
                severity,
                approval_status)
                
                logger.info(f"Logged incident creation: {incident_id} with approval_status={approval_status}")
        
        except Exception as e:
            logger.error(f"Failed to log incident: {e}")
    
    async def get_incident_logs(self, incident_id: str) -> list[dict[str, Any]]:
        """Retrieve all execution logs for an incident."""
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id, incident_id, step_name, step_order, status,
                        input_data, output_data, error_message, duration_ms,
                        created_at
                    FROM execution_logs
                    WHERE incident_id = $1
                    ORDER BY step_order ASC, created_at ASC
                """, incident_id)
                
                return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to retrieve logs: {e}")
            return []
    
    async def get_dashboard_summary(self) -> dict[str, Any]:
        """Get summary statistics for dashboard."""
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM dashboard_summary
                """)
                
                if row:
                    return dict(row)
                return {}
        
        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            return {}
    
    async def get_recent_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent incidents with execution details."""
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM recent_incidents_detail
                    LIMIT $1
                """, limit)
                
                return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get recent incidents: {e}")
            return []
    
    async def get_hourly_metrics(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get hourly incident metrics for charts."""
        if not self.pool:
            await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        DATE_TRUNC('hour', created_at) as hour,
                        COUNT(*) as total,
                        COUNT(CASE WHEN classification->>'priority' = 'P1' THEN 1 END) as p1,
                        COUNT(CASE WHEN classification->>'priority' = 'P2' THEN 1 END) as p2,
                        COUNT(CASE WHEN classification->>'priority' = 'P3' THEN 1 END) as p3,
                        COUNT(CASE WHEN classification->>'priority' = 'P4' THEN 1 END) as p4,
                        AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000)::INTEGER as avg_time_ms
                    FROM incidents
                    WHERE created_at >= NOW() - INTERVAL '$1 hours'
                    GROUP BY hour
                    ORDER BY hour DESC
                """, hours)
                
                return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get hourly metrics: {e}")
            return []


# Global instance
agent_logger = AgentLogger()
