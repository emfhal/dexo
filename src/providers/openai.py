"""
src/providers/openai.py
──────────────────────────
OpenAI / Azure OpenAI provider adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_openai import ChatOpenAI

from src.providers.base import LLMProvider

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


class OpenAIProvider(LLMProvider):
    """Supports: gpt-4o, gpt-4o-mini, o1, o3-mini …"""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "openai"

    def build(self, model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=self._api_key,
            **kwargs,
        )

    def supports_model(self, model: str) -> bool:
        return any(model.startswith(prefix) for prefix in ("gpt-", "o1", "o3", "o4", "text-"))
