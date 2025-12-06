"""Custom exception classes for incident processing system."""


class IncidentProcessingError(Exception):
    """Base exception for all incident processing errors."""
    
    def __init__(self, message: str, incident_id: str | None = None, details: dict | None = None):
        self.message = message
        self.incident_id = incident_id
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "incident_id": self.incident_id,
            "details": self.details
        }


class ValidationError(IncidentProcessingError):
    """Raised when data validation fails."""
    pass


class ClassificationError(IncidentProcessingError):
    """Raised when incident classification fails."""
    pass


class SpatialQueryError(IncidentProcessingError):
    """Raised when Neo4j spatial query fails."""
    
    def __init__(self, message: str, query: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.query = query


class NotificationError(IncidentProcessingError):
    """Raised when notification delivery fails."""
    
    def __init__(self, message: str, recipient: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.recipient = recipient


class DatabaseConnectionError(IncidentProcessingError):
    """Raised when database connection fails."""
    
    def __init__(self, message: str, db_type: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.db_type = db_type


class ApprovalError(IncidentProcessingError):
    """Raised when HITL approval workflow fails."""
    pass


class WorkflowStateError(IncidentProcessingError):
    """Raised when LangGraph workflow state is invalid."""
    
    def __init__(self, message: str, state_snapshot: dict | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.state_snapshot = state_snapshot
