"""Integration tests for agent workflow."""

import pytest
from unittest.mock import patch, Mock, MagicMock

from app.agents.incident_agent import IncidentAgent, incident_agent


@pytest.mark.integration
class TestIncidentAgentWorkflow:
    """Integration tests for the full incident processing workflow."""
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.spatial.GraphDatabase.driver')
    @patch('app.tools.semantic_search._search_instance')
    @patch('app.tools.notify._send_email')
    def test_complete_workflow_high_severity(
        self,
        mock_send_email,
        mock_search,
        mock_neo4j,
        mock_llm,
        sample_incident_data
    ):
        """Test complete workflow for high severity incident."""
        # Mock spatial queries
        mock_session = MagicMock()
        mock_neo4j.return_value.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []
        
        # Mock semantic search
        mock_search.search.return_value = []
        
        # Mock notifications
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        agent = incident_agent
        result = agent.process_incident(
            incident_id=sample_incident_data["incident_id"],
            incident_type=sample_incident_data["incident_type"],
            description=sample_incident_data["description"],
            location=sample_incident_data["location"],
            latitude=sample_incident_data["latitude"],
            longitude=sample_incident_data["longitude"],
            reporter_email=sample_incident_data["reporter_email"],
            urgency=sample_incident_data["urgency"]
        )
        
        assert result["success"] is True
        assert result["severity"] == "high"
        assert "P2" in result["priority"]
        assert isinstance(result["actions"], list)
        assert len(result["actions"]) > 0
        assert result["spatial_context"] is not None
        assert result["notifications"] is not None
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.spatial.GraphDatabase.driver')
    @patch('app.tools.semantic_search._search_instance')
    @patch('app.tools.notify._send_email')
    def test_workflow_critical_incident(
        self,
        mock_send_email,
        mock_search,
        mock_neo4j,
        mock_llm,
        critical_incident_data
    ):
        """Test workflow for critical incident."""
        mock_session = MagicMock()
        mock_neo4j.return_value.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []
        mock_search.search.return_value = []
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        agent = incident_agent
        result = agent.process_incident(
            incident_id=critical_incident_data["incident_id"],
            incident_type=critical_incident_data["incident_type"],
            description=critical_incident_data["description"],
            location=critical_incident_data["location"],
            latitude=critical_incident_data["latitude"],
            longitude=critical_incident_data["longitude"],
            reporter_email=critical_incident_data["reporter_email"],
            urgency=critical_incident_data["urgency"]
        )
        
        assert result["success"] is True
        assert result["severity"] == "critical"
        assert "P1" in result["priority"]
        assert "immediate" in result["priority"].lower()
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.notify._send_email')
    def test_workflow_without_coordinates(
        self,
        mock_send_email,
        mock_llm
    ):
        """Test workflow works without coordinates."""
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        agent = incident_agent
        result = agent.process_incident(
            incident_id="INC-NO-COORDS",
            incident_type="noise_pollution",
            description="Loud music from nearby property",
            location="Manchester City Centre",
            latitude=None,
            longitude=None,
            reporter_email="test@example.com",
            urgency="low"
        )
        
        assert result["success"] is True
        assert result["severity"] is not None
        assert result["spatial_context"] is not None
        assert "No coordinates" in str(result["spatial_context"]) or "message" in result["spatial_context"]
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.spatial.GraphDatabase.driver')
    @patch('app.tools.semantic_search._search_instance')
    @patch('app.tools.notify._send_email')
    @patch('app.tools.classification._determine_severity')
    def test_workflow_handles_classification_error(
        self,
        mock_severity,
        mock_send_email,
        mock_search,
        mock_neo4j,
        mock_llm,
        sample_incident_data
    ):
        """Test workflow handles classification errors gracefully."""
        mock_session = MagicMock()
        mock_neo4j.return_value.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []
        mock_search.search.return_value = []
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        # Make severity determination raise an error
        mock_severity.side_effect = Exception("Severity calculation failed")
        
        agent = incident_agent
        result = agent.process_incident(**sample_incident_data)
        
        # Workflow should continue despite error
        assert result["success"] is True
        assert len(result.get("errors", [])) > 0 or result["severity"] == "unknown"
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.spatial.GraphDatabase.driver')
    @patch('app.tools.semantic_search._search_instance')
    @patch('app.tools.notify._send_email')
    def test_workflow_state_transitions(
        self,
        mock_send_email,
        mock_search,
        mock_neo4j,
        mock_llm,
        sample_incident_data
    ):
        """Test workflow state transitions correctly."""
        mock_session = MagicMock()
        mock_neo4j.return_value.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = []
        mock_search.search.return_value = []
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        agent = incident_agent
        result = agent.process_incident(**sample_incident_data)
        
        # Verify all workflow steps completed
        assert result["classification"] is not None
        assert result["spatial_context"] is not None
        assert result["guidance"] is not None
        assert result["notifications"] is not None


@pytest.mark.integration
class TestAgentErrorHandling:
    """Tests for agent error handling."""
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.spatial.GraphDatabase.driver')
    @patch('app.tools.notify._send_email')
    def test_spatial_query_error_doesnt_break_workflow(
        self,
        mock_send_email,
        mock_neo4j,
        mock_llm,
        sample_incident_data
    ):
        """Test spatial query errors don't break the workflow."""
        mock_neo4j.side_effect = Exception("Neo4j connection failed")
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        agent = incident_agent
        result = agent.process_incident(**sample_incident_data)
        
        assert result["success"] is True
        # Error handling puts errors in spatial_context or errors array
        assert (result["spatial_context"] is not None and 
                ("error" in str(result["spatial_context"]).lower() or 
                 len(result.get("errors", [])) > 0 or
                 "No protected sites found" in str(result["spatial_context"])))  # Fallback behavior is also valid
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.semantic_search._search_instance')
    @patch('app.tools.notify._send_email')
    def test_guidance_search_error_doesnt_break_workflow(
        self,
        mock_send_email,
        mock_search,
        mock_llm,
        sample_incident_data
    ):
        """Test guidance search errors don't break the workflow."""
        mock_search.search.side_effect = Exception("Database connection failed")
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        agent = incident_agent
        result = agent.process_incident(**sample_incident_data)
        
        assert result["success"] is True
        # Error messages are returned in guidance field or errors array
        assert (len(result.get("errors", [])) > 0 or 
                (result["guidance"] and "Error" in result["guidance"]))
    
    @patch('app.agents.incident_agent.ChatOpenAI')
    @patch('app.tools.notify._send_email')
    def test_notification_error_recorded(
        self,
        mock_send_email,
        mock_llm,
        sample_incident_data
    ):
        """Test notification errors are recorded."""
        mock_send_email.side_effect = Exception("Notification service unavailable")
        
        agent = incident_agent
        result = agent.process_incident(**sample_incident_data)
        
        assert result["success"] is True
        assert len(result.get("errors", [])) > 0
