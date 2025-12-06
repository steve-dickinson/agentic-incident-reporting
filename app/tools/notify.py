"""GOV.UK Notify integration for email notifications."""

from langchain_core.tools import tool
import logging

try:
    from notifications_python_client.notifications import NotificationsAPIClient
except ImportError:
    NotificationsAPIClient = None

from app.models.config import settings

logger = logging.getLogger(__name__)


# Global client initialization
_notify_client = None
_test_mode = True

try:
    if NotificationsAPIClient and settings.notify_api_key:
        _notify_client = NotificationsAPIClient(settings.notify_api_key)
        _test_mode = settings.notify_test_mode
    else:
        logger.info("Running in test mode - notifications will be logged only")
except Exception as e:
    logger.warning(f"Failed to initialize Notify client: {e}")


def _send_email(
    email_address: str,
    message_type: str,
    personalisation: dict[str, str]
) -> dict[str, str | bool]:
    """Send email notification via GOV.UK Notify or log in test mode."""
    if _test_mode or _notify_client is None:
        logger.info(
            f"[TEST MODE] Would send {message_type} email to {email_address} "
            f"for incident {personalisation['incident_id']}"
        )
        return {
            "success": True,
            "notification_id": f"test-email-{personalisation['incident_id']}",
            "test_mode": True
        }
    
    try:
        template_id = settings.notify_email_template_id
        
        if not template_id:
            logger.warning("No email template ID configured")
            return {"success": False, "error": "No template configured"}
        
        response = _notify_client.send_email_notification(
            email_address=email_address,
            template_id=template_id,
            personalisation=personalisation
        )
        
        return {
            "success": True,
            "notification_id": response["id"],
            "reference": response.get("reference", "")
        }
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"success": False, "error": str(e)}


@tool
def send_notification_tool(
    incident_id: str,
    incident_type: str,
    severity: str,
    message_type: str = "acknowledgment",
    recipient_email: str | None = None
) -> dict[str, list[str] | bool]:
    """Sends email notifications to acknowledge incident reports or alert teams.
    
    Args:
        incident_id: Unique identifier for the incident
        incident_type: Type of environmental incident
        severity: Severity level of the incident
        message_type: Type of message to send (default: acknowledgment)
        recipient_email: Email address to send notification to
        
    Returns:
        Dictionary with sent/failed lists and test_mode flag
    """
    results = {
        "sent": [],
        "failed": [],
        "test_mode": _test_mode or _notify_client is None
    }
    
    personalisation = {
        "incident_id": incident_id,
        "incident_type": incident_type.replace("_", " ").title(),
        "severity": severity.upper()
    }
    
    if recipient_email:
        email_result = _send_email(
            recipient_email,
            message_type,
            personalisation
        )
        if email_result.get("success"):
            results["sent"].append(f"email to {recipient_email}")
        else:
            results["failed"].append(f"email to {recipient_email}: {email_result.get('error', 'Unknown error')}")
    else:
        logger.info(f"No email address provided for incident {incident_id}")
    
    return results

