"""LangGraph agent for processing environmental incident reports."""

import logging
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from app.models.config import settings
from app.tools.classification import classify_incident
from app.tools.notify import send_notification_tool
from app.tools.spatial import (
    find_nearby_protected_sites,
    find_nearby_water_bodies,
    check_similar_incidents
)
from app.tools.semantic_search import search_guidance_documents

logger = logging.getLogger(__name__)


class IncidentState(TypedDict):
    """Incident processing workflow state."""
    incident_id: str
    incident_type: str
    description: str
    location: str
    latitude: float | None
    longitude: float | None
    reporter_email: str | None
    urgency: str
    classification: dict[str, str | list[str]] | None
    severity: str | None
    priority: str | None
    actions: list[str] | None
    spatial_context: dict[str, str | list[dict[str, str]]] | None
    guidance: str | None
    notifications_sent: dict[str, str] | None
    step: str
    errors: list[str]


class IncidentAgent:
    """Processes incidents through classify -> spatial -> guidance -> notify -> finalize workflow."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model_name,
            temperature=0.1,
            api_key=settings.openai_api_key
        )
        
        self.tools = [
            classify_incident,
            send_notification_tool,
            find_nearby_protected_sites,
            find_nearby_water_bodies,
            check_similar_incidents,
            search_guidance_documents
        ]
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        workflow = StateGraph(IncidentState)
        
        workflow.add_node("classify", self._classify_incident)
        workflow.add_node("spatial", self._check_spatial_context)
        workflow.add_node("guidance", self._search_guidance)
        workflow.add_node("notify", self._send_notifications)
        workflow.add_node("finalize", self._finalize_response)
        
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "spatial")
        workflow.add_edge("spatial", "guidance")
        workflow.add_edge("guidance", "notify")
        workflow.add_edge("notify", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _classify_incident(self, state: IncidentState) -> IncidentState:
        try:
            logger.info(f"Classifying incident {state['incident_id']}")
            
            result = classify_incident.invoke({
                "incident_type": state["incident_type"],
                "description": state["description"],
                "location": state["location"],
                "urgency": state["urgency"]
            })
            
            state["classification"] = result
            state["severity"] = result["severity"]
            state["priority"] = result["priority"]
            state["actions"] = result["required_actions"]
            state["step"] = "classified"
            
            logger.info(f"Classified as {state['severity']} severity, {state['priority']} priority")
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            state["errors"].append(f"Classification failed: {str(e)}")
            state["severity"] = "unknown"
            state["priority"] = "P4"
        
        return state
    
    def _check_spatial_context(self, state: IncidentState) -> IncidentState:
        """Check for nearby protected sites and water bodies."""
        try:
            logger.info(f"Checking spatial context for incident {state['incident_id']}")
            
            spatial_info = {}
            
            # Only check spatial context if coordinates provided
            if state.get("latitude") and state.get("longitude"):
                lat = state["latitude"]
                lon = state["longitude"]
                
                # Find nearby protected sites
                sites_result = find_nearby_protected_sites.invoke({
                    "latitude": lat,
                    "longitude": lon,
                    "radius_km": 5.0
                })
                spatial_info["protected_sites"] = sites_result
                
                # Find nearby water bodies
                water_result = find_nearby_water_bodies.invoke({
                    "latitude": lat,
                    "longitude": lon,
                    "radius_km": 10.0
                })
                spatial_info["water_bodies"] = water_result
                
                # Check for similar historical incidents
                similar_result = check_similar_incidents.invoke({
                    "incident_type": state["incident_type"],
                    "latitude": lat,
                    "longitude": lon,
                    "days_back": 90,
                    "radius_km": 25.0
                })
                spatial_info["historical_incidents"] = similar_result
                
                logger.info(f"Spatial context gathered: {len(spatial_info)} categories")
            else:
                spatial_info["message"] = "No coordinates provided; spatial queries skipped"
            
            state["spatial_context"] = spatial_info
            state["step"] = "spatial_checked"
            
        except Exception as e:
            logger.error(f"Spatial context error: {e}")
            state["errors"].append(f"Spatial query failed: {str(e)}")
            state["spatial_context"] = {"error": str(e)}
        
        return state
    
    def _search_guidance(self, state: IncidentState) -> IncidentState:
        """Search for relevant guidance documents."""
        try:
            logger.info(f"Searching guidance for incident {state['incident_id']}")
            
            # Create search query based on incident details
            query = (
                f"{state['incident_type']} incident "
                f"severity {state.get('severity', 'medium')} "
                f"{state.get('description', '')[:100]}"
            )
            
            guidance_result = search_guidance_documents.invoke({
                "query": query,
                "top_k": 2
            })
            
            state["guidance"] = guidance_result
            state["step"] = "guidance_retrieved"
            
            logger.info(f"Retrieved guidance for {state['incident_type']}")
            
        except Exception as e:
            logger.error(f"Guidance search error: {e}")
            state["errors"].append(f"Guidance search failed: {str(e)}")
            state["guidance"] = None
        
        return state
    
    def _send_notifications(self, state: IncidentState) -> IncidentState:
        try:
            logger.info(f"Sending notifications for {state['incident_id']}")
            
            result = send_notification_tool.invoke({
                "incident_id": state["incident_id"],
                "incident_type": state["incident_type"],
                "severity": state["severity"] or "medium",
                "message_type": "acknowledgment",
                "recipient_email": state.get("reporter_email")
            })
            
            state["notifications_sent"] = result
            state["step"] = "notified"
            
            logger.info(f"Notifications sent: {result}")
            
        except Exception as e:
            logger.error(f"Notification error: {e}")
            state["errors"].append(f"Notification failed: {str(e)}")
        
        return state
    
    def _finalize_response(self, state: IncidentState) -> IncidentState:
        state["step"] = "complete"
        return state
    
    def process_incident(
        self,
        incident_id: str,
        incident_type: str,
        description: str,
        location: str,
        latitude: float | None = None,
        longitude: float | None = None,
        reporter_email: str | None = None,
        urgency: str = "medium"
    ) -> dict[str, Any]:
        initial_state: IncidentState = {
            "incident_id": incident_id,
            "incident_type": incident_type,
            "description": description,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "reporter_email": reporter_email,
            "urgency": urgency,
            "classification": None,
            "severity": None,
            "priority": None,
            "actions": None,
            "spatial_context": None,
            "guidance": None,
            "notifications_sent": None,
            "step": "initialized",
            "errors": []
        }
        
        try:
            final_state = self.workflow.invoke(initial_state)
            
            return {
                "success": True,
                "incident_id": final_state["incident_id"],
                "severity": final_state["severity"],
                "priority": final_state["priority"],
                "actions": final_state["actions"],
                "classification": final_state["classification"],
                "spatial_context": final_state.get("spatial_context"),
                "guidance": final_state.get("guidance"),
                "notifications": final_state["notifications_sent"],
                "errors": final_state["errors"]
            }
            
        except Exception as e:
            logger.error(f"Workflow error for {incident_id}: {e}")
            return {
                "success": False,
                "incident_id": incident_id,
                "error": str(e)
            }


incident_agent = IncidentAgent()
