# VocalisAI — MCP Server & Dashboard

[![CI](https://github.com/zoharmx/vocalisai-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/zoharmx/vocalisai-mcp/actions/workflows/ci.yml)
[![Deploy Dashboard](https://github.com/zoharmx/vocalisai-mcp/actions/workflows/deploy-dashboard.yml/badge.svg)](https://github.com/zoharmx/vocalisai-mcp/actions/workflows/deploy-dashboard.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://modelcontextprotocol.io)
[![Vertex AI](https://img.shields.io/badge/AI-Vertex%20AI-4285F4.svg)](https://cloud.google.com/vertex-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Plataforma de IA de voz multi-agente para clínicas dentales con evaluación ética en tiempo real. Expone la infraestructura completa como servidor MCP para integración con cualquier cliente LLM compatible.

> **🎙 Agente en Vivo:** [`live_agent.html`](https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app/static/live_agent.html)  
> **📊 Dashboard:** [`vocalisai-dashboard`](https://vocalisai-dashboard-hzz2wlra6a-uc.a.run.app)  
> **🔌 MCP Server:** `https://vocalisai-mcp-hzz2wlra6a-uc.a.run.app`  
> **⚙️ Plataforma:** `https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app`  
> Desarrollado para el **Google Gemini Live Agent Challenge 2026** · Powered by **Vertex AI**

---

## ¿Qué es VocalisAI?

VocalisAI V3 es una plataforma de voz con IA multi-agente diseñada para **clínicas dentales**. Atiende llamadas entrantes y salientes 24/7 con agentes especializados, enrutamiento inteligente y evaluación ética automática de cada respuesta antes de que llegue al paciente.

```
Paciente llama
    │
    ▼
Akiva (meta-supervisor)
    ├── Emergencia ──────► Diana  → triage visual con Gemini Vision
    ├── Facturación ─────► Marco  → costos, seguros, planes de pago
    ├── Español ─────────► Alex   → agenda, OCR de seguros en vivo
    └── Inglés ──────────► Nova   → calificación de leads EN
                              │
                              ▼
                    Tikun Olam Framework
                    (evaluación ética en 5 dimensiones antes de responder)
```

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│             CLIENTES MCP                                │
│  Claude Desktop · Cursor · Cline · Agentes custom       │
└───────────────────────┬─────────────────────────────────┘
                        │ stdio / HTTP
                        ▼
┌─────────────────────────────────────────────────────────┐
│              vocalisai-mcp  (Cloud Run)                 │
│  FastMCP · 7 tools · 3 resources · Pydantic v2          │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────┐   ┌──────────────────────────────┐
│  vocalisai-dashboard│   │   vocalis-ai-v3  (Cloud Run)  │
│  FastAPI · Chart.js │   │   Gemini Live · Twilio        │
│  Mobile-first SPA   │   │   ElevenLabs · Firestore      │
└─────────────────────┘   └──────────────────────────────┘
                                       │
                              Vertex AI (us-central1)
                         Gemini 2.5 Flash · GPT-4o
                         DeepSeek · Mistral · Grok-3
```

---

## Servicios en Producción

| Servicio | URL | Descripción |
|---|---|---|
| **Agente en Vivo** | [live_agent.html](https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app/static/live_agent.html) | Interfaz de voz con Gemini Live |
| **Dashboard** | [vocalisai-dashboard](https://vocalisai-dashboard-hzz2wlra6a-uc.a.run.app) | Panel de métricas y simulador |
| **MCP Server** | vocalisai-mcp.run.app | Servidor de herramientas MCP |
| **Plataforma de voz** | vocalis-ai-v3.run.app | Backend principal de agentes |

---

## Agentes (7)

| ID | Nombre | Idioma | Rol | Voz |
|---|---|---|---|---|
| `alex` | Alex | ES-MX | Recepcionista principal | Puck |
| `nova` | Nova | EN-US | Calificadora en inglés | Kore |
| `diana` | Diana | Bilingüe | Especialista en emergencias | Aoede |
| `sara` | Sara | Bilingüe | Seguimiento post-visita | Aoede |
| `marco` | Marco | Bilingüe | Especialista en facturación | Fenrir |
| `raul` | Raúl | Bilingüe | Coordinador de campañas salientes | Puck |
| `akiva` | Akiva | Interno | Meta-supervisor (sin voz) | — |

---

## Herramientas MCP (7)

```python
# Listar agentes
vocalisai_list_agents(include_akiva=True, role_filter="billing")

# Perfil completo de un agente
vocalisai_get_agent(agent_id="diana")

# Evaluar ética de una respuesta (Tikun Olam Framework)
vocalisai_analyze_call(
    agent_id="alex",
    user_message="Me duele mucho, como 8/10",
    agent_response="Le conecto de inmediato con Diana."
)

# Simular enrutamiento Akiva
vocalisai_route_message(message="Tengo dolor severo 9/10", language="es")

# Health check del backend en Cloud Run
vocalisai_health_check()

# Recuperar transcripción de sesión (Firestore, 90 días)
vocalisai_get_session(session_id="session_20260404_153000")

# Información completa de la plataforma
vocalisai_platform_info()
```

---

## Recursos MCP (3)

```
vocalisai://agents/{agent_id}      → Perfil JSON de un agente
vocalisai://ethical-dimensions     → Las 5 dimensiones Tikun Olam
vocalisai://platform-info          → Metadata de la plataforma
```

---

## Marco Ético — Tikun Olam Framework

Cada respuesta de un agente pasa por evaluación ética **antes** de entregarse al paciente.

| Dimensión | Peso | Foco | Proveedor LLM |
|---|---|---|---|
| Chesed | 25% | Bienestar emocional del paciente | Gemini |
| Gevurah | 20% | Límites clínicos y operativos | DeepSeek |
| Tiferet | 25% | Balance entre todos los intereses | GPT-4o |
| Netzach | 15% | Resolución efectiva del problema | Mistral |
| Hod | 15% | Honestidad y transparencia | Grok-3 |

**Umbrales:** `APPROVED ≥ 0.55` · `CONDITIONAL 0.20–0.54` · `REJECTED < 0.20 o hard_veto`

**Hard vetoes automáticos:** diagnóstico médico · emergencia no escalada · manipulación emocional · consejo médico · urgencia falsa · violación de privacidad

---

## Inicio Rápido

### Opción A — Claude Desktop (local, stdio)

```bash
# 1. Instalar
git clone https://github.com/zoharmx/vocalisai-mcp.git
cd vocalisai-mcp
pip install -e .

# 2. Configurar
cp .env.example .env
# editar .env con tu URL de la plataforma

# 3. Agregar a Claude Desktop
# ~/.config/claude/claude_desktop_config.json  (macOS/Linux)
# %APPDATA%\Claude\claude_desktop_config.json  (Windows)
```

```json
{
  "mcpServers": {
    "vocalisai": {
      "command": "vocalisai-mcp",
      "env": {
        "VOCALISAI_BASE_URL": "https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app"
      }
    }
  }
}
```

### Opción B — Dashboard local

```bash
pip install -e .
vocalisai-dashboard
# → http://localhost:8080
```

### Opción C — Docker Compose (ambos servicios)

```bash
cp .env.example .env   # configurar VOCALISAI_BASE_URL
docker compose up -d

# Dashboard:   http://localhost:8080
# MCP Server:  http://localhost:8001
```

### Opción D — Cursor / Cline

```json
{
  "mcpServers": {
    "vocalisai": { "command": "vocalisai-mcp" }
  }
}
```

---

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `VOCALISAI_BASE_URL` | — | URL de la plataforma de voz (Cloud Run) |
| `VOCALISAI_API_KEY` | — | API key (opcional, para endpoints autenticados) |
| `VOCALISAI_REQUEST_TIMEOUT` | `15.0` | Timeout HTTP en segundos |
| `MCP_TRANSPORT` | `stdio` | `stdio` o `http` |
| `MCP_PORT` | `8001` | Puerto en modo HTTP |
| `MCP_DASHBOARD_PORT` | `8080` | Puerto del dashboard (local) |
| `SERVICE` | `mcp` | `mcp` o `dashboard` (para Docker) |
| `LOG_LEVEL` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |

---

## Despliegue en Cloud Run

```bash
# Build con Cloud Build (sin Docker local necesario)
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/TU_PROYECTO/vocalis/vocalisai-dashboard:latest .

# Desplegar dashboard
gcloud run deploy vocalisai-dashboard \
  --image us-central1-docker.pkg.dev/TU_PROYECTO/vocalis/vocalisai-dashboard:latest \
  --set-env-vars "SERVICE=dashboard,VOCALISAI_BASE_URL=https://tu-plataforma.run.app" \
  --region us-central1 --allow-unauthenticated
```

El workflow `.github/workflows/deploy-dashboard.yml` hace esto automáticamente en cada push a `master`.

---

## Tests

```bash
pip install -r requirements-dev.txt

# Suite completa
pytest tests/ -v

# Por módulo
pytest tests/test_routing.py -v   # motor Akiva
pytest tests/test_ethics.py  -v   # Tikun Olam
pytest tests/test_tools.py   -v   # herramientas MCP
```

**Cobertura:** routing (todos los caminos de prioridad) · ética (aprobación, veto, condicional, timestamps) · herramientas MCP · registry de agentes

---

## Estructura del Proyecto

```
vocalisai-mcp/
├── src/vocalisai_mcp/
│   ├── server.py          # MCP server — 7 tools, 3 resources
│   ├── registry.py        # Agentes, dimensiones éticas, veto catalog
│   ├── routing.py         # Motor de enrutamiento Akiva
│   ├── ethics.py          # Motor Tikun Olam
│   ├── client.py          # Cliente HTTP async (httpx)
│   ├── config.py          # Configuración vía env vars (pydantic-settings)
│   └── dashboard/
│       ├── server.py      # FastAPI — 11 endpoints REST
│       ├── metrics.py     # Generación de datos y métricas
│       └── static/
│           └── index.html # SPA mobile-first (Chart.js)
├── tests/
│   ├── test_routing.py
│   ├── test_ethics.py
│   ├── test_tools.py
│   └── test_registry.py
├── .github/workflows/
│   ├── ci.yml             # lint + types + tests en PR
│   └── deploy-dashboard.yml # auto-deploy a Cloud Run
├── Dockerfile             # Multi-service: SERVICE=mcp|dashboard
├── entrypoint.sh          # Selección de servicio en runtime
├── docker-compose.yml     # Stack local completo
└── pyproject.toml         # Metadatos, deps, ruff, mypy, pytest
```

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Telefonía | Twilio Programmable Voice |
| IA de voz | ElevenLabs Conversational AI |
| IA en tiempo real | Google Gemini 2.5 Flash Live (Vertex AI) |
| Visión | Gemini Vision — triage fotográfico en vivo |
| CRM | GoHighLevel |
| Base de datos | Firebase Firestore |
| LLM multi-proveedor | Gemini · GPT-4o · DeepSeek · Mistral · Grok-3 |
| Infraestructura | Google Cloud Run gen2 · us-central1 |
| MCP Framework | FastMCP 3.x |
| Dashboard backend | FastAPI + uvicorn |
| Dashboard frontend | Vanilla JS + Chart.js 4 |
| Validación | Pydantic v2 + pydantic-settings |
| Lenguaje | Python 3.11+ |

---

## Cumplimiento Normativo

- **HIPAA** — manejo encriptado de PHI con audit log
- **TCPA** — cumplimiento para llamadas de telemarketing
- **DNC Registry** — verificación activa de lista Do Not Call
- **Hard vetoes** — bloqueo automático de solicitudes de SSN, números de tarjeta y cualquier PII sensible

---

## Autor

**Jesus Eduardo Rodriguez** — VocalisAI  
Google Gemini Live Agent Challenge 2026  
Proyecto: `tikunframework` · GCP us-central1

---

*Para documentación técnica detallada ver [`TECHNICAL_GUIDE.md`](TECHNICAL_GUIDE.md)*
