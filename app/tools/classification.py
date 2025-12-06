"""Incident classification tool for environmental incidents."""

from langchain.tools import BaseTool
from typing import Any, Final

CRITICAL_KEYWORDS: Final = [
    "drinking water", "mass fish kill", "evacuation", "toxic",
    "hazardous", "emergency", "immediate danger", "life threatening"
]

HIGH_SEVERITY_KEYWORDS: Final = [
    "oil spill", "chemical", "protected site", "sssi", "sac",
    "sewage", "dead fish", "wildlife harm", "major"
]

PRIORITY_MAP: Final = {
    "critical": "P1 - Immediate Response (within 1 hour)",
    "high": "P2 - Urgent Response (within 4 hours)",
    "medium": "P3 - Standard Response (within 24 hours)",
    "low": "P4 - Routine Response (within 5 days)"
}


class ClassifyIncidentTool(BaseTool):
    """Tool to classify environmental incidents"""
    
    name: str = "classify_incident"
    description: str = """
    Classifies an environmental incident based on type, description, and location.
    Returns the category, severity, priority, and required actions.
    Use this tool when you need to determine the appropriate response for an incident.
    """
    
    def _run(
        self,
        incident_type: str,
        description: str,
        location: str,
        urgency: str = "medium"
    ) -> dict[str, Any]:
        severity = self._determine_severity(incident_type, description, urgency)
        priority = self._determine_priority(severity, incident_type)
        actions = self._determine_actions(incident_type, severity)
        reasoning = self._generate_reasoning(incident_type, severity, description)
        
        return {
            "category": incident_type,
            "severity": severity,
            "priority": priority,
            "required_actions": actions,
            "reasoning": reasoning
        }
    
    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async execution not supported")
    
    def _determine_severity(
        self,
        incident_type: str,
        description: str,
        urgency: str
    ) -> str:
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in CRITICAL_KEYWORDS):
            return "critical"
        
        if any(keyword in description_lower for keyword in HIGH_SEVERITY_KEYWORDS):
            return "high"
        
        if urgency in ("critical", "high"):
            return urgency
        
        if "pollution" in incident_type and "water" in incident_type:
            if any(word in description_lower for word in ("river", "stream", "lake")):
                return "high"
        
        if incident_type in ("water_pollution", "chemical_spill", "oil_spill"):
            return "medium"
        
        return "low"
    
    def _determine_priority(self, severity: str, incident_type: str) -> str:
        return PRIORITY_MAP.get(severity, PRIORITY_MAP["medium"])
    
    def _determine_actions(self, incident_type: str, severity: str) -> list[str]:
        actions = ["Log incident in database", "Assign incident ID"]
        
        if severity == "critical":
            actions.extend([
                "Alert Environment Agency duty officer immediately",
                "Dispatch field team for urgent assessment",
                "Notify emergency services if required",
                "Issue public warning if necessary",
                "Activate major incident protocol"
            ])
        elif severity == "high":
            actions.extend([
                "Alert Environment Agency team",
                "Schedule site visit within 4 hours",
                "Notify relevant authorities",
                "Check for nearby protected sites",
                "Prepare evidence collection"
            ])
        elif severity == "medium":
            actions.extend([
                "Notify appropriate team",
                "Schedule site visit within 24 hours",
                "Review historical incidents in area"
            ])
        else:
            actions.extend([
                "Add to routine inspection schedule",
                "Monitor for pattern development"
            ])
        
        if "water" in incident_type:
            actions.append("Check water quality monitoring data")
            actions.append("Identify potential sources")
            if severity in ["critical", "high"]:
                actions.append("Alert water companies if applicable")
        
        if "waste" in incident_type or "tipping" in incident_type:
            actions.append("Document evidence for prosecution")
            actions.append("Arrange waste removal")
            if severity == "high":
                actions.append("Check for hazardous materials")
        
        if "air" in incident_type:
            actions.append("Check permit compliance")
            actions.append("Review air quality data")
        
        actions.append("Send acknowledgment to reporter")
        
        return actions
    
    def _generate_reasoning(
        self,
        incident_type: str,
        severity: str,
        description: str
    ) -> str:
        reasoning_parts = [f"Incident classified as {severity} severity {incident_type}."]
        
        if severity == "critical":
            reasoning_parts.append(
                "Critical classification due to immediate public health or environmental risk."
            )
        elif severity == "high":
            reasoning_parts.append(
                "High severity due to significant environmental impact or protected site proximity."
            )
        
        if "water" in incident_type:
            reasoning_parts.append(
                "Water pollution incidents require urgent response to prevent downstream contamination."
            )
        
        return " ".join(reasoning_parts)


classify_incident_tool = ClassifyIncidentTool()
