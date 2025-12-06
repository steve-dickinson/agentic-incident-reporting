"""LangGraph agent with Human-in-the-Loop using checkpointer interrupts."""

import logging
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

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


class HITLIncidentState(TypedDict):
    """HITL Incident processing workflow state."""
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
    # HITL fields
    human_approval_required: bool
    human_approved: bool | None
    human_feedback: str | None
    modified_classification: dict[str, Any] | None


class HITLIncidentAgent:
    """Incident agent with Human-in-the-Loop at critical decision points."""
    
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
        
        # Create checkpointer for state persistence
        self.checkpointer = MemorySaver()
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow with HITL interrupt after classification."""
        workflow = StateGraph(HITLIncidentState)
        
        workflow.add_node("classify", self._classify_incident)
        workflow.add_node("human_review", self._request_human_review)
        workflow.add_node("spatial", self._check_spatial_context)
        workflow.add_node("guidance", self._search_guidance)
        workflow.add_node("notify", self._send_notifications)
        workflow.add_node("finalize", self._finalize_response)
        
        workflow.set_entry_point("classify")
        
        # After classification, go to human review
        workflow.add_edge("classify", "human_review")
        
        # After human review, continue to spatial analysis
        # This will be interrupted if human_approved is None
        workflow.add_edge("human_review", "spatial")
        workflow.add_edge("spatial", "guidance")
        workflow.add_edge("guidance", "notify")
        workflow.add_edge("notify", "finalize")
        workflow.add_edge("finalize", END)
        
        # Compile with checkpointer and interrupt before human decision
        return workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["spatial"]  # Pause before spatial if human approval needed
        )
    
    def _classify_incident(self, state: HITLIncidentState) -> HITLIncidentState:
        """Classify incident and determine if human approval is needed."""
        state["step"] = "classify"
        logger.info(f"Classifying incident {state['incident_id']}")
        
        try:
            # Call the tool properly (it's a LangChain StructuredTool)
            result = classify_incident.invoke({
                "incident_type": state["incident_type"],
                "description": state["description"],
                "location": state["location"],
                "urgency": state["urgency"]
            })
            
            state["classification"] = result
            state["severity"] = result.get("severity", "medium")
            state["priority"] = result.get("priority", "P3")
            state["actions"] = result.get("required_actions", [])
            
            # Determine if human approval is required (P1 or P2)
            priority = state["priority"]
            state["human_approval_required"] = (
                priority.startswith("P1") or priority.startswith("P2")
            )
            
            logger.info(
                f"Incident {state['incident_id']} classified as {state['severity']} "
                f"({priority}), human_approval_required={state['human_approval_required']}"
            )
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            state["errors"].append(f"Classification error: {str(e)}")
        
        return state
    
    def _request_human_review(self, state: HITLIncidentState) -> HITLIncidentState:
        """Request human review for high-priority incidents."""
        state["step"] = "human_review"
        
        if not state["human_approval_required"]:
            # Low priority, auto-approve
            state["human_approved"] = True
            state["human_feedback"] = "Auto-approved (low priority)"
            logger.info(f"Incident {state['incident_id']} auto-approved (low priority)")
        else:
            # High priority - wait for human input
            # The interrupt_before=["spatial"] will pause execution here
            logger.info(
                f"Incident {state['incident_id']} awaiting human review "
                f"(severity={state['severity']}, priority={state['priority']})"
            )
            # State will be persisted and execution will pause
            # human_approved will be None until human provides input
        
        return state
    
    def _check_spatial_context(self, state: HITLIncidentState) -> HITLIncidentState:
        """Check spatial context - only runs after human approval."""
        state["step"] = "spatial"
        logger.info(f"Checking spatial context for {state['incident_id']}")
        
        # Apply human modifications if provided
        if state.get("modified_classification"):
            logger.info(f"Applying human modifications to classification")
            state["classification"].update(state["modified_classification"])
            state["severity"] = state["modified_classification"].get(
                "severity", state["severity"]
            )
        
        spatial_data = {}
        
        try:
            if state["latitude"] and state["longitude"]:
                # Find nearby protected sites
                protected = find_nearby_protected_sites.invoke({
                    "latitude": state["latitude"],
                    "longitude": state["longitude"],
                    "radius_km": 5.0
                })
                spatial_data["protected_sites"] = protected
                
                # Find nearby water bodies
                water = find_nearby_water_bodies.invoke({
                    "latitude": state["latitude"],
                    "longitude": state["longitude"],
                    "radius_km": 5.0
                })
                spatial_data["water_bodies"] = water
                
                # Check similar incidents
                similar = check_similar_incidents.invoke({
                    "location": state["location"],
                    "incident_type": state["incident_type"],
                    "days": 30
                })
                spatial_data["similar_incidents"] = similar
            
            state["spatial_context"] = spatial_data
            
        except Exception as e:
            logger.error(f"Spatial analysis failed: {e}")
            state["errors"].append(f"Spatial error: {str(e)}")
        
        return state
    
    def _search_guidance(self, state: HITLIncidentState) -> HITLIncidentState:
        """Search for relevant guidance documents."""
        state["step"] = "guidance"
        logger.info(f"Searching guidance for {state['incident_id']}")
        
        try:
            query = f"{state['incident_type']} {state['description']} {state['severity']}"
            guidance_result = search_guidance_documents.invoke({"query": query, "top_k": 3})
            state["guidance"] = guidance_result
            
        except Exception as e:
            logger.error(f"Guidance search failed: {e}")
            state["errors"].append(f"Guidance error: {str(e)}")
        
        return state
    
    def _send_notifications(self, state: HITLIncidentState) -> HITLIncidentState:
        """Send notifications to relevant parties."""
        state["step"] = "notify"
        logger.info(f"Sending notifications for {state['incident_id']}")
        
        try:
            notification_result = send_notification_tool.invoke({
                "incident_id": state["incident_id"],
                "severity": state["severity"],
                "recipient_email": state["reporter_email"] or "duty@environment.gov.uk"
            })
            state["notifications_sent"] = notification_result
            
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            state["errors"].append(f"Notification error: {str(e)}")
        
        return state
    
    def _finalize_response(self, state: HITLIncidentState) -> HITLIncidentState:
        """Finalize the incident response."""
        state["step"] = "finalize"
        logger.info(f"Finalizing {state['incident_id']}")
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
        """Process incident with HITL support.
        
        Returns the current state. If human approval is required,
        the state will have human_approved=None and execution will be paused.
        """
        initial_state: HITLIncidentState = {
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
            "step": "initialize",
            "errors": [],
            "human_approval_required": False,
            "human_approved": None,
            "human_feedback": None,
            "modified_classification": None
        }
        
        # Run workflow with checkpointing
        config = {"configurable": {"thread_id": incident_id}}
        result = self.workflow.invoke(initial_state, config)
        
        return {
            "success": len(result["errors"]) == 0,
            "incident_id": incident_id,
            "severity": result["severity"],
            "priority": result["priority"],
            "classification": result["classification"],
            "actions": result["actions"],
            "spatial_context": result["spatial_context"],
            "guidance": result["guidance"],
            "notifications": result["notifications_sent"],
            "errors": result["errors"],
            "human_approval_required": result["human_approval_required"],
            "human_approved": result["human_approved"],
            "awaiting_human": result["human_approval_required"] and result["human_approved"] is None
        }
    
    def continue_after_approval(
        self,
        incident_id: str,
        approved: bool,
        feedback: str | None = None,
        modified_classification: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Continue processing after human approval/rejection."""
        config = {"configurable": {"thread_id": incident_id}}
        
        # Get current state
        current_state = self.workflow.get_state(config)
        
        # Update state with human decision
        current_state.values["human_approved"] = approved
        current_state.values["human_feedback"] = feedback
        if modified_classification:
            current_state.values["modified_classification"] = modified_classification
        
        # Update the checkpoint
        self.workflow.update_state(config, current_state.values)
        
        if not approved:
            # Rejected - stop processing
            logger.info(f"Incident {incident_id} rejected by human: {feedback}")
            return {
                "success": False,
                "incident_id": incident_id,
                "message": "Incident rejected by human reviewer",
                "rejection_reason": feedback
            }
        
        # Approved - continue processing
        logger.info(f"Incident {incident_id} approved by human, continuing workflow")
        result = self.workflow.invoke(None, config)
        
        return {
            "success": len(result["errors"]) == 0,
            "incident_id": incident_id,
            "severity": result["severity"],
            "priority": result["priority"],
            "classification": result["classification"],
            "actions": result["actions"],
            "spatial_context": result["spatial_context"],
            "guidance": result["guidance"],
            "notifications": result["notifications_sent"],
            "errors": result["errors"],
            "human_feedback": feedback
        }


# Create singleton instance
hitl_incident_agent = HITLIncidentAgent()
