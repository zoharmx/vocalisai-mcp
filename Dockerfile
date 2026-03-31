# ─────────────────────────────────────────────────────────────────────────────
# VocalisAI MCP Server — Production Container
# Transport: Streamable HTTP (port 8001)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Security: non-root user
RUN groupadd -r vocalis && useradd -r -g vocalis vocalis

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Switch to non-root
USER vocalis

# ── Runtime defaults ──────────────────────────────────────────────────────────
ENV MCP_TRANSPORT=http \
    MCP_PORT=8001 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx, asyncio; asyncio.run(httpx.AsyncClient().get('http://localhost:8001/health'))" || exit 1

CMD ["python", "-m", "vocalisai_mcp.server"]
