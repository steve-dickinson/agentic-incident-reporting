"""Unit tests for notification tool."""

import pytest
from unittest.mock import patch, Mock

from app.tools.notify import send_notification_tool, _send_email


class TestSendEmail:
    """Tests for _send_email helper function."""
    
    @patch('app.tools.notify._notify_client', None)
    @patch('app.tools.notify._test_mode', True)
    def test_send_email_test_mode(self):
        """Test email sending in test mode."""
        result = _send_email(
            "test@example.com",
            "acknowledgment",
            {
                "incident_id": "INC-TEST-001",
                "incident_type": "Water Pollution",
                "severity": "HIGH"
            }
        )
        
        assert result["success"] is True
        assert result["test_mode"] is True
        assert "test-email" in result["notification_id"]
    
    @patch('app.tools.notify._notify_client')
    @patch('app.tools.notify._test_mode', False)
    @patch('app.tools.notify.settings')
    def test_send_email_with_client(self, mock_settings, mock_client):
        """Test email sending with real client."""
        mock_settings.notify_email_template_id = "test-template-id"
        mock_client.send_email_notification.return_value = {
            "id": "notify-12345",
            "reference": "ref-67890"
        }
        
        result = _send_email(
            "test@example.com",
            "acknowledgment",
            {
                "incident_id": "INC-TEST-001",
                "incident_type": "Water Pollution",
                "severity": "HIGH"
            }
        )
        
        assert result["success"] is True
        assert result["notification_id"] == "notify-12345"
        assert result["reference"] == "ref-67890"
        
        mock_client.send_email_notification.assert_called_once()
    
    @patch('app.tools.notify._notify_client')
    @patch('app.tools.notify._test_mode', False)
    @patch('app.tools.notify.settings')
    def test_send_email_no_template(self, mock_settings, mock_client):
        """Test email sending fails without template ID."""
        mock_settings.notify_email_template_id = None
        
        result = _send_email(
            "test@example.com",
            "acknowledgment",
            {"incident_id": "INC-001", "incident_type": "Test", "severity": "HIGH"}
        )
        
        assert result["success"] is False
        assert "No template configured" in result["error"]
    
    @patch('app.tools.notify._notify_client')
    @patch('app.tools.notify._test_mode', False)
    @patch('app.tools.notify.settings')
    def test_send_email_api_error(self, mock_settings, mock_client):
        """Test email sending handles API errors."""
        mock_settings.notify_email_template_id = "test-template"
        mock_client.send_email_notification.side_effect = Exception("API Error")
        
        result = _send_email(
            "test@example.com",
            "acknowledgment",
            {"incident_id": "INC-001", "incident_type": "Test", "severity": "HIGH"}
        )
        
        assert result["success"] is False
        assert "API Error" in result["error"]


class TestSendNotificationTool:
    """Tests for send_notification_tool."""
    
    @patch('app.tools.notify._notify_client', None)
    @patch('app.tools.notify._test_mode', True)
    def test_send_notification_with_email(self):
        """Test notification tool with email address."""
        result = send_notification_tool.invoke({
            "incident_id": "INC-TEST-001",
            "incident_type": "water_pollution",
            "severity": "high",
            "message_type": "acknowledgment",
            "recipient_email": "test@example.com"
        })
        
        assert isinstance(result["sent"], list)
        assert len(result["sent"]) == 1
        assert "email to test@example.com" in result["sent"]
        assert len(result["failed"]) == 0
        assert result["test_mode"] is True
    
    @patch('app.tools.notify._notify_client', None)
    @patch('app.tools.notify._test_mode', True)
    def test_send_notification_without_email(self):
        """Test notification tool without email address."""
        result = send_notification_tool.invoke({
            "incident_id": "INC-TEST-002",
            "incident_type": "air_pollution",
            "severity": "medium",
            "message_type": "acknowledgment",
            "recipient_email": None
        })
        
        assert len(result["sent"]) == 0
        assert len(result["failed"]) == 0
        assert result["test_mode"] is True
    
    @patch('app.tools.notify._send_email')
    def test_send_notification_formats_incident_type(self, mock_send_email):
        """Test incident type is formatted correctly."""
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        send_notification_tool.invoke({
            "incident_id": "INC-003",
            "incident_type": "water_pollution",
            "severity": "high",
            "recipient_email": "test@example.com"
        })
        
        call_args = mock_send_email.call_args[0]
        personalisation = call_args[2]
        
        assert personalisation["incident_type"] == "Water Pollution"
    
    @patch('app.tools.notify._send_email')
    def test_send_notification_formats_severity(self, mock_send_email):
        """Test severity is uppercased."""
        mock_send_email.return_value = {"success": True, "test_mode": True}
        
        send_notification_tool.invoke({
            "incident_id": "INC-004",
            "incident_type": "illegal_dumping",
            "severity": "critical",
            "recipient_email": "test@example.com"
        })
        
        call_args = mock_send_email.call_args[0]
        personalisation = call_args[2]
        
        assert personalisation["severity"] == "CRITICAL"
    
    @patch('app.tools.notify._send_email')
    def test_send_notification_handles_email_failure(self, mock_send_email):
        """Test notification tool handles email sending failures."""
        mock_send_email.return_value = {
            "success": False,
            "error": "Email delivery failed"
        }
        
        result = send_notification_tool.invoke({
            "incident_id": "INC-005",
            "incident_type": "wildlife_harm",
            "severity": "high",
            "recipient_email": "invalid@example.com"
        })
        
        assert len(result["sent"]) == 0
        assert len(result["failed"]) == 1
        assert "invalid@example.com" in result["failed"][0]
        assert "Email delivery failed" in result["failed"][0]
    
    @pytest.mark.parametrize("message_type", [
        "acknowledgment",
        "alert",
        "update",
        "resolution"
    ])
    def test_send_notification_different_message_types(self, message_type):
        """Test different message types are handled."""
        with patch('app.tools.notify._send_email') as mock_send:
            mock_send.return_value = {"success": True, "test_mode": True}
            
            send_notification_tool.invoke({
                "incident_id": "INC-006",
                "incident_type": "noise_pollution",
                "severity": "low",
                "message_type": message_type,
                "recipient_email": "test@example.com"
            })
            
            call_args = mock_send.call_args[0]
            assert call_args[1] == message_type


class TestNotificationPersonalisation:
    """Tests for notification personalisation data."""
    
    @patch('app.tools.notify._send_email')
    def test_personalisation_includes_incident_id(self, mock_send_email):
        """Test personalisation includes incident ID."""
        mock_send_email.return_value = {"success": True}
        
        send_notification_tool.invoke({
            "incident_id": "INC-CUSTOM-123",
            "incident_type": "water_pollution",
            "severity": "high",
            "recipient_email": "test@example.com"
        })
        
        personalisation = mock_send_email.call_args[0][2]
        assert personalisation["incident_id"] == "INC-CUSTOM-123"
    
    @patch('app.tools.notify._send_email')
    def test_personalisation_handles_underscores(self, mock_send_email):
        """Test underscores in incident type are replaced with spaces."""
        mock_send_email.return_value = {"success": True}
        
        send_notification_tool.invoke({
            "incident_id": "INC-007",
            "incident_type": "illegal_waste_tipping",
            "severity": "medium",
            "recipient_email": "test@example.com"
        })
        
        personalisation = mock_send_email.call_args[0][2]
        assert personalisation["incident_type"] == "Illegal Waste Tipping"
