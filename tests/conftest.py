"""Shared pytest fixtures for VocalisAI MCP tests."""

import pytest
from vocalisai_mcp.ethics import TikunOlamEngine
from vocalisai_mcp.routing import AkivaRouter


@pytest.fixture
def engine() -> TikunOlamEngine:
    return TikunOlamEngine()


@pytest.fixture
def router() -> AkivaRouter:
    return AkivaRouter()
