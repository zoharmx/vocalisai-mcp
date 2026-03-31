"""
VocalisAI MCP Server
====================
Model Context Protocol server for the VocalisAI multi-agent voice AI platform.

Exposes 7 production tools and 3 URI resources to any MCP-compatible LLM client
(Claude Desktop, Cursor, Cline, custom agents).

Platform: VocalisAI V3 — Google Cloud Run / ElevenLabs / Twilio
Ethics: Tikun Olam Framework (5 dimensions, hard-veto patterns)
"""

__version__ = "1.0.0"
__author__ = "Jesus Eduardo Rodriguez"
__all__ = ["__version__"]
