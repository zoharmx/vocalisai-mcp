# ─────────────────────────────────────────────────────────────────────────────
# VocalisAI MCP Server — Production Container
# Transport: Streamable HTTP — Cloud Run compatible
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Security: non-root user
RUN groupadd -r vocalis && useradd -r -g vocalis vocalis

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the package so `python -m vocalisai_mcp` is resolvable
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps -e .

# Switch to non-root
USER vocalis

# ── Runtime defaults ──────────────────────────────────────────────────────────
# PORT is set by Cloud Run at runtime — do NOT hardcode it here
ENV MCP_TRANSPORT=http \
    MCP_PORT=8001 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Cloud Run ignores EXPOSE but useful for local docker run
EXPOSE 8001

CMD ["python", "-m", "vocalisai_mcp.server"]
