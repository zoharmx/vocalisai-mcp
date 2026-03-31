"""
Async HTTP client for the VocalisAI production platform on Google Cloud Run.

Handles:
  - Authentication via optional API key header
  - Timeout and connection error handling
  - Cloud Run cold-start detection and user guidance
  - Clean error messages for MCP tool consumers
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from .config import settings

logger = logging.getLogger(__name__)


# ─── Error handler ────────────────────────────────────────────────────────────


def format_error(exc: Exception) -> str:
    """Convert httpx exceptions into clean, actionable error strings."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            return "Error: Unauthorized — check VOCALISAI_API_KEY in your environment."
        if status == 404:
            return "Error: Resource not found — verify the ID or endpoint path."
        if status == 429:
            return "Error: Rate limit reached — please wait a moment and retry."
        if status == 503:
            return (
                "Error: VocalisAI service temporarily unavailable (possible cold start). "
                "Retry in ~10 seconds."
            )
        return f"Error: API request failed with HTTP {status}."

    if isinstance(exc, httpx.TimeoutException):
        return (
            "Error: Request timed out. Cloud Run instance may be cold-starting — "
            f"retry in 10 seconds. (timeout={settings.vocalisai_request_timeout}s)"
        )

    if isinstance(exc, httpx.ConnectError):
        return (
            "Error: Could not connect to VocalisAI platform. "
            "Verify VOCALISAI_BASE_URL and network connectivity."
        )

    return f"Error: {type(exc).__name__} — {exc}"


def is_cold_start(elapsed_ms: float) -> bool:
    """Heuristic: Cloud Run cold starts typically take > 3 seconds."""
    return elapsed_ms > 3000


# ─── Client factory ───────────────────────────────────────────────────────────


@asynccontextmanager
async def get_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Async context manager yielding a configured httpx.AsyncClient.

    The client targets the VocalisAI base URL from settings, sets the API key
    header when present, and uses the configured timeout.

    Usage:
        async with get_client() as client:
            response = await client.get("/health")
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}

    api_key = settings.vocalisai_api_key
    if api_key is not None:
        headers["X-API-Key"] = api_key.get_secret_value()
        logger.debug("API key header set")

    base_url = settings.vocalisai_base_url
    if not base_url:
        raise RuntimeError(
            "VOCALISAI_BASE_URL is not set. "
            "Copy .env.example to .env and set the platform URL."
        )

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=settings.vocalisai_request_timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        logger.debug("HTTP client created | base_url=%s", base_url)
        yield client
