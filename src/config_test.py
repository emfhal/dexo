"""
src/config_test.py
─────────────────
Tests for configuration parsing and validation.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import Settings, ToolConfig


def test_default_settings() -> None:
    with (
        patch.dict(os.environ, {}, clear=True),
        patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test",
                "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db",
                "LLM_PROVIDER": "ollama",
            },
        ),
    ):
        settings = Settings()
        assert settings.llm.llm_provider == "ollama"
        assert settings.database.pool_size == 10
        assert settings.server.port == 8080


def test_invalid_provider_raises() -> None:
    with (
        patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test",
                "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db",
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "",  # Missing key should raise
            },
        ),
        pytest.raises(ValidationError),
    ):
        Settings()


def test_tool_allowlist_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMAND_ALLOWLIST", '["git", "ls"]')
    cfg = ToolConfig()
    assert cfg.command_allowlist == ["git", "ls"]
