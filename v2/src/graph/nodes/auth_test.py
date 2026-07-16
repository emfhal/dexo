"""
src/graph/nodes/auth_test.py
───────────────────────────
Tests for the auth node.
"""
from __future__ import annotations

import pytest

from src.graph.state import AgentState
from src.graph.nodes.auth import auth_node

def test_auth_node_no_token() -> None:
    state = AgentState(raw_token="")
    with pytest.raises(PermissionError):
        auth_node(state)


def test_auth_node_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    # We will mock the security module's JWTService.verify_token
    class MockTokenClaims:
        sub = "user123"
        roles = ["admin"]
        permissions = []
        extra = {}

    monkeypatch.setattr("src.graph.nodes.auth.JWTService.verify_token", lambda self, token: MockTokenClaims())
    
    state = AgentState(raw_token="fake.token")
    result = auth_node(state)
    assert "auth" in result
    assert result["auth"].user_id == "user123"
