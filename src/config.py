"""
src/config.py
───────────────
Typed, validated configuration loaded from environment variables.
Uses pydantic-settings for full type safety, .env support, and
sub-config composition.

Provider priority (set LLM_PROVIDER):
  ollama    → local Ollama server (gemma3:27b, llama3 …)
  gemini    → Google Gemini API / Vertex AI
  openai    → OpenAI API
  anthropic → Anthropic Claude API
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from ipaddress import IPv4Network
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─────────────────────────────────────────────────────────────────────────────
#  Sub-configs
# ─────────────────────────────────────────────────────────────────────────────


from typing import Any

def _load_project_metadata() -> dict[str, Any]:
    path = Path(__file__).parent.parent / "pyproject.toml"
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {})
    return {}


_project_meta = _load_project_metadata()


class ProjectConfig(BaseSettings):
    title: str = (
        _project_meta.get("name", "dexo").capitalize() + " - Enterprise Agentic Orchestrator"
    )
    version: str = _project_meta.get("version", "2.0.0")
    description: str = _project_meta.get(
        "description", "A robust, frontier-grade multi-agent architecture."
    )
    contact_name: str = "Dexo"
    contact_url: str = "http://127.0.0.1:8081"


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Provider routing ──────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "gemini", "ollama"] = Field(
        "ollama", alias="LLM_PROVIDER"
    )
    llm_primary_model: str = Field("gemma4:27b", alias="LLM_PRIMARY_MODEL")
    llm_fallback_provider: str = Field("gemini", alias="LLM_FALLBACK_PROVIDER")
    llm_fallback_model: str = Field("gemini-2.0-flash", alias="LLM_FALLBACK_MODEL")
    temperature: float = Field(0.0, alias="LLM_TEMPERATURE", ge=0.0, le=2.0)

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")

    # ── Gemini ────────────────────────────────────────────────────────────────
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    gemini_project_id: str = Field("", alias="GEMINI_PROJECT_ID")
    gemini_location: str = Field("us-central1", alias="GEMINI_LOCATION")

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_keep_alive: str = Field("5m", alias="OLLAMA_KEEP_ALIVE")
    ollama_num_ctx: int = Field(32768, alias="OLLAMA_NUM_CTX")

    @model_validator(mode="after")
    def validate_provider_credentials(self) -> LLMConfig:
        """Ensure the selected primary provider has credentials."""
        checks = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.gemini_api_key or self.gemini_project_id,
            "ollama": True,  # No credentials needed
        }
        if not checks.get(self.llm_provider):
            raise ValueError(
                f"Provider '{self.llm_provider}' selected but credentials are missing. "
                "Set the corresponding API key in .env."
            )
        return self


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    url: PostgresDsn = Field(..., alias="DATABASE_URL")
    pool_size: int = Field(10, alias="DATABASE_POOL_SIZE", ge=1, le=100)
    max_overflow: int = Field(20, alias="DATABASE_MAX_OVERFLOW", ge=0, le=100)


class MemoryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    zep_api_url: str = Field("http://localhost:8010", alias="ZEP_API_URL")
    zep_api_key: str = Field("", alias="ZEP_API_KEY")
    mem0_api_key: str = Field("", alias="MEM0_API_KEY")
    summary_token_threshold: int = Field(8000, alias="SUMMARY_TOKEN_THRESHOLD")


class SecurityConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: Literal["HS256", "RS256"] = Field("HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")


class ObservabilityConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    otlp_endpoint: str = Field("http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name: str = Field("langgraph-src", alias="OTEL_SERVICE_NAME")
    service_version: str = Field("2.0.0", alias="OTEL_SERVICE_VERSION")
    sampler_ratio: float = Field(1.0, alias="OTEL_TRACES_SAMPLER_ARG", ge=0.0, le=1.0)


class AssetsConfig(BaseSettings):
    """
    Paths to all content assets (skills, subagents, rules, prompts, MCP).
    Maps to the assets/ directory tree.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    assets_dir: str = Field("./src/assets", alias="ASSETS_DIR")
    skills_dir: str = Field("./src/assets/skills", alias="SKILLS_DIR")
    subagents_dir: str = Field("./src/assets/subagents", alias="SUBAGENTS_DIR")
    rules_file: str = Field("./src/assets/rules/AGENTS.md", alias="RULES_FILE")
    prompts_dir: str = Field("./src/assets/prompts", alias="PROMPTS_DIR")
    mcp_servers_config: str = Field("./src/assets/mcp/servers.json", alias="MCP_SERVERS_CONFIG")
    context_token_budget: int = Field(16000, alias="CONTEXT_TOKEN_BUDGET")


class ToolConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    command_allowlist: list[str] = Field(
        default=["git", "ls", "cat", "grep", "find", "echo", "pwd", "uv", "python"],
        alias="COMMAND_ALLOWLIST",
    )
    command_require_approval: bool = Field(True, alias="COMMAND_REQUIRE_APPROVAL")
    fetch_timeout_seconds: int = Field(10, alias="FETCH_TIMEOUT_SECONDS")
    ssrf_blocked_cidrs: list[IPv4Network] = Field(
        default=[
            IPv4Network("127.0.0.0/8"),
            IPv4Network("10.0.0.0/8"),
            IPv4Network("172.16.0.0/12"),
            IPv4Network("192.168.0.0/16"),
        ],
        alias="SSRF_BLOCKED_CIDRS",
    )

    @field_validator("command_allowlist", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v

    @field_validator("ssrf_blocked_cidrs", mode="before")
    @classmethod
    def parse_cidrs(cls, v: str | list) -> list[IPv4Network]:  # type: ignore[type-arg]
        if isinstance(v, str):
            return [IPv4Network(cidr.strip()) for cidr in v.split(",")]
        return [IPv4Network(cidr) if isinstance(cidr, str) else cidr for cidr in v]


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8080, alias="PORT")
    workers: int = Field(1, ge=1, alias="WORKERS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_pretty: bool = Field(True, alias="LOG_PRETTY")
    environment: Literal["development", "staging", "production"] = Field(
        "development", alias="ENVIRONMENT"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Root settings
# ─────────────────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Root settings — composes all sub-configs."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    assets: AssetsConfig = Field(default_factory=AssetsConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings accessor — safe to call anywhere in the codebase."""
    return Settings()
