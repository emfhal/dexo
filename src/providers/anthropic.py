"""
src/providers/anthropic.py
──────────────────────────────
Anthropic / Claude provider adapter.
"""
from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from src.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Supports: claude-3-5-sonnet, claude-3-7-sonnet, claude-opus …"""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "anthropic"

    def build(self, model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=self._api_key,
            **kwargs,
        )

    def supports_model(self, model: str) -> bool:
        return model.startswith("claude")
