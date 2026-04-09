"""
Structured logging utility with correlation ID support
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Context variable for correlation ID (thread-safe, async-safe)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to extract/generate correlation ID and add to response headers"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Extract X-Correlation-ID from request headers or generate new one.
        Set it in context and add to response headers.
        """
        # Try to get correlation ID from request headers
        correlation_id = request.headers.get('X-Correlation-ID')
        
        # Generate new one if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set in context (available to all code handling this request)
        set_request_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers for tracing
        response.headers['X-Correlation-ID'] = correlation_id
        
        # Log request completion
        logger_instance = logging.getLogger(__name__)
        logger_instance.info(
            json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO',
                'message': 'Request completed',
                'request_id': correlation_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code
            })
        )
        
        return response


class StructuredLogger:
    """Wrapper around Python logging that outputs structured JSON logs"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _get_request_id(self) -> str:
        """Get correlation ID from context or generate new one"""
        request_id = request_id_var.get()
        return request_id or str(uuid.uuid4())[:8]
    
    def _build_log_payload(self, message: str, level: str, **kwargs) -> str:
        """Build structured JSON log payload"""
        payload = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'request_id': self._get_request_id(),
            **kwargs
        }
        return json.dumps(payload)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured fields"""
        log_msg = self._build_log_payload(message, 'INFO', **kwargs)
        self.logger.info(log_msg)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured fields"""
        log_msg = self._build_log_payload(message, 'WARNING', **kwargs)
        self.logger.warning(log_msg)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured fields"""
        log_msg = self._build_log_payload(message, 'ERROR', **kwargs)
        self.logger.error(log_msg)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured fields"""
        log_msg = self._build_log_payload(message, 'DEBUG', **kwargs)
        self.logger.debug(log_msg)


def set_request_id(request_id: str) -> None:
    """Set correlation ID for current request context"""
    request_id_var.set(request_id)


def get_request_id() -> str:
    """Get correlation ID from context"""
    request_id = request_id_var.get()
    return request_id or str(uuid.uuid4())[:8]
