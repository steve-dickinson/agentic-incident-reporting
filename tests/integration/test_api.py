"""Integration tests for API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.api.main import app


@pytest.mark.api
class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_root_endpoint(self, api_client):
        """Test root endpoint returns service info."""
        response = api_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "Defra AI Agent API"
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_check_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "defra-ai-agent"


@pytest.mark.api
class TestIncidentSubmissionEndpoint:
    """Tests for incident submission endpoint."""
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_submit_incident_success(self, mock_process, api_client):
        """Test successful incident submission."""
        mock_process.return_value = {
            "success": True,
            "incident_id": "INC-TEST-001",
            "severity": "high",
            "priority": "P2 - Urgent Response (within 4 hours)",
            "classification": {"category": "water_pollution"},
            "actions": ["Alert Environment Agency"],
            "spatial_context": {"protected_sites": "None found"},
            "guidance": "Follow water pollution protocol",
            "notifications": {"sent": ["email"], "failed": []},
            "errors": []
        }
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "water_pollution",
                "location": "River Thames",
                "latitude": 51.5007,
                "longitude": -0.1246,
                "description": "Oil spill in river",
                "reporter_email": "test@example.com",
                "urgency": "high"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "incident_id" in data
        assert data["severity"] == "high"
        assert "P2" in data["priority"]
        assert isinstance(data["actions"], list)
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_submit_incident_minimal_data(self, mock_process, api_client):
        """Test incident submission with minimal required data."""
        mock_process.return_value = {
            "success": True,
            "incident_id": "INC-TEST-002",
            "severity": "medium",
            "priority": "P3",
            "classification": {},
            "actions": [],
            "spatial_context": None,
            "guidance": None,
            "notifications": {},
            "errors": []
        }
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "noise_pollution",
                "location": "Manchester",
                "description": "Loud music"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_submit_incident_missing_required_fields(self, api_client):
        """Test incident submission fails with missing required fields."""
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "water_pollution"
                # Missing location and description
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_submit_incident_with_all_fields(self, mock_process, api_client):
        """Test incident submission with all optional fields."""
        mock_process.return_value = {
            "success": True,
            "incident_id": "INC-TEST-003",
            "severity": "critical",
            "priority": "P1",
            "classification": {},
            "actions": [],
            "spatial_context": {},
            "guidance": "",
            "notifications": {},
            "errors": []
        }
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "water_pollution",
                "location": "River Thames near Reading",
                "latitude": 51.4543,
                "longitude": -0.9781,
                "description": "Major oil spill",
                "reporter_name": "John Doe",
                "reporter_email": "john@example.com",
                "reporter_phone": "+44 20 7946 0958",
                "urgency": "critical",
                "images": ["https://example.com/image1.jpg"],
                "additional_info": {"source": "aerial survey"}
            }
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_submit_incident_processing_errors(self, mock_process, api_client):
        """Test incident submission when processing has errors."""
        mock_process.return_value = {
            "success": True,
            "incident_id": "INC-TEST-004",
            "severity": "medium",
            "priority": "P3",
            "classification": {},
            "actions": [],
            "spatial_context": {},
            "guidance": None,
            "notifications": {},
            "errors": ["Spatial query failed", "Guidance search failed"]
        }
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "illegal_dumping",
                "location": "Industrial Estate",
                "description": "Waste dumped"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["errors"]) > 0
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_submit_incident_agent_exception(self, mock_process, api_client):
        """Test incident submission handles agent exceptions."""
        mock_process.side_effect = Exception("Agent processing failed")
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "air_pollution",
                "location": "Birmingham",
                "description": "Smoke from factory"
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_incident_id_format(self, mock_process, api_client):
        """Test incident ID is generated correctly."""
        mock_process.return_value = {
            "success": True,
            "incident_id": "INC-20251206-123456",
            "severity": "low",
            "priority": "P4",
            "classification": {},
            "actions": [],
            "spatial_context": {},
            "guidance": "",
            "notifications": {},
            "errors": []
        }
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "noise_pollution",
                "location": "London",
                "description": "Construction noise"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"].startswith("INC-")
        assert "-" in data["incident_id"]
    
    def test_submit_incident_invalid_json(self, api_client):
        """Test incident submission with invalid JSON."""
        response = api_client.post(
            "/api/v1/incidents/submit",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_response_includes_timestamp(self, mock_process, api_client):
        """Test response includes timestamp."""
        mock_process.return_value = {
            "success": True,
            "incident_id": "INC-TEST",
            "severity": "medium",
            "priority": "P3",
            "classification": {},
            "actions": [],
            "spatial_context": {},
            "guidance": "",
            "notifications": {},
            "errors": []
        }
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "water_pollution",
                "location": "Test",
                "description": "Test incident"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO format


@pytest.mark.api
class TestIncidentRetrievalEndpoint:
    """Tests for incident retrieval endpoint."""
    
    def test_get_incident_not_implemented(self, api_client):
        """Test get incident endpoint returns not implemented message."""
        response = api_client.get("/api/v1/incidents/INC-TEST-001")
        
        assert response.status_code == 200
        data = response.json()
        assert "not yet implemented" in data["message"].lower()


@pytest.mark.api
class TestCORSHeaders:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, api_client):
        """Test CORS headers are present in responses."""
        response = api_client.options(
            "/api/v1/incidents/submit",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert "access-control-allow-origin" in response.headers


@pytest.mark.api
class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_not_found(self, api_client):
        """Test 404 response for non-existent endpoint."""
        response = api_client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
    
    @patch('app.api.main.incident_agent.process_incident')
    def test_general_exception_handler(self, mock_process, api_client):
        """Test general exception handler."""
        mock_process.side_effect = RuntimeError("Unexpected error")
        
        response = api_client.post(
            "/api/v1/incidents/submit",
            json={
                "incident_type": "water_pollution",
                "location": "Test",
                "description": "Test"
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "timestamp" in data
