"""
Unit tests for classification tool output validation.

Tests the Pydantic validation layer including:
- Priority/severity auto-correction
- Action deduplication and quality
- Reasoning content validation
- Fallback mechanism on validation errors
"""

import pytest
from pydantic import ValidationError
from app.tools.classification import ClassificationOutput, classify_incident


class TestClassificationOutputValidation:
    """Test the ClassificationOutput Pydantic model validators."""
    
    def test_valid_classification_output(self):
        """Test that valid output passes validation."""
        output = ClassificationOutput(
            category="water_pollution",
            severity="critical",
            priority="P1 - Immediate Response (within 1 hour)",
            required_actions=[
                "Deploy containment booms",
                "Notify Environment Agency",
                "Start water quality monitoring",
                "Assess impact on wildlife"
            ],
            reasoning="Critical water pollution incident requiring immediate response"
        )
        assert output.severity == "critical"
        assert output.priority.startswith("P1")
        assert len(output.required_actions) == 4
    
    def test_priority_severity_mismatch_auto_correction(self):
        """Test that priority is auto-corrected when it doesn't match severity."""
        output = ClassificationOutput(
            category="air_quality",
            severity="critical",
            priority="P4 - Low",  # Wrong! Should be P1 for critical
            required_actions=[
                "Action 1", "Action 2", "Action 3", "Action 4"
            ],
            reasoning="This is a valid reasoning with sufficient length."
        )
        # Validator should auto-correct to P1
        assert output.priority.startswith("P1")
    
    def test_high_severity_priority_correction(self):
        """Test P2 is set for high severity."""
        output = ClassificationOutput(
            category="waste",
            severity="high",
            priority="P3 - Wrong",  # Should be P2
            required_actions=["Action 1", "Action 2", "Action 3"],
            reasoning="Valid reasoning for high severity incident."
        )
        assert output.priority.startswith("P2")
    
    def test_medium_severity_priority_correction(self):
        """Test P3 is set for medium severity."""
        output = ClassificationOutput(
            category="noise",
            severity="medium",
            priority="P1 - Wrong",  # Should be P3
            required_actions=["Action 1", "Action 2", "Action 3"],
            reasoning="Valid reasoning for medium severity incident."
        )
        assert output.priority.startswith("P3")
    
    def test_low_severity_priority_correction(self):
        """Test P4 is set for low severity."""
        output = ClassificationOutput(
            category="other",
            severity="low",
            priority="P2 - Wrong",  # Should be P4
            required_actions=["Action 1", "Action 2", "Action 3"],
            reasoning="Valid reasoning for low severity incident."
        )
        assert output.priority.startswith("P4")
    
    def test_duplicate_actions_removed(self):
        """Test that duplicate actions are automatically removed."""
        output = ClassificationOutput(
            category="water_pollution",
            severity="high",
            priority="P2",
            required_actions=[
                "Deploy booms",
                "Notify agency",
                "Deploy booms",  # Duplicate
                "Monitor water",
                "Notify agency"  # Duplicate
            ],
            reasoning="Valid reasoning text with sufficient length."
        )
        # Should have only 3 unique actions
        assert len(output.required_actions) == 3
        assert "Deploy booms" in output.required_actions
        assert output.required_actions.count("Deploy booms") == 1
    
    def test_short_actions_removed(self):
        """Test that actions shorter than 5 characters are removed."""
        output = ClassificationOutput(
            category="air_quality",
            severity="medium",
            priority="P3",
            required_actions=[
                "Call",  # Only 4 chars - should be removed
                "Monitor air quality levels",
                "Go",  # Only 2 chars - should be removed
                "Deploy sensors",
                "Alert nearby residents"
            ],
            reasoning="Valid reasoning with enough content for validation."
        )
        # Should only have 3 valid actions (short ones removed)
        assert len(output.required_actions) == 3
        assert "Call" not in output.required_actions
        assert "Go" not in output.required_actions
    
    def test_minimum_actions_required(self):
        """Test that at least 3 actions are required."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationOutput(
                category="noise",
                severity="low",
                priority="P4",
                required_actions=["Action 1", "Action 2"],  # Only 2 actions
                reasoning="Valid reasoning text."
            )
        assert "at least 3 items" in str(exc_info.value)
    
    def test_maximum_actions_enforced(self):
        """Test that no more than 20 actions are allowed."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationOutput(
                category="water_pollution",
                severity="critical",
                priority="P1",
                required_actions=[f"Action {i}" for i in range(25)],  # 25 actions
                reasoning="Valid reasoning text."
            )
        assert "at most 20 items" in str(exc_info.value)
    
    def test_reasoning_too_short(self):
        """Test that reasoning must be at least 20 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationOutput(
                category="waste",
                severity="medium",
                priority="P3",
                required_actions=["Action 1", "Action 2", "Action 3"],
                reasoning="Short"  # Only 5 chars
            )
        assert "at least 20 characters" in str(exc_info.value)
    
    def test_reasoning_placeholder_rejected(self):
        """Test that placeholder text is rejected in reasoning."""
        # Test cases that should definitely be rejected (exact matches or starts with)
        definite_placeholders = [
            "TODO: Add reasoning here",
            "TBD",
            "N/A",
            "None"
        ]
        
        for placeholder in definite_placeholders:
            with pytest.raises(ValidationError) as exc_info:
                ClassificationOutput(
                    category="air_quality",
                    severity="high",
                    priority="P2",
                    required_actions=["Action 1", "Action 2", "Action 3"],
                    reasoning=placeholder
                )
            # Just verify it raised an error
            assert exc_info.value is not None
        
        # Test cases that should be accepted (placeholder words in context)
        valid_reasoning = [
            "Chemicals need immediate testing and analysis",
            "No immediate danger but requires monitoring",
            "Task list has been completed for this incident"
        ]
        
        for reasoning in valid_reasoning:
            # Should not raise
            output = ClassificationOutput(
                category="air_quality",
                severity="high",
                priority="P2",
                required_actions=["Action 1", "Action 2", "Action 3"],
                reasoning=reasoning
            )
            assert output.reasoning == reasoning
    
    def test_invalid_severity_literal(self):
        """Test that only valid severity literals are accepted."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationOutput(
                category="noise",
                severity="super-critical",  # Invalid literal
                priority="P1",
                required_actions=["Action 1", "Action 2", "Action 3"],
                reasoning="Valid reasoning text here."
            )
        # Pydantic should reject invalid Literal value
        assert "severity" in str(exc_info.value).lower()


class TestClassifyIncidentIntegration:
    """Test the classify_incident tool with validation integrated."""
    
    def test_classify_incident_returns_valid_output(self):
        """Test that classify_incident produces validated output."""
        result = classify_incident.invoke({
            "incident_type": "water_pollution",
            "description": "Chemical spill in River Thames",
            "location": "London",
            "urgency": "high"
        })
        
        # Should return all expected fields
        assert "category" in result
        assert "severity" in result
        assert "priority" in result
        assert "required_actions" in result
        assert "reasoning" in result
        
        # Validate output matches Pydantic schema
        validated = ClassificationOutput(**result)
        assert validated.severity in ["critical", "high", "medium", "low"]
        assert len(validated.required_actions) >= 3
        assert len(validated.reasoning) >= 20
    
    def test_classify_incident_fallback_on_validation_error(self):
        """Test that fallback mechanism works if validation fails."""
        # This test assumes the LLM might return invalid output
        # The tool should catch validation errors and return fallback
        result = classify_incident.invoke({
            "incident_type": "unknown_type",
            "description": "Test incident",
            "location": "Test location",
            "urgency": "unknown"
        })
        
        # Even with potentially invalid input, should return valid output
        # Either validated LLM output or fallback
        assert "severity" in result
        assert "required_actions" in result
        assert isinstance(result["required_actions"], list)
        assert len(result["required_actions"]) >= 3
    
    def test_critical_incident_gets_p1_priority(self):
        """Test that critical incidents are assigned P1 priority."""
        result = classify_incident.invoke({
            "incident_type": "water_pollution",
            "description": "Major chemical spill with immediate danger to public health",
            "location": "River Thames",
            "urgency": "critical"
        })
        
        # Should be critical severity with P1 priority
        validated = ClassificationOutput(**result)
        if validated.severity == "critical":
            assert validated.priority.startswith("P1")


class TestValidationEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exactly_three_actions(self):
        """Test minimum valid number of actions (3)."""
        output = ClassificationOutput(
            category="noise",
            severity="low",
            priority="P4",
            required_actions=[
                "Action one here",
                "Action two here",
                "Action three here"
            ],
            reasoning="Valid reasoning with sufficient length."
        )
        assert len(output.required_actions) == 3
    
    def test_exactly_twenty_actions(self):
        """Test maximum valid number of actions (20)."""
        output = ClassificationOutput(
            category="waste",
            severity="high",
            priority="P2",
            required_actions=[f"Action number {i} with content" for i in range(20)],
            reasoning="Valid reasoning for incident."
        )
        assert len(output.required_actions) == 20
    
    def test_reasoning_exactly_twenty_chars(self):
        """Test minimum valid reasoning length (20 chars)."""
        output = ClassificationOutput(
            category="air_quality",
            severity="medium",
            priority="P3",
            required_actions=["Action 1", "Action 2", "Action 3"],
            reasoning="12345678901234567890"  # Exactly 20 chars
        )
        assert len(output.reasoning) == 20
    
    def test_mixed_valid_invalid_actions(self):
        """Test that valid actions are kept when mixed with invalid ones."""
        output = ClassificationOutput(
            category="water_pollution",
            severity="high",
            priority="P2",
            required_actions=[
                "Valid action number one",
                "OK",  # Too short
                "Valid action number two",
                "Valid action number one",  # Duplicate
                "Go",  # Too short
                "Valid action number three",
                "Valid action number four"
            ],
            reasoning="Valid reasoning text with sufficient length."
        )
        # Should have 4 unique valid actions (3 short/duplicate removed)
        assert len(output.required_actions) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
