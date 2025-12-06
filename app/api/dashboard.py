"""Dashboard API endpoints for monitoring and analytics."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.logging import agent_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary() -> dict[str, Any]:
    """Get summary statistics for the dashboard."""
    try:
        summary = await agent_logger.get_dashboard_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents")
async def get_recent_incidents(limit: int = 50) -> list[dict[str, Any]]:
    """Get recent incidents with execution details."""
    try:
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
        
        incidents = await agent_logger.get_recent_incidents(limit=limit)
        return incidents
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}/logs")
async def get_incident_logs(incident_id: str) -> list[dict[str, Any]]:
    """Get execution logs for a specific incident."""
    try:
        logs = await agent_logger.get_incident_logs(incident_id)
        
        if not logs:
            raise HTTPException(status_code=404, detail=f"No logs found for incident {incident_id}")
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get incident logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_hourly_metrics(hours: int = 24) -> list[dict[str, Any]]:
    """Get hourly incident metrics for charts."""
    try:
        if hours < 1 or hours > 168:  # Max 7 days
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
        
        metrics = await agent_logger.get_hourly_metrics(hours=hours)
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hourly metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
