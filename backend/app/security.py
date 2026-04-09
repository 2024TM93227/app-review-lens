"""
Security module for authentication and authorization
"""
from fastapi import HTTPException, Depends, Header
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def verify_auth(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify API authentication via Authorization header.
    
    For MVP, uses simple API key validation.
    To enable: set ENABLE_AUTH=true and API_KEY=your-key
    
    Returns:
    - User identifier (API key hash or user_id)
    
    Raises:
    - HTTPException 401 if auth missing or invalid
    """
    import os
    
    # Check if auth is enabled
    enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    
    if not enable_auth:
        # Auth disabled for MVP - allow all requests
        return "anonymous"
    
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Validate API key format
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid Authorization format")
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    
    token = authorization.replace("Bearer ", "")
    expected_key = os.getenv("API_KEY", "demo-key")
    
    if token != expected_key:
        logger.warning(f"Invalid API key provided")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token[:16]  # Return truncated key for logging
