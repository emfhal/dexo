"""
src/providers/registry.py
─────────────────────────────
Provider registry: builds the correct LLMProvider from configuration
and routes model strings to their provider.

Supports automatic fallback:
  primary provider fails → fallback provider kicks in
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.providers.anthropic import AnthropicProvider
from src.providers.gemini import GeminiProvider
from src.providers.ollama import OllamaProvider
from src.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from src.config import LLMConfig
    from src.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Central factory for LLM providers.

    Usage:
        registry = ProviderRegistry.from_config(cfg)
        llm = registry.build_primary()
        fallback_llm = registry.build_fallback()
    """

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        primary_provider: str,
        primary_model: str,
        fallback_provider: str,
        fallback_model: str,
        temperature: float,
    ) -> None:
        self._providers = providers
        self._primary_provider = primary_provider
        self._primary_model = primary_model
        self._fallback_provider = fallback_provider
        self._fallback_model = fallback_model
        self._temperature = temperature

    @classmethod
    def from_config(cls, cfg: LLMConfig) -> ProviderRegistry:
        """Build all available providers from config (skips unconfigured ones)."""
        providers: dict[str, LLMProvider] = {}

        if cfg.openai_api_key:
            providers["openai"] = OpenAIProvider(api_key=cfg.openai_api_key)
            logger.debug("OpenAI provider registered.")

        if cfg.anthropic_api_key:
            providers["anthropic"] = AnthropicProvider(api_key=cfg.anthropic_api_key)
            logger.debug("Anthropic provider registered.")

        if cfg.gemini_api_key or cfg.gemini_project_id:
            providers["gemini"] = GeminiProvider(
                api_key=cfg.gemini_api_key,
                project_id=cfg.gemini_project_id,
                location=cfg.gemini_location,
            )
            logger.debug("Gemini provider registered.")

        # Ollama is always available (local, no key needed)
        providers["ollama"] = OllamaProvider(
            base_url=cfg.ollama_base_url,
            keep_alive=cfg.ollama_keep_alive,
            num_ctx=cfg.ollama_num_ctx,
        )
        logger.debug("Ollama provider registered (base_url=%s).", cfg.ollama_base_url)

        if cfg.llm_provider not in providers:
            raise ValueError(
                f"Primary provider '{cfg.llm_provider}' is not configured. "
                f"Available: {list(providers.keys())}"
            )

        logger.info(
            "ProviderRegistry ready. Primary: %s/%s | Fallback: %s/%s",
            cfg.llm_provider,
            cfg.llm_primary_model,
            cfg.llm_fallback_provider,
            cfg.llm_fallback_model,
        )

        return cls(
            providers=providers,
            primary_provider=cfg.llm_provider,
            primary_model=cfg.llm_primary_model,
            fallback_provider=cfg.llm_fallback_provider,
            fallback_model=cfg.llm_fallback_model,
            temperature=cfg.temperature,
        )

    def build_primary(self, **extra: Any) -> BaseChatModel:
        """Build the primary LLM."""
        provider = self._providers[self._primary_provider]
        return provider.build(self._primary_model, self._temperature, **extra)

    def build_fallback(self, **extra: Any) -> BaseChatModel:
        """Build the fallback LLM."""
        if self._fallback_provider not in self._providers:
            logger.warning(
                "Fallback provider '%s' not configured — using primary.", self._fallback_provider
            )
            return self.build_primary(**extra)
        provider = self._providers[self._fallback_provider]
        return provider.build(self._fallback_model, self._temperature, **extra)

    def build_for_subagent(self, manifest: dict[str, Any]) -> BaseChatModel:
        """
        Build an LLM from a subagent manifest's model definition.
        Falls back to primary if the manifest's provider is unconfigured.

        Manifest format:
          { "provider": "ollama", "model": "gemma3:27b", "temperature": 0.0 }
        """
        model_cfg = manifest.get("model", {})
        provider_name = model_cfg.get("provider", self._primary_provider)
        model = model_cfg.get("model", self._primary_model)
        temperature = model_cfg.get("temperature", self._temperature)
        options = model_cfg.get("options", {})

        if provider_name not in self._providers:
            logger.warning(
                "Subagent requested provider '%s' (not configured) — using primary.",
                provider_name,
            )
            return self.build_primary()

        return self._providers[provider_name].build(model, temperature, **options)

    @property
    def primary_info(self) -> dict[str, str]:
        return {"provider": self._primary_provider, "model": self._primary_model}

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers.keys())
