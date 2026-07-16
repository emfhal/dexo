"""
src/providers/gemini.py
──────────────────────────
Google Gemini provider adapter.
Supports both Google AI Studio (API key) and Vertex AI (project + location).
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from src.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Supports: gemini-2.0-flash, gemini-2.5-pro, gemini-2.5-flash …

    Authentication:
    - Google AI Studio: set GEMINI_API_KEY
    - Vertex AI: set GEMINI_PROJECT_ID + GEMINI_LOCATION (uses ADC)
    """

    def __init__(
        self,
        api_key: str,
        project_id: str = "",
        location: str = "us-central1",
    ) -> None:
        self._api_key = api_key
        self._project_id = project_id
        self._location = location

        if project_id:
            logger.info("Gemini: using Vertex AI (project=%s, location=%s)", project_id, location)
        else:
            logger.info("Gemini: using AI Studio (API key)")

    @property
    def name(self) -> str:
        return "gemini"

    def build(self, model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
        base_kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "convert_system_message_to_human": True,  # Gemini quirk
            **kwargs,
        }

        if self._project_id:
            # Vertex AI — no API key needed (uses Application Default Credentials)
            return ChatGoogleGenerativeAI(
                **base_kwargs,
                project=self._project_id,
                location=self._location,
            )

        # Google AI Studio
        return ChatGoogleGenerativeAI(
            google_api_key=self._api_key,
            **base_kwargs,
        )

    def supports_model(self, model: str) -> bool:
        return model.startswith("gemini")
