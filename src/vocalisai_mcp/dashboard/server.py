"""
VocalisAI Dashboard Server
===========================
FastAPI web application that exposes REST APIs consumed by the SPA dashboard.

Endpoints:
    GET  /                          → Serve index.html
    GET  /api/overview              → KPI summary cards
    GET  /api/agents                → Agent registry with mock stats
    GET  /api/calls/timeline        → 24h call volume (hourly)
    GET  /api/calls/trend           → 7-day call trend (daily)
    GET  /api/calls/recent          → Recent calls table
    GET  /api/routing/distribution  → Routing counts per agent
    GET  /api/routing/language      → Language split
    GET  /api/ethics/summary        → Ethics scores + clearance distribution
    GET  /api/health                → Platform health status
    POST /api/simulate/route        → Live Akiva routing simulation
    POST /api/simulate/ethics       → Live Tikun Olam evaluation

Usage:
    vocalisai-dashboard              # starts on http://0.0.0.0:8080
    MCP_DASHBOARD_PORT=3000 vocalisai-dashboard
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .. import __version__
from ..client import format_error, is_cold_start
from ..config import settings
from ..ethics import TikunOlamEngine
from ..registry import AGENTS_REGISTRY, ETHICAL_DIMENSIONS, HARD_VETO_CATALOG
from ..routing import AkivaRouter
from .metrics import (
    AGENT_COLORS,
    AGENT_NAMES,
    generate_7day_trend,
    generate_call_timeline_24h,
    generate_ethics_summary,
    generate_kpi_overview,
    generate_language_split,
    generate_recent_calls,
    generate_routing_distribution,
)

logger = logging.getLogger(__name__)

_ethics = TikunOlamEngine()
_router = AkivaRouter()

STATIC_DIR = Path(__file__).parent / "static"

# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="VocalisAI Dashboard",
    description="Monitoring and analytics dashboard for the VocalisAI MCP platform",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Static / SPA ─────────────────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def serve_dashboard() -> FileResponse:
    """Serve the SPA dashboard."""
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Dashboard HTML not found. Build may be incomplete.")
    return FileResponse(index, media_type="text/html")


# ─── Input models ─────────────────────────────────────────────────────────────


class RouteRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: Optional[str] = Field(default=None, description="'es' | 'en' | null for auto")


class EthicsRequest(BaseModel):
    agent_id: str = Field(..., min_length=2, max_length=20)
    user_message: str = Field(..., min_length=1, max_length=2000)
    agent_response: str = Field(..., min_length=1, max_length=2000)
    context: Optional[str] = Field(default=None, max_length=4000)


# ─── API routes ───────────────────────────────────────────────────────────────


@app.get("/api/overview")
async def api_overview() -> JSONResponse:
    """KPI summary: calls today, agents, avg ethics score, emergencies."""
    data = generate_kpi_overview()
    return JSONResponse(data)


@app.get("/api/agents")
async def api_agents() -> JSONResponse:
    """Agent registry with display metadata and mock call stats."""
    routing = generate_routing_distribution()
    counts_by_agent = dict(zip(routing["agents"], routing["counts"]))

    agents_out: list[dict[str, Any]] = []
    for agent_id, agent in AGENTS_REGISTRY.items():
        agents_out.append({
            **agent,
            "color":      AGENT_COLORS.get(agent_id, "#64748b"),
            "calls_week": counts_by_agent.get(agent_id, 0),
            "is_voice":   agent.get("voice") is not None,
        })

    return JSONResponse({"agents": agents_out, "total": len(agents_out)})


@app.get("/api/calls/timeline")
async def api_calls_timeline() -> JSONResponse:
    """Hourly call volume — last 24 hours."""
    return JSONResponse(generate_call_timeline_24h())


@app.get("/api/calls/trend")
async def api_calls_trend() -> JSONResponse:
    """Daily call totals — last 7 days."""
    return JSONResponse(generate_7day_trend())


@app.get("/api/calls/recent")
async def api_calls_recent(n: int = 15) -> JSONResponse:
    """Recent calls with routing and ethics metadata."""
    n = max(1, min(n, 50))
    return JSONResponse({"calls": generate_recent_calls(n)})


@app.get("/api/routing/distribution")
async def api_routing_distribution() -> JSONResponse:
    """Routing distribution across agents this week."""
    return JSONResponse(generate_routing_distribution())


@app.get("/api/routing/language")
async def api_language_split() -> JSONResponse:
    """Language detection distribution."""
    return JSONResponse(generate_language_split())


@app.get("/api/ethics/summary")
async def api_ethics_summary() -> JSONResponse:
    """Aggregated ethics scores, clearance distribution, and veto counts."""
    data = generate_ethics_summary()

    # Enrich veto data with catalog descriptions
    veto_detail: list[dict[str, Any]] = []
    for veto_id, count in data["veto_counts"].items():
        catalog_entry = HARD_VETO_CATALOG.get(veto_id, {})
        veto_detail.append({
            "id":          veto_id,
            "count":       count,
            "severity":    catalog_entry.get("severity", "UNKNOWN"),
            "description": catalog_entry.get("description", ""),
        })

    # Enrich dimension data
    dimension_detail: list[dict[str, Any]] = []
    for dim_name, avg_score in data["avg_scores"].items():
        dim_info = ETHICAL_DIMENSIONS.get(dim_name, {})
        dimension_detail.append({
            "name":     dim_name,
            "label":    dim_name.capitalize(),
            "score":    avg_score,
            "weight":   dim_info.get("weight", 0.0),
            "focus":    dim_info.get("focus", ""),
            "provider": dim_info.get("provider", ""),
        })

    return JSONResponse({
        **data,
        "veto_detail":     veto_detail,
        "dimension_detail": dimension_detail,
    })


@app.get("/api/health")
async def api_health() -> JSONResponse:
    """Platform health check — pings VocalisAI backend when URL is configured."""
    base_status: dict[str, Any] = {
        "mcp_server":    "running",
        "mcp_version":   __version__,
        "agents_loaded": len(AGENTS_REGISTRY),
        "ethical_engine": "ready",
        "routing_engine": "ready",
        "backend_url":   settings.vocalisai_base_url or "(not configured)",
    }

    if not settings.vocalisai_base_url:
        return JSONResponse({
            **base_status,
            "platform":        "unconfigured",
            "firebase":        None,
            "response_time_ms": None,
            "cold_start":      None,
            "note":            "Set VOCALISAI_BASE_URL in .env to enable live health checks.",
        })

    start = asyncio.get_event_loop().time()
    try:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.vocalisai_api_key:
            headers["X-API-Key"] = settings.vocalisai_api_key.get_secret_value()

        async with httpx.AsyncClient(
            base_url=settings.vocalisai_base_url,
            timeout=8.0,
            headers=headers,
        ) as client:
            resp = await client.get("/health")
            elapsed = round((asyncio.get_event_loop().time() - start) * 1000, 1)
            resp.raise_for_status()
            payload = resp.json()
            return JSONResponse({
                **base_status,
                "platform":        payload.get("status", "unknown"),
                "firebase":        payload.get("firebase", False),
                "response_time_ms": elapsed,
                "cold_start":      is_cold_start(elapsed),
            })
    except Exception as exc:
        elapsed = round((asyncio.get_event_loop().time() - start) * 1000, 1)
        logger.warning("Dashboard health check failed: %s", exc)
        return JSONResponse({
            **base_status,
            "platform":        "unreachable",
            "firebase":        None,
            "response_time_ms": elapsed,
            "cold_start":      None,
            "error":           format_error(exc),
        }, status_code=200)   # 200 so the dashboard can read the body


@app.post("/api/simulate/route")
async def api_simulate_route(req: RouteRequest) -> JSONResponse:
    """Live Akiva routing simulation."""
    decision = _router.route(req.message, req.language)
    agent = AGENTS_REGISTRY.get(decision.routed_to, {})
    explanation = _router.explanation(decision)

    return JSONResponse({
        "message_preview": req.message[:120] + ("…" if len(req.message) > 120 else ""),
        "routing": {
            **decision.to_dict(),
            "agent_color": AGENT_COLORS.get(decision.routed_to, "#64748b"),
            "agent_name":  AGENT_NAMES.get(decision.routed_to, decision.routed_to),
        },
        "agent": {
            "id":           agent.get("id"),
            "name":         agent.get("name"),
            "role":         agent.get("role"),
            "language":     agent.get("language"),
            "voice":        agent.get("voice"),
            "capabilities": agent.get("capabilities", []),
            "color":        AGENT_COLORS.get(decision.routed_to, "#64748b"),
        },
        "explanation": explanation,
    })


@app.post("/api/simulate/ethics")
async def api_simulate_ethics(req: EthicsRequest) -> JSONResponse:
    """Live Tikun Olam ethical evaluation."""
    if req.agent_id.lower() not in AGENTS_REGISTRY:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown agent '{req.agent_id}'. Valid: {sorted(AGENTS_REGISTRY.keys())}",
        )

    result = _ethics.evaluate(
        agent_id=req.agent_id,
        user_message=req.user_message,
        agent_response=req.agent_response,
        context=req.context,
    )
    return JSONResponse(result.to_dict())


# ─── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Start the dashboard server.
    Port resolution order: PORT (Cloud Run) → MCP_DASHBOARD_PORT → 8080.
    """
    import uvicorn

    # Cloud Run sets PORT automatically; respect it first
    port = int(os.environ.get("PORT", os.environ.get("MCP_DASHBOARD_PORT", 8080)))
    logger.info("Starting VocalisAI Dashboard v%s on http://0.0.0.0:%d", __version__, port)
    uvicorn.run(
        "vocalisai_mcp.dashboard.server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
