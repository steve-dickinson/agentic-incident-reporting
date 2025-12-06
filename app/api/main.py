"""FastAPI application for environmental incident reporting."""

import json
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agents.incident_agent import incident_agent
from app.agents.hitl_incident_agent import hitl_incident_agent
from app.api.dashboard import router as dashboard_router
from app.models.logging import agent_logger
from app.tools.classification import _determine_severity, PRIORITY_MAP
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.database.neo4j_pool import get_neo4j_pool, close_neo4j_pool
from app.exceptions import IncidentProcessingError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Defra AI Agent API",
    description="AI-powered environmental incident reporting system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware (100 requests/minute, 2000/hour)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,
    requests_per_hour=2000
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard_router)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    try:
        # Initialize Neo4j connection pool
        neo4j_pool = get_neo4j_pool()
        logger.info("Neo4j connection pool initialized")
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections on shutdown."""
    close_neo4j_pool()
    logger.info("Application shutdown complete")


# Exception handlers
@app.exception_handler(IncidentProcessingError)
async def incident_error_handler(request: Request, exc: IncidentProcessingError):
    """Handle all incident processing errors with structured response."""
    logger.error(f"Incident processing error: {exc.message}", extra=exc.details)
    return JSONResponse(
        status_code=500,
        content=exc.to_dict()
    )


class IncidentSubmission(BaseModel):
    """Model for incident form submission"""
    incident_type: str = Field(..., description="Type of environmental incident")
    location: str = Field(..., description="Location description")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    description: str = Field(..., description="Detailed description of incident")
    reporter_name: str | None = Field(None, description="Name of reporter")
    reporter_email: str | None = Field(None, description="Email of reporter")
    reporter_phone: str | None = Field(None, description="Phone of reporter")
    urgency: str | None = Field("medium", description="Urgency level: low, medium, high")
    images: list[str] | None = Field(None, description="URLs or base64 encoded images")
    additional_info: dict[str, Any] | None = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "incident_type": "water_pollution",
                "location": "River Thames near Reading",
                "latitude": 51.4543,
                "longitude": -0.9781,
                "description": "Oil spill observed in river",
                "reporter_email": "citizen@example.com",
                "urgency": "high"
            }
        }


class IncidentResponse(BaseModel):
    """Model for API response"""
    success: bool
    incident_id: str
    message: str
    severity: str | None = None
    priority: str | None = None
    classification: dict[str, Any] | None = None
    actions: list[str] | None = None
    spatial_context: dict[str, Any] | None = None
    guidance: str | None = None
    notifications: dict[str, Any] | None = None
    errors: list[str] | None = None
    timestamp: str


def quick_classify_priority(incident: IncidentSubmission) -> tuple[str, str]:
    """Quickly determine severity and priority without full agent processing.
    
    Returns:
        tuple[str, str]: (severity, priority)
    """
    severity = _determine_severity(
        incident_type=incident.incident_type,
        description=incident.description,
        urgency=incident.urgency or "medium"
    )
    priority = PRIORITY_MAP.get(severity, "P3 - Standard Response (within 24 hours)")
    return severity, priority


def requires_approval(priority: str) -> bool:
    """Determine if incident requires human approval before processing.
    
    P1/P2 incidents require approval, P3/P4 are auto-approved.
    """
    return priority.startswith("P1") or priority.startswith("P2")


@app.get("/")
async def root():
    return {
        "service": "Defra AI Agent API",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "submit": "/api/v1/incidents/submit"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "defra-ai-agent"
    }


@app.post("/api/v1/incidents/submit", response_model=IncidentResponse)
async def submit_incident(incident: IncidentSubmission):
    """Submit incident using LangGraph HITL agent with interrupt-based approval.
    
    The agent begins processing immediately, classifies the incident, and if it's
    high-priority (P1/P2), the workflow pauses (via LangGraph interrupt) awaiting
    human review. Low-priority incidents auto-approve and complete processing.
    """
    try:
        logger.info(f"Received incident submission: {incident.incident_type}")
        
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        start_time = time.time()
        form_data = incident.model_dump()
        
        # Log incident creation
        await agent_logger.log_incident_creation(
            incident_id=incident_id,
            form_data=form_data,
            classification=None,
            severity=None,
            approval_status="processing"
        )
        
        # Log start of processing
        await agent_logger.log_step(
            incident_id=incident_id,
            step_name="initialize",
            step_order=0,
            status="started",
            input_data=form_data
        )
        
        # Process through HITL agent (may pause at interrupt point)
        result = hitl_incident_agent.process_incident(
            incident_id=incident_id,
            incident_type=incident.incident_type,
            description=incident.description,
            location=incident.location,
            latitude=incident.latitude,
            longitude=incident.longitude,
            reporter_email=incident.reporter_email,
            urgency=incident.urgency or "medium"
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Check if workflow is awaiting human input
        if result.get("awaiting_human"):
            logger.info(
                f"Incident {incident_id} paused at interrupt, awaiting human review "
                f"(severity={result['severity']}, priority={result['priority']})"
            )
            
            # Update incident status to pending
            await agent_logger.log_step(
                incident_id=incident_id,
                step_name="human_review_required",
                step_order=2,
                status="interrupted",
                output_data=result,
                duration_ms=duration_ms
            )
            
            # Update approval status
            async with agent_logger.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE incidents
                    SET approval_status = 'pending',
                        classification = $1::jsonb,
                        severity = $2
                    WHERE incident_id = $3
                """, json.dumps(result["classification"]), result["severity"], incident_id)
            
            return IncidentResponse(
                success=True,
                incident_id=incident_id,
                message=(
                    f"Incident {incident_id} classified and paused for human review. "
                    f"LangGraph workflow interrupted at decision point. "
                    f"Severity: {result['severity']}, Priority: {result['priority']}. "
                    f"Use the Approval Queue to review and continue processing."
                ),
                severity=result.get("severity"),
                priority=result.get("priority"),
                classification=result.get("classification"),
                actions=["Workflow paused - awaiting human review at LangGraph interrupt"],
                errors=[],
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Low priority - auto-approved and fully processed
        logger.info(f"Incident {incident_id} auto-approved and completed")
        
        # Log completion
        await agent_logger.log_step(
            incident_id=incident_id,
            step_name="complete",
            step_order=99,
            status="completed",
            output_data=result,
            duration_ms=duration_ms
        )
        
        # Update incident with final classification
        async with agent_logger.pool.acquire() as conn:
            await conn.execute("""
                UPDATE incidents
                SET approval_status = 'completed',
                    classification = $1::jsonb,
                    severity = $2
                WHERE incident_id = $3
            """, json.dumps(result.get("classification")), result.get("severity"), incident_id)
        
        message = (
            f"Incident {incident_id} received and processed. "
            f"Classified as {result['severity']} severity. {result['priority']}"
        )
        
        return IncidentResponse(
            success=result["success"],
            incident_id=incident_id,
            message=message,
            severity=result.get("severity"),
            priority=result.get("priority"),
            classification=result.get("classification"),
            actions=result.get("actions"),
            spatial_context=result.get("spatial_context"),
            guidance=result.get("guidance"),
            notifications=result.get("notifications"),
            errors=result.get("errors", []),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing incident: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/incidents/pending-approval")
async def list_pending_approvals():
    """List all incidents awaiting human approval (paused at LangGraph interrupt)."""
    try:
        if not agent_logger.pool:
            await agent_logger.init_pool()
        
        async with agent_logger.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    incident_id,
                    form_data,
                    classification,
                    severity,
                    created_at,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))/60 AS pending_minutes
                FROM incidents
                WHERE approval_status = 'pending'
                ORDER BY created_at ASC
            """)
            
            pending = []
            for row in rows:
                pending.append({
                    "incident_id": row["incident_id"],
                    "form_data": row["form_data"],
                    "classification": row["classification"],
                    "severity": row["severity"],
                    "created_at": row["created_at"].isoformat(),
                    "pending_minutes": float(row["pending_minutes"])
                })
            
            return {
                "success": True,
                "count": len(pending),
                "incidents": pending,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    return {
        "incident_id": incident_id,
        "status": "pending",
        "message": "Incident retrieval not yet implemented"
    }


class ApprovalRequest(BaseModel):
    """Model for approval/rejection requests."""
    approved_by: str = Field(..., description="Name or ID of person approving/rejecting")
    reason: str | None = Field(None, description="Reason for rejection (required if rejecting)")


@app.post("/api/v1/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str, approval: ApprovalRequest):
    """Approve a pending incident and resume LangGraph workflow from interrupt.
    
    This demonstrates LangGraph's HITL strength: the workflow was paused at an
    interrupt point, state was persisted in the checkpointer, and now we resume
    execution with human approval incorporated into the state.
    """
    try:
        if not agent_logger.pool:
            await agent_logger.init_pool()
        
        # Check if incident exists and is pending
        async with agent_logger.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT approval_status, form_data, classification, severity
                FROM incidents
                WHERE incident_id = $1
            """, incident_id)
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
            
            if row["approval_status"] != "pending":
                raise HTTPException(
                    status_code=400, 
                    detail=f"Incident {incident_id} is not at interrupt point (status: {row['approval_status']})"
                )
            
            # Update to approved
            await conn.execute("""
                UPDATE incidents
                SET approval_status = 'processing',
                    approved_by = $1,
                    approved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE incident_id = $2
            """, approval.approved_by, incident_id)
        
        logger.info(
            f"Incident {incident_id} approved by {approval.approved_by}, "
            f"resuming LangGraph workflow from checkpoint"
        )
        
        # Log approval
        await agent_logger.log_step(
            incident_id=incident_id,
            step_name="human_approval",
            step_order=3,
            status="completed",
            input_data={"approved_by": approval.approved_by, "approved": True}
        )
        
        start_time = time.time()
        
        # Continue workflow from checkpoint (LangGraph magic!)
        result = hitl_incident_agent.continue_after_approval(
            incident_id=incident_id,
            approved=True,
            feedback=f"Approved by {approval.approved_by}"
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log completion
        await agent_logger.log_step(
            incident_id=incident_id,
            step_name="complete",
            step_order=99,
            status="completed",
            output_data=result,
            duration_ms=duration_ms
        )
        
        # Update to completed
        async with agent_logger.pool.acquire() as conn:
            await conn.execute("""
                UPDATE incidents
                SET approval_status = 'completed',
                    classification = $1::jsonb,
                    severity = $2
                WHERE incident_id = $3
            """, json.dumps(result.get("classification")), result.get("severity"), incident_id)
        
        return {
            "success": result["success"],
            "incident_id": incident_id,
            "message": f"Incident {incident_id} approved and LangGraph workflow resumed from checkpoint",
            "approved_by": approval.approved_by,
            "workflow_state": "resumed_from_interrupt",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/incidents/{incident_id}/reject")
async def reject_incident(incident_id: str, approval: ApprovalRequest):
    """Reject a pending incident - workflow will not resume."""
    try:
        if not approval.reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        if not agent_logger.pool:
            await agent_logger.init_pool()
        
        async with agent_logger.pool.acquire() as conn:
            # Check if incident exists and is pending
            row = await conn.fetchrow("""
                SELECT approval_status
                FROM incidents
                WHERE incident_id = $1
            """, incident_id)
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
            
            if row["approval_status"] != "pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"Incident {incident_id} is not at interrupt point (status: {row['approval_status']})"
                )
            
            # Update to rejected
            await conn.execute("""
                UPDATE incidents
                SET approval_status = 'rejected',
                    approved_by = $1,
                    approved_at = CURRENT_TIMESTAMP,
                    rejection_reason = $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE incident_id = $3
            """, approval.approved_by, approval.reason, incident_id)
        
        logger.info(f"Incident {incident_id} rejected by {approval.approved_by}: {approval.reason}")
        
        # Log rejection
        await agent_logger.log_step(
            incident_id=incident_id,
            step_name="human_rejection",
            step_order=3,
            status="rejected",
            input_data={"rejected_by": approval.approved_by, "reason": approval.reason}
        )
        
        # Tell HITL agent to stop (workflow will not resume)
        hitl_incident_agent.continue_after_approval(
            incident_id=incident_id,
            approved=False,
            feedback=approval.reason
        )
        
        return {
            "success": True,
            "incident_id": incident_id,
            "message": f"Incident {incident_id} rejected - LangGraph workflow terminated",
            "rejected_by": approval.approved_by,
            "reason": approval.reason,
            "workflow_state": "terminated_at_interrupt",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
