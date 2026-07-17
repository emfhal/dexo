"""
src/providers/providers_test.py
─────────────────────────
Unit tests for the LLM provider registry.
Uses mocking — no real API calls made.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.config import LLMConfig
from src.providers.registry import ProviderRegistry


def _make_cfg(**overrides: Any) -> LLMConfig:
    """Build a minimal LLMConfig for testing."""
    defaults = {
        "LLM_PROVIDER": "ollama",
        "LLM_PRIMARY_MODEL": "gemma4:27b",
        "LLM_FALLBACK_PROVIDER": "gemini",
        "LLM_FALLBACK_MODEL": "gemini-2.0-flash",
        "LLM_TEMPERATURE": "0.0",
        "GEMINI_API_KEY": "fake-gemini-key",
        "JWT_SECRET_KEY": "test-secret",
        "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db",
    }
    defaults.update({k.upper(): str(v) for k, v in overrides.items()})
    return LLMConfig(**{alias: val for alias, val in defaults.items()})


class TestProviderRegistry:
    def test_ollama_always_registered(self) -> None:
        cfg = _make_cfg()
        registry = ProviderRegistry.from_config(cfg)
        assert "ollama" in registry.available_providers

    def test_gemini_registered_with_key(self) -> None:
        cfg = _make_cfg(GEMINI_API_KEY="fake-key")
        registry = ProviderRegistry.from_config(cfg)
        assert "gemini" in registry.available_providers

    def test_openai_registered_with_key(self) -> None:
        cfg = _make_cfg(
            LLM_PROVIDER="openai",
            LLM_PRIMARY_MODEL="gpt-4o",
            OPENAI_API_KEY="sk-fake",
        )
        registry = ProviderRegistry.from_config(cfg)
        assert "openai" in registry.available_providers

    def test_missing_provider_credentials_raises(self) -> None:
        with pytest.raises(ValueError, match="credentials are missing"):
            _make_cfg(
                LLM_PROVIDER="openai",
                LLM_PRIMARY_MODEL="gpt-4o",
                OPENAI_API_KEY="",  # missing
            )

    @patch("src.providers.ollama.ChatOllama")
    def test_build_primary_returns_model(self, mock_ollama: MagicMock) -> None:
        cfg = _make_cfg()
        registry = ProviderRegistry.from_config(cfg)
        registry.build_primary()
        mock_ollama.assert_called_once()

    @patch("src.providers.gemini.ChatGoogleGenerativeAI")
    def test_build_fallback_uses_gemini(self, mock_gemini: MagicMock) -> None:
        cfg = _make_cfg(GEMINI_API_KEY="fake-key")
        registry = ProviderRegistry.from_config(cfg)
        registry.build_fallback()
        mock_gemini.assert_called_once()

    def test_primary_info(self) -> None:
        cfg = _make_cfg()
        registry = ProviderRegistry.from_config(cfg)
        info = registry.primary_info
        assert info["provider"] == "ollama"
        assert info["model"] == "gemma4:27b"

    def test_build_for_subagent_manifest(self) -> None:
        cfg = _make_cfg()
        registry = ProviderRegistry.from_config(cfg)
        manifest = {
            "name": "coder",
            "model": {
                "provider": "ollama",
                "model": "gemma4:27b",
                "temperature": 0.0,
            },
        }
        with patch("src.providers.ollama.ChatOllama") as mock:
            registry.build_for_subagent(manifest)
            mock.assert_called_once()

    def test_build_for_subagent_unknown_provider_falls_back(self) -> None:
        """If a manifest requests an unconfigured provider, use primary."""
        cfg = _make_cfg()
        registry = ProviderRegistry.from_config(cfg)
        manifest = {"model": {"provider": "nonexistent", "model": "x"}}
        with patch("src.providers.ollama.ChatOllama"):
            registry.build_for_subagent(manifest)
