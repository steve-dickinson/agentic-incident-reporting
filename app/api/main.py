"""FastAPI application for environmental incident reporting."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any
import logging
from datetime import datetime

from app.agents.incident_agent import incident_agent

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    notifications: dict[str, Any] | None = None
    errors: list[str] | None = None
    timestamp: str


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
    """Submit incident for AI classification and notification."""
    try:
        logger.info(f"Received incident submission: {incident.incident_type}")
        
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        result = incident_agent.process_incident(
            incident_id=incident_id,
            incident_type=incident.incident_type,
            description=incident.description,
            location=incident.location,
            latitude=incident.latitude,
            longitude=incident.longitude,
            reporter_email=incident.reporter_email,
            urgency=incident.urgency or "medium"
        )
        
        if result["success"]:
            message = (
                f"Incident {incident_id} received and classified as "
                f"{result['severity']} severity. {result['priority']}"
            )
        else:
            message = f"Incident {incident_id} received but processing encountered errors"
        
        return IncidentResponse(
            success=result["success"],
            incident_id=incident_id,
            message=message,
            severity=result.get("severity"),
            priority=result.get("priority"),
            classification=result.get("classification"),
            actions=result.get("actions"),
            spatial_context=result.get("spatial_context"),
            notifications=result.get("notifications"),
            errors=result.get("errors", []),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing incident: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    return {
        "incident_id": incident_id,
        "status": "pending",
        "message": "Incident retrieval not yet implemented"
    }


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
