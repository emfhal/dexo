"""
src/conftest.py
──────────────────
Shared pytest fixtures for all test modules.
"""
from __future__ import annotations

import os
import pytest
from langchain_core.messages import HumanMessage

from src.graph.state import AgentState, AuthContext, Permission


@pytest.fixture(autouse=True)
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-12345")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/testdb")
    monkeypatch.setenv("ASSETS_DIR", "src/assets")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

@pytest.fixture
def mock_auth() -> AuthContext:
    return AuthContext(
        user_id="test-user-123",
        session_id="test-session-abc",
        permissions=[
            Permission(role="developer", scopes=["src:read", "src:write", "tool:fetch_website"])
        ],
    )


@pytest.fixture
def base_state(mock_auth: AuthContext) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content="What is the capital of France?")],
        thread_id="test-thread-001",
        raw_token="test.token.here",
        auth=mock_auth,
    )
