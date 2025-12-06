"""Tests for structured logging functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.logging import AgentLogger


class AsyncContextManager:
    """Helper for async context manager mocking."""
    def __init__(self, return_value):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, *args):
        return None


@pytest.fixture
def mock_pool():
    """Mock asyncpg connection pool."""
    pool = MagicMock()
    conn = AsyncMock()
    
    # Make pool.acquire() return an async context manager
    def acquire_side_effect():
        return AsyncContextManager(conn)
    
    pool.acquire = MagicMock(side_effect=acquire_side_effect)
    
    return pool, conn


@pytest.mark.asyncio
class TestAgentLogger:
    """Test suite for AgentLogger class."""
    
    async def test_init_pool(self):
        """Test database pool initialization."""
        logger = AgentLogger()
        assert logger.pool is None
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            await logger.init_pool()
            
            assert logger.pool is not None
            mock_create_pool.assert_called_once()
    
    async def test_close_pool(self):
        """Test closing database pool."""
        logger = AgentLogger()
        mock_pool = AsyncMock()
        logger.pool = mock_pool
        
        await logger.close_pool()
        
        mock_pool.close.assert_called_once()
        assert logger.pool is None
    
    async def test_log_step_success(self, mock_pool):
        """Test logging a successful step."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        await logger.log_step(
            incident_id="INC-001",
            step_name="classify",
            step_order=1,
            status="completed",
            input_data={"type": "water_pollution"},
            output_data={"severity": "high"},
            duration_ms=150
        )
        
        conn.execute.assert_called_once()
        args = conn.execute.call_args[0]
        assert "INSERT INTO execution_logs" in args[0]
        assert args[1] == "INC-001"
        assert args[2] == "classify"
        assert args[3] == 1
        assert args[4] == "completed"
    
    async def test_log_step_with_error(self, mock_pool):
        """Test logging a failed step with error message."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        await logger.log_step(
            incident_id="INC-002",
            step_name="spatial",
            step_order=2,
            status="failed",
            error_message="Database connection timeout",
            duration_ms=5000
        )
        
        conn.execute.assert_called_once()
        args = conn.execute.call_args[0]
        assert args[7] == "Database connection timeout"
    
    async def test_update_incident_status(self, mock_pool):
        """Test updating incident status."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        await logger.update_incident_status(
            incident_id="INC-003",
            status="completed",
            agent_actions={"notifications_sent": True}
        )
        
        conn.execute.assert_called_once()
        args = conn.execute.call_args[0]
        assert "UPDATE incidents" in args[0]
        assert args[1] == "completed"
        assert args[3] == "INC-003"
    
    async def test_log_incident_creation(self, mock_pool):
        """Test logging initial incident creation."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        form_data = {
            "incident_type": "air_pollution",
            "location": "Manchester",
            "description": "Industrial emissions"
        }
        
        await logger.log_incident_creation(
            incident_id="INC-004",
            form_data=form_data,
            classification={"severity": "medium"},
            severity="medium"
        )
        
        conn.execute.assert_called_once()
        args = conn.execute.call_args[0]
        assert "INSERT INTO incidents" in args[0]
        assert args[1] == "INC-004"
    
    async def test_get_incident_logs(self, mock_pool):
        """Test retrieving incident logs."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        mock_rows = [
            {
                'id': 1,
                'incident_id': 'INC-005',
                'step_name': 'classify',
                'step_order': 1,
                'status': 'completed',
                'duration_ms': 120
            },
            {
                'id': 2,
                'incident_id': 'INC-005',
                'step_name': 'spatial',
                'step_order': 2,
                'status': 'completed',
                'duration_ms': 250
            }
        ]
        conn.fetch.return_value = mock_rows
        
        logs = await logger.get_incident_logs("INC-005")
        
        assert len(logs) == 2
        assert logs[0]['step_name'] == 'classify'
        assert logs[1]['step_name'] == 'spatial'
        conn.fetch.assert_called_once()
    
    async def test_get_dashboard_summary(self, mock_pool):
        """Test retrieving dashboard summary."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        mock_summary = {
            'total_incidents': 100,
            'p1_incidents': 5,
            'p2_incidents': 15,
            'completed': 80,
            'avg_processing_ms': 2500
        }
        conn.fetchrow.return_value = mock_summary
        
        summary = await logger.get_dashboard_summary()
        
        assert summary['total_incidents'] == 100
        assert summary['p1_incidents'] == 5
        assert summary['completed'] == 80
        conn.fetchrow.assert_called_once()
    
    async def test_get_recent_incidents(self, mock_pool):
        """Test retrieving recent incidents."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        mock_incidents = [
            {
                'incident_id': 'INC-006',
                'incident_type': 'water_pollution',
                'severity': 'high',
                'status': 'completed'
            },
            {
                'incident_id': 'INC-007',
                'incident_type': 'illegal_dumping',
                'severity': 'medium',
                'status': 'processing'
            }
        ]
        conn.fetch.return_value = mock_incidents
        
        incidents = await logger.get_recent_incidents(limit=50)
        
        assert len(incidents) == 2
        assert incidents[0]['incident_id'] == 'INC-006'
        conn.fetch.assert_called_once()
    
    async def test_get_hourly_metrics(self, mock_pool):
        """Test retrieving hourly metrics."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        mock_metrics = [
            {
                'hour': '2025-12-06 14:00:00',
                'total': 10,
                'p1': 1,
                'p2': 3,
                'avg_time_ms': 2000
            },
            {
                'hour': '2025-12-06 13:00:00',
                'total': 8,
                'p1': 0,
                'p2': 2,
                'avg_time_ms': 1800
            }
        ]
        conn.fetch.return_value = mock_metrics
        
        metrics = await logger.get_hourly_metrics(hours=24)
        
        assert len(metrics) == 2
        assert metrics[0]['total'] == 10
        conn.fetch.assert_called_once()
    
    async def test_handles_database_errors_gracefully(self, mock_pool):
        """Test that database errors are handled gracefully."""
        pool, conn = mock_pool
        logger = AgentLogger()
        logger.pool = pool
        
        # Simulate database error
        conn.execute.side_effect = Exception("Database connection failed")
        
        # Should not raise exception
        await logger.log_step(
            incident_id="INC-008",
            step_name="classify",
            step_order=1,
            status="started"
        )
        
        # Verify error was logged but didn't crash
        conn.execute.assert_called_once()
