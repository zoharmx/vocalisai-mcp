"""
VocalisAI MCP Server — Entry Point
====================================
Exposes the VocalisAI multi-agent voice AI platform as MCP tools and resources
to any compatible LLM client (Claude Desktop, Cursor, Cline, custom agents).

Tools (7):
    vocalisai_list_agents          → Registry of all specialized agents
    vocalisai_get_agent            → Full profile for a specific agent
    vocalisai_analyze_call         → Ethical evaluation (Tikun Olam Framework)
    vocalisai_route_message        → Simulate Akiva routing logic
    vocalisai_health_check         → Ping the live Cloud Run service
    vocalisai_get_session          → Retrieve a session transcript
    vocalisai_platform_info        → Full platform capabilities overview

Resources (3 URI templates):
    vocalisai://agents/{agent_id}     → Agent profile JSON
    vocalisai://ethical-dimensions    → Tikun Olam dimension definitions
    vocalisai://platform-info         → Platform metadata

Transport:
    stdio (default) — for Claude Desktop / Cursor / Cline
    http            — for Docker / remote clients (set MCP_TRANSPORT=http)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .client import format_error, get_client, is_cold_start
from .config import settings
from .ethics import TikunOlamEngine
from .registry import AGENTS_REGISTRY, ETHICAL_DIMENSIONS, HARD_VETO_PATTERNS
from .routing import AkivaRouter

# ─── Logging (stderr only — stdout is MCP protocol channel) ──────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("vocalisai_mcp")

# ─── MCP Server ───────────────────────────────────────────────────────────────

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP  # type: ignore[no-reuse-import]

mcp = FastMCP(
    "vocalisai_mcp",
    instructions=(
        "VocalisAI MCP Server v{version} — production multi-agent voice AI platform "
        "for dental healthcare. "
        "Use these tools to inspect agents, evaluate conversations ethically (Tikun Olam), "
        "simulate intelligent routing (Akiva), retrieve session data, and check platform health. "
        "All ethical evaluations use the same 5-dimension framework running in production."
    ).format(version=__version__),
)

# ─── Shared engine/router singletons ─────────────────────────────────────────

_ethics = TikunOlamEngine()
_router = AkivaRouter()

# ─── Input Models ─────────────────────────────────────────────────────────────


class ListAgentsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_akiva: bool = Field(
        default=True,
        description="Include Akiva (meta-supervisor) in results",
    )
    role_filter: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Filter by role keyword, e.g. 'billing', 'triage', 'outbound'",
    )


class GetAgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Agent ID: alex | nova | diana | sara | marco | raul | akiva",
    )


class AnalyzeCallInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(
        ..., min_length=2, max_length=20,
        description="Which agent produced this response",
    )
    user_message: str = Field(
        ..., min_length=1, max_length=2000,
        description="The patient's incoming message",
    )
    agent_response: str = Field(
        ..., min_length=1, max_length=2000,
        description="The agent's proposed response to evaluate",
    )
    context: Optional[str] = Field(
        default=None, max_length=4000,
        description="Optional conversation context (prior turns)",
    )


class RouteMessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(
        ..., min_length=1, max_length=2000,
        description="Incoming patient message to route",
    )
    language: Optional[str] = Field(
        default=None,
        description="Language hint: 'es' | 'en' (omit for auto-detection)",
    )
    explain: bool = Field(
        default=True,
        description="Include human-readable routing explanation in response",
    )


class GetSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(
        ..., min_length=5, max_length=100,
        description="Session ID (format: session_YYYYMMDD_HHMMSS or Firestore document ID)",
    )


# ─── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool(
    name="vocalisai_list_agents",
    annotations={
        "title": "List VocalisAI Agents",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def vocalisai_list_agents(params: ListAgentsInput) -> str:
    """List all agents in the VocalisAI platform with their roles, languages, and capabilities.

    Returns the full agent registry (7 agents: Alex, Nova, Diana, Sara, Marco, Raúl, Akiva).
    Supports optional role-based filtering.

    Args:
        params: Filter options — include_akiva flag and optional role_filter keyword.

    Returns:
        JSON with total count, agent list, and platform metadata.
    """
    agents = dict(AGENTS_REGISTRY)

    if not params.include_akiva:
        agents.pop("akiva", None)

    if params.role_filter:
        kw = params.role_filter.lower()
        agents = {
            k: v for k, v in agents.items()
            if kw in v["role"].lower() or kw in v["description"].lower()
        }

    result = {
        "total": len(agents),
        "agents": list(agents.values()),
        "platform": "VocalisAI V3",
        "deployment": "Google Cloud Run gen2 — us-central1",
        "ethical_engine": "Tikun Olam Framework (5 dimensions, 5 LLM providers in production)",
        "mcp_server_version": __version__,
    }
    logger.debug("vocalisai_list_agents | total=%d filter=%s", len(agents), params.role_filter)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool(
    name="vocalisai_get_agent",
    annotations={
        "title": "Get Agent Profile",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def vocalisai_get_agent(params: GetAgentInput) -> str:
    """Get the full profile of a specific VocalisAI agent.

    Returns capabilities, voice, language, routing rules, and handoff targets
    for the specified agent.

    Args:
        params: Agent ID (alex, nova, diana, sara, marco, raul, or akiva).

    Returns:
        JSON agent profile, or an error with the list of valid IDs.
    """
    agent_id = params.agent_id.lower()
    agent = AGENTS_REGISTRY.get(agent_id)

    if not agent:
        return json.dumps({
            "error": f"Agent '{agent_id}' not found.",
            "available_agents": sorted(AGENTS_REGISTRY.keys()),
        }, indent=2)

    logger.debug("vocalisai_get_agent | agent=%s", agent_id)
    return json.dumps(agent, indent=2, ensure_ascii=False)


@mcp.tool(
    name="vocalisai_analyze_call",
    annotations={
        "title": "Ethical Call Analysis — Tikun Olam Framework",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def vocalisai_analyze_call(params: AnalyzeCallInput) -> str:
    """Run ethical evaluation on a conversation turn using the Tikun Olam Framework.

    Evaluates the agent's proposed response across 5 ethical dimensions:
      • Chesed   (0.25) — Patient wellbeing and empathy
      • Gevurah  (0.20) — Operational boundaries and clinical limits
      • Tiferet  (0.25) — Balance across all stakeholder interests
      • Netzach  (0.15) — Resolution effectiveness
      • Hod      (0.15) — Honesty and transparency

    Also runs a hard-veto scan for critical violations (diagnosis attempts,
    emergency non-escalation, emotional manipulation, medical advice, false urgency,
    privacy violations).

    This mirrors the multi-LLM evaluation engine running in production, using
    deterministic heuristics that replicate the same scoring thresholds.

    Args:
        params: agent_id, user_message, agent_response, and optional prior context.

    Returns:
        JSON with clearance decision (APPROVED|CONDITIONAL|REJECTED), overall_score
        (0.0–1.0), per-dimension breakdown, violations list, and recommendation.
    """
    result = _ethics.evaluate(
        agent_id=params.agent_id,
        user_message=params.user_message,
        agent_response=params.agent_response,
        context=params.context,
    )
    logger.info(
        "vocalisai_analyze_call | agent=%s clearance=%s score=%.3f veto=%s",
        params.agent_id, result.clearance, result.overall_score, result.hard_veto_triggered,
    )
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


@mcp.tool(
    name="vocalisai_route_message",
    annotations={
        "title": "Simulate Akiva Routing",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def vocalisai_route_message(params: RouteMessageInput) -> str:
    """Simulate Akiva's intelligent routing logic for an incoming patient message.

    Applies the same priority chain used in production:
      1. Emergency override → Diana (HIGH priority, language-independent)
      2. Billing intent     → Marco
      3. Language detection → Alex (ES) | Nova (EN)
      4. Default            → Alex

    Args:
        params: Patient message, optional language hint ('es'|'en'), and explain flag.

    Returns:
        JSON with routing_decision (routed_to, reason, priority, confidence),
        agent_details, and optional human-readable explanation.
    """
    decision = _router.route(params.message, params.language)
    agent = AGENTS_REGISTRY.get(decision.routed_to, {})

    result: dict = {
        "message_preview": params.message[:120] + ("…" if len(params.message) > 120 else ""),
        "routing_decision": decision.to_dict(),
        "agent_details": {
            "id": agent.get("id"),
            "name": agent.get("name"),
            "role": agent.get("role"),
            "language": agent.get("language"),
            "voice": agent.get("voice"),
        },
    }

    if params.explain:
        result["explanation"] = _router.explanation(decision)

    logger.info(
        "vocalisai_route_message | routed_to=%s reason=%s priority=%s",
        decision.routed_to, decision.reason, decision.priority,
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool(
    name="vocalisai_health_check",
    annotations={
        "title": "Platform Health Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def vocalisai_health_check() -> str:
    """Check the health of the VocalisAI production platform on Google Cloud Run.

    Pings the /health endpoint and returns service status, Firebase connectivity,
    response time, and cold-start detection.

    Returns:
        JSON with status, firebase, response_time_ms, cold_start flag, and endpoint.
    """
    start = asyncio.get_event_loop().time()
    try:
        async with get_client() as client:
            response = await client.get("/health")
            elapsed_ms = round((asyncio.get_event_loop().time() - start) * 1000, 1)
            response.raise_for_status()
            data = response.json()
            result = {
                "status": data.get("status", "unknown"),
                "firebase": data.get("firebase", False),
                "response_time_ms": elapsed_ms,
                "cold_start": is_cold_start(elapsed_ms),
                "endpoint": f"{settings.vocalisai_base_url}/health",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            logger.info("health_check | status=%s time=%.0fms", result["status"], elapsed_ms)
            return json.dumps(result, indent=2)
    except Exception as exc:
        elapsed_ms = round((asyncio.get_event_loop().time() - start) * 1000, 1)
        logger.warning("health_check failed | error=%s", exc)
        return json.dumps({
            "status": "unreachable",
            "error": format_error(exc),
            "response_time_ms": elapsed_ms,
            "endpoint": f"{settings.vocalisai_base_url}/health",
            "note": "Cloud Run may be cold-starting — retry in ~10 seconds.",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2)


@mcp.tool(
    name="vocalisai_get_session",
    annotations={
        "title": "Get Session Transcript",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def vocalisai_get_session(params: GetSessionInput) -> str:
    """Retrieve a session transcript and metadata from the VocalisAI platform.

    Fetches conversation history, agent assignments, ethical evaluation results,
    and call metadata for a specific session stored in Firestore.

    Args:
        params: session_id — the Firestore document ID (format: session_YYYYMMDD_HHMMSS).

    Returns:
        JSON with session transcript, agent routing history, ethical scores, and call metadata.
        Returns a structured error if the session is not found or the service is unreachable.
    """
    try:
        async with get_client() as client:
            response = await client.get(f"/sessions/{params.session_id}")
            response.raise_for_status()
            data = response.json()
            logger.info("get_session | session_id=%s", params.session_id)
            return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.warning("get_session failed | session_id=%s error=%s", params.session_id, exc)
        return json.dumps({
            "error": format_error(exc),
            "session_id": params.session_id,
            "hint": (
                "Ensure the session ID is valid. Sessions are stored for 90 days. "
                "Format: session_YYYYMMDD_HHMMSS or a Firestore document ID."
            ),
        }, indent=2)


@mcp.tool(
    name="vocalisai_platform_info",
    annotations={
        "title": "Platform Capabilities Overview",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def vocalisai_platform_info() -> str:
    """Return a comprehensive overview of VocalisAI V3 capabilities, integrations, and architecture.

    Includes: agent roster, ethical framework dimensions, LLM providers, telephony stack,
    compliance coverage, industry modules, and MCP server version.

    Returns:
        JSON with full platform metadata — useful for LLM context initialization.
    """
    result = {
        "platform": {
            "name": "VocalisAI V3",
            "version": "3.0",
            "mcp_server_version": __version__,
            "description": (
                "Production multi-agent voice AI platform for dental clinics. "
                "Handles inbound/outbound calls with specialized AI agents, "
                "real-time ethical evaluation, and multi-LLM consensus."
            ),
            "deployment": "Google Cloud Run gen2 — us-central1",
            "base_url": settings.vocalisai_base_url,
        },
        "agents": {
            "total": len(AGENTS_REGISTRY),
            "roster": [
                {"id": a["id"], "name": a["name"], "role": a["role"], "language": a["language"]}
                for a in AGENTS_REGISTRY.values()
            ],
        },
        "ethical_framework": {
            "name": "Tikun Olam Framework",
            "dimensions": len(ETHICAL_DIMENSIONS),
            "hard_veto_patterns": len(HARD_VETO_PATTERNS),
            "production_providers": ["Gemini", "DeepSeek", "GPT-4o", "Mistral", "Grok-3"],
            "clearance_thresholds": {
                "APPROVED": ">= 0.55",
                "CONDITIONAL": "0.20 – 0.54",
                "REJECTED": "< 0.20 or hard_veto=True",
            },
        },
        "integrations": {
            "telephony": "Twilio Programmable Voice",
            "voice_ai": "ElevenLabs Conversational AI",
            "realtime_ai": "Google Gemini Live API",
            "crm": "GoHighLevel",
            "database": "Firebase Firestore",
            "llm_providers": ["Gemini 2.0 Flash", "GPT-4o", "DeepSeek", "Mistral", "Grok-3"],
        },
        "compliance": {
            "hipaa_aligned": True,
            "tcpa": True,
            "dnc_checking": True,
            "phi_handling": "encrypted + audit-logged",
        },
        "industry_modules": ["dental", "healthcare", "legal", "logistics"],
        "mcp_tools": [
            "vocalisai_list_agents",
            "vocalisai_get_agent",
            "vocalisai_analyze_call",
            "vocalisai_route_message",
            "vocalisai_health_check",
            "vocalisai_get_session",
            "vocalisai_platform_info",
        ],
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


# ─── Resources ────────────────────────────────────────────────────────────────


@mcp.resource("vocalisai://agents/{agent_id}")
async def get_agent_resource(agent_id: str) -> str:
    """Agent profile as an MCP resource — efficient for repeated lookups."""
    agent = AGENTS_REGISTRY.get(agent_id.lower())
    if not agent:
        return json.dumps({
            "error": f"Agent '{agent_id}' not found.",
            "available": sorted(AGENTS_REGISTRY.keys()),
        })
    return json.dumps(agent, indent=2, ensure_ascii=False)


@mcp.resource("vocalisai://ethical-dimensions")
async def get_ethical_dimensions() -> str:
    """Tikun Olam ethical dimensions as an MCP resource."""
    return json.dumps(ETHICAL_DIMENSIONS, indent=2, ensure_ascii=False)


@mcp.resource("vocalisai://platform-info")
async def get_platform_info_resource() -> str:
    """Lightweight platform overview as an MCP resource."""
    return json.dumps({
        "name": "VocalisAI V3",
        "version": "3.0",
        "agents": len(AGENTS_REGISTRY),
        "ethical_engine": "Tikun Olam Framework",
        "deployment": "Google Cloud Run gen2 — us-central1",
        "base_url": settings.vocalisai_base_url,
        "mcp_version": __version__,
    }, indent=2)


# ─── Entry Point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Start the MCP server. Transport is controlled by MCP_TRANSPORT env var.

    Cloud Run compatibility:
      - Reads PORT env var first (Cloud Run always sets this).
      - Falls back to MCP_PORT setting.
      - Binds to 0.0.0.0 so Cloud Run health probes reach the container.
    """
    import os

    transport = settings.mcp_transport.lower()

    # Cloud Run sets PORT; respect it over MCP_PORT
    port = int(os.environ.get("PORT", settings.mcp_port))

    logger.info(
        "Starting VocalisAI MCP Server v%s | transport=%s host=0.0.0.0 port=%d",
        __version__, transport, port,
    )

    if transport == "http":
        # FastMCP 3.x: transport="http", explicit host binding for Cloud Run
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()  # Default: stdio


if __name__ == "__main__":
    main()
