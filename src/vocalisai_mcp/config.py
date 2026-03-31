"""
Configuration management — all values come from environment variables.
No secrets are hardcoded here. See .env.example for the full list.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables (with .env fallback).

    All sensitive values (api_key) are typed as SecretStr so they are never
    accidentally serialized or logged.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── VocalisAI Platform ────────────────────────────────────────────────────
    vocalisai_base_url: str = Field(
        default="",
        description="Production Cloud Run base URL",
    )
    vocalisai_api_key: SecretStr | None = Field(
        default=None,
        description="API key for authenticated endpoints (optional)",
    )
    vocalisai_request_timeout: float = Field(
        default=15.0,
        gt=0,
        description="HTTP client timeout in seconds",
    )

    # ── MCP Transport ─────────────────────────────────────────────────────────
    mcp_transport: str = Field(
        default="stdio",
        description="Transport mode: 'stdio' or 'http'",
    )
    mcp_port: int = Field(
        default=8001,
        ge=1024,
        le=65535,
        description="Port for HTTP transport mode",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Python logging level",
    )


# Singleton — imported by all modules
settings = Settings()
