"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import tempfile
import json

from fastapi.testclient import TestClient
from neo4j import GraphDatabase
import psycopg2


@pytest.fixture
def sample_incident_data():
    """Sample incident data for testing."""
    return {
        "incident_id": "INC-TEST-001",
        "incident_type": "water_pollution",
        "description": "Oil spill observed in river near protected marshes",
        "location": "River Thames, London",
        "latitude": 51.5007,
        "longitude": -0.1246,
        "reporter_email": "test@example.com",
        "urgency": "high"
    }


@pytest.fixture
def critical_incident_data():
    """Critical severity incident data."""
    return {
        "incident_id": "INC-TEST-002",
        "incident_type": "water_pollution",
        "description": "Toxic chemical spill near drinking water source, immediate danger to public",
        "location": "Thames Water Treatment Plant",
        "latitude": 51.4875,
        "longitude": -0.1687,
        "reporter_email": "emergency@example.com",
        "urgency": "critical"
    }


@pytest.fixture
def low_severity_incident_data():
    """Low severity incident data."""
    return {
        "incident_id": "INC-TEST-003",
        "incident_type": "noise_pollution",
        "description": "Minor noise from construction site",
        "location": "Commercial area, Manchester",
        "latitude": 53.4808,
        "longitude": -2.2426,
        "reporter_email": "resident@example.com",
        "urgency": "low"
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4-turbo",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a test response"
            },
            "finish_reason": "stop"
        }]
    }


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    mock_driver = Mock(spec=GraphDatabase.driver)
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    return mock_driver


@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection."""
    mock_conn = Mock(spec=psycopg2.extensions.connection)
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def mock_notify_client():
    """Mock GOV.UK Notify client."""
    mock_client = Mock()
    mock_client.send_email_notification.return_value = {
        "id": "test-notification-id",
        "reference": "test-ref",
        "uri": "https://api.notifications.service.gov.uk/test"
    }
    return mock_client


@pytest.fixture
def temp_guidance_dir():
    """Temporary directory with test guidance documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # Create test guidance document
        guidance_file = temp_path / "test_guidance.md"
        guidance_file.write_text("""
# Test Environmental Guidance

## Water Pollution Response

When responding to water pollution incidents:

1. Assess the severity of the pollution
2. Identify the source if possible
3. Check for nearby protected sites
4. Alert relevant authorities
5. Document evidence for investigation

## Protected Sites

Sites of Special Scientific Interest (SSSI) require special consideration.
Any pollution affecting an SSSI must be reported immediately.
        """.strip())
        
        yield temp_path


@pytest.fixture
def sample_protected_site():
    """Sample protected site data."""
    return {
        "name": "Test Marshes SSSI",
        "designation": "SSSI",
        "latitude": 51.5100,
        "longitude": -0.1300,
        "area_hectares": 250.0,
        "features": ["wetland", "bird habitat"],
        "vulnerabilities": ["water pollution", "oil spills"]
    }


@pytest.fixture
def sample_water_body():
    """Sample water body data."""
    return {
        "name": "Test River",
        "type": "river",
        "latitude": 51.5050,
        "longitude": -0.1250,
        "length_km": 45.0,
        "quality_status": "good"
    }


@pytest.fixture
def api_client():
    """FastAPI test client."""
    from app.api.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "defra_agent")
    monkeypatch.setenv("POSTGRES_USER", "defra")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    monkeypatch.setenv("NOTIFY_API_KEY", "test-notify-key")
    monkeypatch.setenv("NOTIFY_TEST_MODE", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only")


@pytest.fixture
def mock_embedding_response():
    """Mock OpenAI embedding response."""
    return [[0.1] * 1536]  # Mock 1536-dimension embedding


@pytest.fixture
def sample_search_results():
    """Sample semantic search results."""
    return [
        {
            "id": 1,
            "title": "Water Pollution Response",
            "content": "When responding to water pollution incidents, assess severity first...",
            "metadata": {"source": "guidance.md", "chunk_id": 1},
            "similarity": 0.85
        },
        {
            "id": 2,
            "title": "Protected Sites Protocol",
            "content": "Sites of Special Scientific Interest require immediate reporting...",
            "metadata": {"source": "guidance.md", "chunk_id": 2},
            "similarity": 0.72
        }
    ]
