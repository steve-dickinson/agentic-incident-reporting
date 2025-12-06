"""Incident classification tool for environmental incidents."""

import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError
from typing import Final, Literal

from app.exceptions import ClassificationError

logger = logging.getLogger(__name__)

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


def _determine_severity(incident_type: str, description: str, urgency: str) -> str:
    """Determine incident severity based on keywords and context."""
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


def _determine_actions(incident_type: str, severity: str) -> list[str]:
    """Generate required actions based on incident type and severity."""
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


def _generate_reasoning(incident_type: str, severity: str) -> str:
    """Generate classification reasoning."""
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


class ClassificationOutput(BaseModel):
    """Validated classification output schema."""
    
    category: str = Field(..., description="Incident category/type")
    severity: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Severity level of the incident"
    )
    priority: str = Field(..., description="Priority level with response time")
    required_actions: list[str] = Field(
        ..., min_length=3, max_length=20, description="List of required actions"
    )
    reasoning: str = Field(
        ..., min_length=20, max_length=500, description="Classification reasoning"
    )
    
    @field_validator('priority')
    @classmethod
    def validate_priority_format(cls, v, info):
        """Ensure priority matches severity and has correct format."""
        if 'severity' not in info.data:
            return v
        
        severity = info.data['severity']
        expected_prefix = {
            "critical": "P1",
            "high": "P2", 
            "medium": "P3",
            "low": "P4"
        }
        
        prefix = expected_prefix.get(severity)
        if not v.startswith(prefix):
            logger.warning(
                f"Priority '{v}' doesn't match severity '{severity}'. "
                f"Expected to start with '{prefix}'"
            )
            # Auto-correct to match severity
            return PRIORITY_MAP.get(severity, v)
        
        return v
    
    @field_validator('required_actions')
    @classmethod
    def validate_required_actions(cls, v):
        """Ensure actions are meaningful and not duplicated."""
        # Remove duplicates while preserving order
        if len(v) != len(set(v)):
            seen = set()
            v = [x for x in v if not (x in seen or seen.add(x))]
            logger.warning("Removed duplicate actions from classification")
        
        # Remove short or poorly formatted actions
        valid_actions = []
        for action in v:
            action = action.strip()
            if len(action) >= 5:  # Minimum meaningful length
                valid_actions.append(action)
            else:
                logger.warning(f"Removed short action: '{action}'")
        
        if len(valid_actions) < 3:
            raise ValueError(f"After validation, only {len(valid_actions)} valid actions remain (minimum 3 required)")
        
        return valid_actions
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v):
        """Ensure reasoning is substantive."""
        v = v.strip()
        
        if not v:
            raise ValueError("Reasoning cannot be empty")
        
        # Check for placeholder text (be more specific to avoid false positives)
        placeholders = ["TODO:", "TBD", "N/A", "None"]
        v_lower = v.lower()
        for placeholder in placeholders:
            if v_lower.startswith(placeholder.lower()) or v_lower == placeholder.lower():
                raise ValueError(f"Reasoning appears to be placeholder text: {v}")
        
        return v


@tool
def classify_incident(
    incident_type: str,
    description: str,
    location: str,
    urgency: str = "medium"
) -> dict[str, str | list[str]]:
    """
    Classify environmental incident and determine appropriate response.
    
    Analyzes incident details to determine severity, priority level, and
    required actions based on UK environmental regulations and best practices.
    
    Args:
        incident_type: Type of environmental incident
        description: Detailed description of the incident
        location: Location where incident occurred
        urgency: Initial urgency assessment (critical, high, medium, low)
    
    Returns:
        Classification with severity, priority, required actions, and reasoning
    """
    severity = _determine_severity(incident_type, description, urgency)
    priority = PRIORITY_MAP.get(severity, PRIORITY_MAP["medium"])
    actions = _determine_actions(incident_type, severity)
    reasoning = _generate_reasoning(incident_type, severity)
    
    # Create unvalidated output
    output_data = {
        "category": incident_type,
        "severity": severity,
        "priority": priority,
        "required_actions": actions,
        "reasoning": reasoning
    }
    
    # Validate output before returning
    try:
        validated_output = ClassificationOutput(**output_data)
        logger.info(
            f"Classification validated: {incident_type} -> {severity} "
            f"({len(validated_output.required_actions)} actions)"
        )
        return validated_output.model_dump()
    except Exception as e:
        logger.error(f"Classification validation failed: {e}")
        logger.error(f"Invalid output: {output_data}")
        
        # Return fallback with minimal valid data
        fallback = {
            "category": incident_type,
            "severity": "medium",
            "priority": PRIORITY_MAP["medium"],
            "required_actions": [
                "Log incident in database",
                "Assign incident ID",
                "Notify appropriate team"
            ],
            "reasoning": f"Classification failed validation. Using medium severity default for {incident_type}."
        }
        logger.warning(f"Returning fallback classification: {fallback}")
        return fallback

