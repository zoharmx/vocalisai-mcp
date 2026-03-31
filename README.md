# VocalisAI MCP Server

[![CI](https://github.com/zoharmx/vocalisai-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/zoharmx/vocalisai-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A production-grade **Model Context Protocol (MCP)** server that exposes the VocalisAI multi-agent voice AI platform to any MCP-compatible LLM client — Claude Desktop, Cursor, Cline, or custom AI applications.

> **MCP Server (production):** `https://vocalisai-mcp-495684990330.us-central1.run.app`  
> **Live voice platform:** `https://vocalis-ai-v3-495684990330.us-central1.run.app`  
> Built for the **Google Gemini Live Agent Challenge 2026**

---

## What It Exposes

VocalisAI V3 is a production healthcare voice AI platform with 7 specialized agents, real-time ethical evaluation (Tikun Olam Framework), and live image analysis. This MCP server makes all of that accessible to LLMs as structured tools.

### Tools (7)

| Tool | Description |
|---|---|
| `vocalisai_list_agents` | Full agent registry — roles, languages, capabilities |
| `vocalisai_get_agent` | Detailed profile for a specific agent |
| `vocalisai_analyze_call` | Ethical evaluation via Tikun Olam Framework |
| `vocalisai_route_message` | Simulate Akiva's intelligent routing logic |
| `vocalisai_health_check` | Ping the live Cloud Run service |
| `vocalisai_get_session` | Retrieve a session transcript from Firestore |
| `vocalisai_platform_info` | Full platform capabilities and architecture overview |

### Resources (3 URI templates)

| Resource | URI |
|---|---|
| Agent profile | `vocalisai://agents/{agent_id}` |
| Ethical dimensions | `vocalisai://ethical-dimensions` |
| Platform info | `vocalisai://platform-info` |

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Install

```bash
git clone https://github.com/zoharmx/vocalisai-mcp.git
cd vocalisai-mcp

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env and set VOCALISAI_BASE_URL to your Cloud Run URL
```

### Run (stdio — for Claude Desktop / Cursor)

```bash
python -m vocalisai_mcp
```

### Run (HTTP — for Docker / remote clients)

```bash
MCP_TRANSPORT=http MCP_PORT=8001 python -m vocalisai_mcp
```

### Run with Docker

```bash
docker compose up
```

---

## Claude Desktop Integration

**Option A — Remote (no install needed):** point directly to the production Cloud Run server:

```json
{
  "mcpServers": {
    "vocalisai": {
      "url": "https://vocalisai-mcp-495684990330.us-central1.run.app/mcp"
    }
  }
}
```

**Option B — Local:** add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)  
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "vocalisai": {
      "command": "python",
      "args": ["-m", "vocalisai_mcp"],
      "cwd": "/path/to/vocalisai-mcp",
      "env": {
        "VOCALISAI_BASE_URL": "https://vocalis-ai-v3-495684990330.us-central1.run.app"
      }
    }
  }
}
```

---

## Usage Examples

### List all agents

```json
Tool: vocalisai_list_agents
Input: { "include_akiva": true }
```

### Route an emergency message

```json
Tool: vocalisai_route_message
Input: { "message": "Tengo dolor severo 9/10", "explain": true }
Output: { "routing_decision": { "routed_to": "diana", "priority": "HIGH" }, ... }
```

### Ethical evaluation

```json
Tool: vocalisai_analyze_call
Input: {
  "agent_id": "alex",
  "user_message": "Necesito una cita",
  "agent_response": "Con gusto le ayudo a agendar su cita. ¿Qué día le queda bien?"
}
Output: { "clearance": "APPROVED", "overall_score": 0.843, ... }
```

### Get platform overview

```json
Tool: vocalisai_platform_info
Input: {}
Output: { "platform": {...}, "agents": {...}, "ethical_framework": {...}, ... }
```

---

## Architecture

```
MCP Client (Claude Desktop / Cursor / Custom Agent)
    │
    └── stdio / Streamable HTTP transport
          │
          └── vocalisai_mcp/server.py  (FastMCP)
                ├── 7 Tools
                ├── 3 Resources
                ├── TikunOlamEngine    ← ethics.py
                ├── AkivaRouter        ← routing.py
                └── HTTP Client        ← client.py → Cloud Run
```

The ethical evaluation tool (`vocalisai_analyze_call`) mirrors the real multi-LLM engine running in production — same 5 dimensions, same hard-veto patterns, same clearance thresholds.

---

## Agents

| Agent | Language | Role |
|---|---|---|
| Alex | ES-MX | Dental Receptionist |
| Nova | EN-US | English Qualifier |
| Diana | Bilingual | Emergency Triage Specialist |
| Sara | Bilingual | Post-Visit Follow-up Coordinator |
| Marco | Bilingual | Billing Specialist |
| Raúl | Bilingual | Outbound Coordinator |
| Akiva | Internal | Meta-Agent Supervisor |

---

## Tikun Olam Ethical Framework

Every agent response is evaluated across 5 dimensions before delivery:

| Dimension | Weight | Focus | Production LLM |
|---|---|---|---|
| Chesed | 25% | Patient wellbeing & empathy | Gemini |
| Gevurah | 20% | Operational boundaries | DeepSeek |
| Tiferet | 25% | Stakeholder balance | GPT-4o |
| Netzach | 15% | Resolution effectiveness | Mistral |
| Hod | 15% | Honesty & transparency | Grok-3 |

**Hard veto patterns** (any trigger → REJECTED):
- `attempted_diagnosis`
- `emergency_not_escalated`
- `emotional_manipulation`
- `medical_advice_given`
- `false_urgency`
- `privacy_violation`

---

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Type check
mypy src/vocalisai_mcp/
```

---

## Stack

| Component | Technology |
|---|---|
| MCP SDK | FastMCP (Python) |
| Transport | stdio (default) / Streamable HTTP |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| HTTP Client | httpx (async) |
| CI/CD | GitHub Actions |
| Container | Docker / GHCR |
| Live Platform | Google Cloud Run gen2 |

---

Built by **Jesus Eduardo Rodriguez** — [eduardorodriguez.site](https://eduardorodriguez.site)  
Part of the VocalisAI V3 ecosystem — Google Gemini Live Agent Challenge 2026
