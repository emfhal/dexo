"""
src/security/security_test.py
────────────────────────────
Tests for JWT and RBAC.
"""
from __future__ import annotations

import pytest
from jose import jwt

from src.config import SecurityConfig
from src.security.jwt import JWTService

def test_jwt_creation_and_verification() -> None:
    config = SecurityConfig(JWT_SECRET_KEY="test-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30)
    service = JWTService(config)
    
    token = service.create_access_token(subject="user123", roles=["admin"])
    assert token is not None
    
    payload = service.verify_token(token)
    assert payload is not None
    assert payload.sub == "user123"
    assert "admin" in payload.roles

def test_jwt_invalid_token() -> None:
    config = SecurityConfig(JWT_SECRET_KEY="test-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30)
    service = JWTService(config)
    with pytest.raises(Exception):
        service.verify_token("invalid.token.here")
