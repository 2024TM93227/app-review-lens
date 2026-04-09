"""
Unit tests for app/security.py
Tests authentication and authorization
"""
import pytest
from fastapi import HTTPException
from unittest.mock import patch
from app.security import verify_auth


@pytest.mark.asyncio
async def test_verify_auth_disabled_by_default():
    """When ENABLE_AUTH is false, verify_auth returns 'anonymous'"""
    with patch.dict('os.environ', {'ENABLE_AUTH': 'false'}):
        result = await verify_auth(authorization='Bearer test-key')
        assert result == 'anonymous'


@pytest.mark.asyncio
async def test_verify_auth_missing_header_when_enabled():
    """When auth is enabled and header is missing, returns 401"""
    with patch.dict('os.environ', {'ENABLE_AUTH': 'true'}):
        with pytest.raises(HTTPException) as exc_info:
            await verify_auth(authorization=None)
        assert exc_info.value.status_code == 401
        assert 'Missing Authorization header' in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_auth_invalid_format():
    """When Authorization header format is invalid, returns 401"""
    with patch.dict('os.environ', {'ENABLE_AUTH': 'true'}):
        with pytest.raises(HTTPException) as exc_info:
            await verify_auth(authorization='InvalidFormat')
        assert exc_info.value.status_code == 401
        assert 'Invalid Authorization format' in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_auth_valid_token():
    """When valid token is provided, returns truncated key"""
    env = {'ENABLE_AUTH': 'true', 'API_KEY': 'demo-key'}
    with patch.dict('os.environ', env):
        result = await verify_auth(authorization='Bearer demo-key')
        assert result == 'demo'  # First 16 chars of 'demo-key'


@pytest.mark.asyncio
async def test_verify_auth_invalid_token():
    """When invalid token is provided, returns 401"""
    env = {'ENABLE_AUTH': 'true', 'API_KEY': 'valid-key'}
    with patch.dict('os.environ', env):
        with pytest.raises(HTTPException) as exc_info:
            await verify_auth(authorization='Bearer invalid-key')
        assert exc_info.value.status_code == 401
