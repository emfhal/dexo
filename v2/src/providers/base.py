"""
src/providers/base.py
────────────────────────
Abstract base for all LLM provider adapters.
"""
from __future__ import annotations

import abc
from typing import Any

from langchain_core.language_models import BaseChatModel


class LLMProvider(abc.ABC):
    """
    All LLM provider adapters implement this interface.
    This decouples the graph nodes from specific provider libraries.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @abc.abstractmethod
    def build(self, model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
        """
        Instantiate and return a LangChain chat model.

        Args:
            model:       Provider-specific model identifier (e.g. "gemma3:27b")
            temperature: Sampling temperature [0.0, 2.0]
            **kwargs:    Provider-specific extra options
        """
        ...

    def supports_model(self, model: str) -> bool:
        """Optional: return True if this provider can serve `model`."""
        return True
