"""
Rate limiting middleware and utilities
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# In-memory store of {key: [(timestamp, count), ...]}
_rate_limit_store: Dict[str, list[float]] = defaultdict(list)

# Rate limit configuration by endpoint pattern
RATE_LIMITS = {
    "/jobs/ingest": {"requests": 5, "window": 3600, "key_type": "api_key"},  # 5 per hour per API key
    "/analysis": {"requests": 30, "window": 60, "key_type": "ip"},  # 30 per minute per IP
    "/apps/search": {"requests": 60, "window": 60, "key_type": "ip"},  # 60 per minute per IP
    "/compare": {"requests": 20, "window": 60, "key_type": "ip"},  # 20 per minute per IP
}


class RateLimiter:
    """Rate limiter using sliding window algorithm"""
    
    @staticmethod
    def get_key(request: Request, key_type: str = "ip") -> str:
        """Get rate limit key from request"""
        if key_type == "api_key":
            # Extract API key from Authorization header
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                return f"api_key:{auth_header[7:]}"
            return "api_key:anonymous"
        else:
            # Use client IP
            client_ip = request.client.host if request.client else "0.0.0.0"
            return f"ip:{client_ip}"
    
    @staticmethod
    def is_rate_limited(
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, dict]:
        """
        Check if request exceeds rate limit.
        
        Returns:
            (is_limited, info_dict) where info_dict contains:
                - requests_remaining: int
                - reset_at: datetime
        """
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds
        
        # Get requests in current window
        if key not in _rate_limit_store:
            _rate_limit_store[key] = []
        
        # Remove old requests outside window
        _rate_limit_store[key] = [
            ts for ts in _rate_limit_store[key]
            if ts > window_start
        ]
        
        current_count = len(_rate_limit_store[key])
        is_limited = current_count >= max_requests
        
        # Calculate reset time (when oldest request in window expires)
        if _rate_limit_store[key]:
            oldest_request = min(_rate_limit_store[key])
            reset_at = oldest_request + window_seconds
        else:
            reset_at = now + window_seconds
        
        # Record this request if not already limited
        if not is_limited:
            _rate_limit_store[key].append(now)
        
        return is_limited, {
            "requests_remaining": max(0, max_requests - current_count - (0 if is_limited else 1)),
            "reset_at": datetime.utcfromtimestamp(reset_at),
            "retry_after": int(reset_at - now + 1) if is_limited else None
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Check rate limits before processing request"""
        
        # Find matching rate limit config
        matching_config = None
        for pattern, config in RATE_LIMITS.items():
            if request.url.path.startswith(pattern):
                matching_config = config
                break
        
        # No limit configured for this endpoint
        if not matching_config:
            return await call_next(request)
        
        # Skip rate limit for GET requests (non-idempotent check)
        # Rate limit on POST/PUT/DELETE
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)
        
        # Check rate limit
        key = RateLimiter.get_key(request, matching_config["key_type"])
        is_limited, info = RateLimiter.is_rate_limited(
            key,
            matching_config["requests"],
            matching_config["window"]
        )
        
        if is_limited:
            retry_after = info["retry_after"]
            logger.warning(f"Rate limit exceeded for {key}: {retry_after}s until reset")
            
            # Return 429 Too Many Requests
            response = Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json"
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["RateLimit-Limit"] = str(matching_config["requests"])
            response.headers["RateLimit-Remaining"] = str(info["requests_remaining"])
            response.headers["RateLimit-Reset"] = info["reset_at"].isoformat()
            return response
        
        # Request allowed - process normally
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["RateLimit-Limit"] = str(matching_config["requests"])
        response.headers["RateLimit-Remaining"] = str(info["requests_remaining"])
        response.headers["RateLimit-Reset"] = info["reset_at"].isoformat()
        
        return response


def check_rate_limit(request: Request, endpoint: str) -> None:
    """
    Synchronous rate limit check for endpoint.
    Raises HTTPException 429 if rate limited.
    """
    config = RATE_LIMITS.get(endpoint)
    if not config:
        return
    
    key = RateLimiter.get_key(request, config["key_type"])
    is_limited, info = RateLimiter.is_rate_limited(
        key,
        config["requests"],
        config["window"]
    )
    
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={
                "Retry-After": str(info["retry_after"]),
                "RateLimit-Limit": str(config["requests"]),
                "RateLimit-Remaining": "0",
                "RateLimit-Reset": info["reset_at"].isoformat()
            }
        )
