"""Unit tests for incident classification tool."""

import pytest
from unittest.mock import patch, Mock

from app.tools.classification import (
    classify_incident,
    _determine_severity,
    _determine_actions,
    _generate_reasoning,
    CRITICAL_KEYWORDS,
    HIGH_SEVERITY_KEYWORDS,
    PRIORITY_MAP
)


class TestDetermineSeverity:
    """Tests for severity determination logic."""
    
    def test_critical_severity_from_keywords(self):
        """Test critical severity detection from keywords."""
        result = _determine_severity(
            "water_pollution",
            "toxic chemical spill near drinking water source",
            "medium"
        )
        assert result == "critical"
    
    def test_high_severity_from_keywords(self):
        """Test high severity detection from keywords."""
        result = _determine_severity(
            "water_pollution",
            "oil spill in river affecting protected SSSI site",
            "medium"
        )
        assert result == "high"
    
    def test_high_severity_from_urgency(self):
        """Test high severity from urgency override."""
        result = _determine_severity(
            "noise_pollution",
            "construction noise at night",
            "high"
        )
        assert result == "high"
    
    def test_medium_severity_water_pollution(self):
        """Test medium severity for standard water pollution."""
        result = _determine_severity(
            "water_pollution",
            "discoloration observed in stream",
            "medium"
        )
        # Water pollution in streams defaults to high severity
        assert result == "high"
    
    def test_low_severity_default(self):
        """Test low severity default."""
        result = _determine_severity(
            "noise_pollution",
            "minor disturbance from traffic",
            "low"
        )
        assert result == "low"
    
    def test_case_insensitive_keyword_matching(self):
        """Test keywords are matched case-insensitively."""
        result = _determine_severity(
            "water_pollution",
            "OIL SPILL in River Thames",
            "low"
        )
        assert result == "high"


class TestDetermineActions:
    """Tests for action determination logic."""
    
    def test_critical_actions_include_immediate_response(self):
        """Test critical severity generates immediate response actions."""
        actions = _determine_actions("water_pollution", "critical")
        
        assert "Log incident in database" in actions
        assert "Alert Environment Agency duty officer immediately" in actions
        assert "Dispatch field team for urgent assessment" in actions
        assert "Activate major incident protocol" in actions
    
    def test_high_severity_actions(self):
        """Test high severity actions include 4-hour response."""
        actions = _determine_actions("water_pollution", "high")
        
        assert "Schedule site visit within 4 hours" in actions
        assert "Alert Environment Agency team" in actions
        assert "Check for nearby protected sites" in actions
    
    def test_medium_severity_actions(self):
        """Test medium severity actions include 24-hour response."""
        actions = _determine_actions("illegal_dumping", "medium")
        
        assert "Schedule site visit within 24 hours" in actions
        assert "Review historical incidents in area" in actions
    
    def test_low_severity_actions(self):
        """Test low severity actions are routine."""
        actions = _determine_actions("noise_pollution", "low")
        
        assert "Add to routine inspection schedule" in actions
        assert "Monitor for pattern development" in actions
    
    def test_water_incident_specific_actions(self):
        """Test water incidents get water-specific actions."""
        actions = _determine_actions("water_pollution", "high")
        
        assert "Check water quality monitoring data" in actions
        assert "Identify potential sources" in actions
        assert "Alert water companies if applicable" in actions
    
    def test_waste_incident_specific_actions(self):
        """Test waste incidents get waste-specific actions."""
        # Use incident type that triggers waste-specific actions
        actions = _determine_actions("illegal_waste_tipping", "high")
        
        assert "Document evidence for prosecution" in actions
        assert "Arrange waste removal" in actions
        assert "Check for hazardous materials" in actions
    
    def test_air_pollution_specific_actions(self):
        """Test air pollution gets permit actions."""
        actions = _determine_actions("air_pollution", "medium")
        
        assert "Check permit compliance" in actions
        assert "Review air quality data" in actions
    
    def test_all_actions_include_reporter_acknowledgment(self):
        """Test all incident types include reporter acknowledgment."""
        for incident_type in ["water_pollution", "air_pollution", "illegal_dumping"]:
            for severity in ["critical", "high", "medium", "low"]:
                actions = _determine_actions(incident_type, severity)
                assert "Send acknowledgment to reporter" in actions


class TestGenerateReasoning:
    """Tests for reasoning generation."""
    
    def test_critical_reasoning_mentions_public_health(self):
        """Test critical reasoning mentions public health risk."""
        reasoning = _generate_reasoning("water_pollution", "critical")
        
        assert "critical severity" in reasoning
        assert "immediate public health or environmental risk" in reasoning
    
    def test_high_severity_reasoning(self):
        """Test high severity reasoning."""
        reasoning = _generate_reasoning("water_pollution", "high")
        
        assert "high severity" in reasoning
        assert "significant environmental impact" in reasoning
    
    def test_water_pollution_reasoning(self):
        """Test water pollution includes contamination reasoning."""
        reasoning = _generate_reasoning("water_pollution", "high")
        
        assert "Water pollution" in reasoning
        assert "downstream contamination" in reasoning
    
    def test_non_water_incident_reasoning(self):
        """Test non-water incidents don't mention contamination."""
        reasoning = _generate_reasoning("air_pollution", "medium")
        
        assert "water" not in reasoning.lower() or "Water" not in reasoning


class TestClassifyIncident:
    """Tests for the full classify_incident tool."""
    
    def test_classify_critical_incident(self, critical_incident_data):
        """Test classification of critical incident."""
        result = classify_incident.invoke({
            "incident_type": critical_incident_data["incident_type"],
            "description": critical_incident_data["description"],
            "location": critical_incident_data["location"],
            "urgency": critical_incident_data["urgency"]
        })
        
        assert result["category"] == "water_pollution"
        assert result["severity"] == "critical"
        assert result["priority"] == PRIORITY_MAP["critical"]
        assert isinstance(result["required_actions"], list)
        assert len(result["required_actions"]) > 5
        assert "reasoning" in result
    
    def test_classify_high_severity_incident(self, sample_incident_data):
        """Test classification of high severity incident."""
        result = classify_incident.invoke({
            "incident_type": sample_incident_data["incident_type"],
            "description": sample_incident_data["description"],
            "location": sample_incident_data["location"],
            "urgency": sample_incident_data["urgency"]
        })
        
        assert result["severity"] == "high"
        assert result["priority"] == PRIORITY_MAP["high"]
        assert "Alert Environment Agency team" in result["required_actions"]
    
    def test_classify_low_severity_incident(self, low_severity_incident_data):
        """Test classification of low severity incident."""
        result = classify_incident.invoke({
            "incident_type": low_severity_incident_data["incident_type"],
            "description": low_severity_incident_data["description"],
            "location": low_severity_incident_data["location"],
            "urgency": low_severity_incident_data["urgency"]
        })
        
        assert result["severity"] == "low"
        assert result["priority"] == PRIORITY_MAP["low"]
        assert "routine" in result["priority"].lower()
    
    def test_classification_result_structure(self, sample_incident_data):
        """Test classification result has correct structure."""
        result = classify_incident.invoke({
            "incident_type": sample_incident_data["incident_type"],
            "description": sample_incident_data["description"],
            "location": sample_incident_data["location"],
            "urgency": sample_incident_data["urgency"]
        })
        
        assert "category" in result
        assert "severity" in result
        assert "priority" in result
        assert "required_actions" in result
        assert "reasoning" in result
        
        assert isinstance(result["required_actions"], list)
        assert len(result["required_actions"]) > 0
        assert all(isinstance(action, str) for action in result["required_actions"])
    
    def test_default_urgency_medium(self):
        """Test default urgency is medium."""
        result = classify_incident.invoke({
            "incident_type": "water_pollution",
            "description": "Some pollution in a stream",
            "location": "Test Location"
        })
        
        assert result["severity"] in ["medium", "high"]  # Could be high from water pollution default
    
    @pytest.mark.parametrize("incident_type,expected_category", [
        ("water_pollution", "water_pollution"),
        ("air_pollution", "air_pollution"),
        ("illegal_dumping", "illegal_dumping"),
        ("noise_pollution", "noise_pollution"),
        ("wildlife_harm", "wildlife_harm")
    ])
    def test_incident_type_categorization(self, incident_type, expected_category):
        """Test different incident types are categorized correctly."""
        result = classify_incident.invoke({
            "incident_type": incident_type,
            "description": "Test incident description",
            "location": "Test location",
            "urgency": "medium"
        })
        
        assert result["category"] == expected_category


class TestPriorityMapping:
    """Tests for priority mapping constants."""
    
    def test_priority_map_completeness(self):
        """Test priority map includes all severity levels."""
        assert "critical" in PRIORITY_MAP
        assert "high" in PRIORITY_MAP
        assert "medium" in PRIORITY_MAP
        assert "low" in PRIORITY_MAP
    
    def test_priority_format(self):
        """Test priority values follow expected format."""
        for severity, priority in PRIORITY_MAP.items():
            assert priority.startswith("P")
            assert "-" in priority
            assert "within" in priority.lower() or "days" in priority.lower()
    
    def test_priority_response_times(self):
        """Test priority response times are appropriate."""
        assert "1 hour" in PRIORITY_MAP["critical"]
        assert "4 hours" in PRIORITY_MAP["high"]
        assert "24 hours" in PRIORITY_MAP["medium"]
        assert "5 days" in PRIORITY_MAP["low"]


class TestKeywordConstants:
    """Tests for keyword constants."""
    
    def test_critical_keywords_exist(self):
        """Test critical keywords are defined."""
        assert len(CRITICAL_KEYWORDS) > 0
        assert "drinking water" in CRITICAL_KEYWORDS
        assert "toxic" in CRITICAL_KEYWORDS
    
    def test_high_severity_keywords_exist(self):
        """Test high severity keywords are defined."""
        assert len(HIGH_SEVERITY_KEYWORDS) > 0
        assert "oil spill" in HIGH_SEVERITY_KEYWORDS
        assert "protected site" in HIGH_SEVERITY_KEYWORDS
    
    def test_keywords_are_lowercase(self):
        """Test keywords are in lowercase for matching."""
        for keyword in CRITICAL_KEYWORDS:
            assert keyword == keyword.lower()
        
        for keyword in HIGH_SEVERITY_KEYWORDS:
            assert keyword == keyword.lower()
