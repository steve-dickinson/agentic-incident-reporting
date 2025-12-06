"""GOV.UK Notify integration for email notifications."""

from langchain.tools import BaseTool
from typing import Any
import logging

try:
    from notifications_python_client.notifications import NotificationsAPIClient
except ImportError:
    NotificationsAPIClient = None

from app.models.config import settings

logger = logging.getLogger(__name__)


class SendNotificationTool(BaseTool):
    """Sends email notifications via GOV.UK Notify."""
    
    name: str = "send_notification"
    description: str = "Sends email notifications to acknowledge incident reports or alert teams."
    
    test_mode: bool = True
    client: Any | None = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.test_mode = settings.notify_test_mode
        
        if NotificationsAPIClient and settings.notify_api_key:
            try:
                self.client = NotificationsAPIClient(settings.notify_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Notify client: {e}")
                self.client = None
        else:
            self.client = None
            logger.info("Running in test mode - notifications will be logged only")
    
    def _run(
        self,
        incident_id: str,
        incident_type: str,
        severity: str,
        message_type: str = "acknowledgment",
        recipient_email: str | None = None
    ) -> dict[str, Any]:
        results = {
            "sent": [],
            "failed": [],
            "test_mode": self.test_mode or self.client is None
        }
        
        personalisation = {
            "incident_id": incident_id,
            "incident_type": incident_type.replace("_", " ").title(),
            "severity": severity.upper()
        }
        
        if recipient_email:
            email_result = self._send_email(
                recipient_email,
                message_type,
                personalisation
            )
            if email_result["success"]:
                results["sent"].append(f"email to {recipient_email}")
            else:
                results["failed"].append(f"email to {recipient_email}: {email_result['error']}")
        else:
            logger.info(f"No email address provided for incident {incident_id}")
        
        return results
    
    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async execution not supported")
    
    def _send_email(
        self,
        email_address: str,
        message_type: str,
        personalisation: dict[str, str]
    ) -> dict[str, Any]:
        if self.test_mode or self.client is None:
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
            # Use template ID from settings or default
            template_id = settings.notify_email_template_id
            
            if not template_id:
                logger.warning("No email template ID configured")
                return {"success": False, "error": "No template configured"}
            
            response = self.client.send_email_notification(
                email_address=email_address,
                template_id=template_id,
                personalisation=personalisation
            )
            
            return {
                "success": True,
                "notification_id": response["id"],
                "reference": response.get("reference")
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}


send_notification_tool = SendNotificationTool()
