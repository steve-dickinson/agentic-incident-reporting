"""Rate limiting middleware for API protection."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    For production, use Redis-backed rate limiting (e.g., slowapi or fastapi-limiter)
    to work across multiple server instances.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        super().__init__(app)
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        
        # Track requests: {client_ip: [timestamp, timestamp, ...]}
        self.minute_requests: Dict[str, List[datetime]] = defaultdict(list)
        self.hour_requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def _clean_old_requests(self, client_ip: str, now: datetime):
        """Remove requests older than the time windows."""
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)
        
        self.minute_requests[client_ip] = [
            req_time for req_time in self.minute_requests[client_ip]
            if req_time > one_minute_ago
        ]
        
        self.hour_requests[client_ip] = [
            req_time for req_time in self.hour_requests[client_ip]
            if req_time > one_hour_ago
        ]
    
    def _check_rate_limit(self, client_ip: str, now: datetime) -> bool:
        """Check if client has exceeded rate limits."""
        # Clean old requests first
        self._clean_old_requests(client_ip, now)
        
        # Check per-minute limit
        if len(self.minute_requests[client_ip]) >= self.rpm_limit:
            return False
        
        # Check per-hour limit
        if len(self.hour_requests[client_ip]) >= self.rph_limit:
            return False
        
        return True
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str, now: datetime):
        """Add rate limit information to response headers."""
        self._clean_old_requests(client_ip, now)
        
        minute_remaining = max(0, self.rpm_limit - len(self.minute_requests[client_ip]))
        hour_remaining = max(0, self.rph_limit - len(self.hour_requests[client_ip]))
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.rpm_limit)
        response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.rph_limit)
        response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Check rate limit and process request."""
        # Get client IP (consider X-Forwarded-For if behind proxy)
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            # Use first IP in chain (real client)
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        now = datetime.now()
        
        # Check rate limit
        if not self._check_rate_limit(client_ip, now):
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.rpm_limit} requests per minute or {self.rph_limit} requests per hour",
                    "retry_after": 60  # seconds
                }
            )
        
        # Record this request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, client_ip, now)
        
        return response


# Production-ready Redis-based rate limiting (requires Redis)
"""
For production, use this instead:

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# In main.py:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On endpoints:
@app.post("/submit-incident")
@limiter.limit("10/minute")
async def submit_incident(request: Request, ...):
    pass
"""
