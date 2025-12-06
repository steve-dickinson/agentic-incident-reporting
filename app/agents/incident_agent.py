"""LangGraph agent for processing environmental incident reports."""

from typing import Any, TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import logging

from app.models.config import settings
from app.tools.classification import classify_incident_tool
from app.tools.notify import send_notification_tool

logger = logging.getLogger(__name__)


class IncidentState(TypedDict):
    """Incident processing workflow state."""
    incident_id: str
    incident_type: str
    description: str
    location: str
    reporter_email: str | None
    urgency: str
    classification: dict[str, Any] | None
    severity: str | None
    priority: str | None
    actions: list[str] | None
    notifications_sent: dict[str, Any] | None
    step: str
    errors: list[str]


class IncidentAgent:
    """Processes incidents through classify -> notify -> finalize workflow."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model_name,
            temperature=0.1,
            api_key=settings.openai_api_key
        )
        
        self.tools = [classify_incident_tool, send_notification_tool]
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        workflow = StateGraph(IncidentState)
        
        workflow.add_node("classify", self._classify_incident)
        workflow.add_node("notify", self._send_notifications)
        workflow.add_node("finalize", self._finalize_response)
        
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "notify")
        workflow.add_edge("notify", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _classify_incident(self, state: IncidentState) -> IncidentState:
        try:
            logger.info(f"Classifying incident {state['incident_id']}")
            
            result = classify_incident_tool._run(
                incident_type=state["incident_type"],
                description=state["description"],
                location=state["location"],
                urgency=state["urgency"]
            )
            
            state["classification"] = result
            state["severity"] = result["severity"]
            state["priority"] = result["priority"]
            state["actions"] = result["required_actions"]
            state["step"] = "classified"
            
            logger.info(
                f"Incident {state['incident_id']} classified as "
                f"{result['severity']} severity"
            )
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            state["errors"].append(f"Classification failed: {str(e)}")
        
        return state
    
    def _send_notifications(self, state: IncidentState) -> IncidentState:
        try:
            logger.info(f"Sending notifications for {state['incident_id']}")
            
            result = send_notification_tool._run(
                incident_id=state["incident_id"],
                incident_type=state["incident_type"],
                severity=state["severity"] or "medium",
                message_type="acknowledgment",
                recipient_email=state.get("reporter_email")
            )
            
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
        reporter_email: str | None = None,
        urgency: str = "medium"
    ) -> dict[str, Any]:
        initial_state: IncidentState = {
            "incident_id": incident_id,
            "incident_type": incident_type,
            "description": description,
            "location": location,
            "reporter_email": reporter_email,
            "urgency": urgency,
            "classification": None,
            "severity": None,
            "priority": None,
            "actions": None,
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
