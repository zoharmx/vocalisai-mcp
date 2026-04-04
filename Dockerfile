# ─────────────────────────────────────────────────────────────────────────────
# VocalisAI — Multi-service Production Container
#
# SERVICE=mcp        → MCP Server  (HTTP transport, Cloud Run compatible)
# SERVICE=dashboard  → Dashboard   (FastAPI/uvicorn, Cloud Run compatible)
#
# Build:  docker build -t vocalisai .
# Run MCP: docker run -e SERVICE=mcp -e PORT=8080 vocalisai
# Run UI:  docker run -e SERVICE=dashboard -e PORT=8080 vocalisai
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Security: non-root user
RUN groupadd -r vocalis && useradd -r -g vocalis vocalis

WORKDIR /app

# Install deps first (layer cache stays valid unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/

# Entrypoint selects which service to start (default: mcp)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to non-root
USER vocalis

# ── Runtime defaults ──────────────────────────────────────────────────────────
# PORT is injected by Cloud Run at runtime — NEVER hardcode it
ENV SERVICE=mcp \
    MCP_TRANSPORT=http \
    MCP_PORT=8001 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
