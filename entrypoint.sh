#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# VocalisAI Container Entrypoint
# Selects which service to run based on the SERVICE environment variable.
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "[entrypoint] SERVICE=${SERVICE:-mcp} | PORT=${PORT:-not set}"

case "${SERVICE:-mcp}" in
  dashboard)
    echo "[entrypoint] Starting VocalisAI Dashboard (FastAPI/uvicorn)…"
    exec python -m vocalisai_mcp.dashboard.server
    ;;
  mcp)
    echo "[entrypoint] Starting VocalisAI MCP Server (FastMCP HTTP)…"
    exec python -m vocalisai_mcp.server
    ;;
  *)
    echo "[entrypoint] ERROR: Unknown SERVICE='${SERVICE}'. Use 'mcp' or 'dashboard'." >&2
    exit 1
    ;;
esac
