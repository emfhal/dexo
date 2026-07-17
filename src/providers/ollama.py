"""
src/providers/ollama.py
──────────────────────────
Ollama provider adapter — runs models locally.
Supports: gemma3:27b, gemma3:12b, llama3.2, mistral, qwen2.5-coder …

Ollama must be running: `ollama serve`
Pull a model first: `ollama pull gemma4:27b`
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx
from langchain_ollama import ChatOllama

from src.providers.base import LLMProvider

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Local Ollama provider.

    Key settings:
    - base_url:    Ollama server (default: http://localhost:11434)
    - keep_alive:  How long to keep model hot in VRAM (e.g. "5m", "1h", "-1" = forever)
    - num_ctx:     Context window size (max depends on model)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        keep_alive: str = "5m",
        num_ctx: int = 32768,
    ) -> None:
        self._base_url = base_url
        self._keep_alive = keep_alive
        self._num_ctx = num_ctx

    @property
    def name(self) -> str:
        return "ollama"

    def build(self, model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
        return ChatOllama(
            model=model,
            base_url=self._base_url,
            temperature=temperature,
            keep_alive=self._keep_alive,
            num_ctx=self._num_ctx,
            **kwargs,
        )

    def supports_model(self, model: str) -> bool:
        """
        Checks if the model is available in the local Ollama instance.
        Falls back to True (optimistic) if Ollama is unreachable.
        """
        try:
            response = httpx.get(f"{self._base_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                available = [m["name"] for m in response.json().get("models", [])]
                # Ollama tags include digest suffix: "gemma3:27b:latest"
                return any(model in tag for tag in available)
        except Exception:
            logger.warning(
                "Ollama unreachable at %s — assuming model is available.", self._base_url
            )
        return True

    def is_healthy(self) -> bool:
        """Returns True if the Ollama server is running."""
        try:
            return httpx.get(f"{self._base_url}/", timeout=2.0).status_code == 200
        except Exception:
            return False
