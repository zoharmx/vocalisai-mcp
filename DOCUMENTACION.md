# VocalisAI MCP Server — Documentación Técnica Completa

> **Versión:** 1.0.0 | **Plataforma:** VocalisAI V3 | **Despliegue:** Google Cloud Run gen2 — us-central1
> **Protocolo:** Model Context Protocol (MCP) | **Licencia:** MIT

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Agentes Especializados](#3-agentes-especializados)
4. [Motor de Enrutamiento — Akiva](#4-motor-de-enrutamiento--akiva)
5. [Marco Ético — Tikun Olam Framework](#5-marco-ético--tikun-olam-framework)
6. [Herramientas MCP (API)](#6-herramientas-mcp-api)
7. [Recursos MCP](#7-recursos-mcp)
8. [Integraciones y Stack Tecnológico](#8-integraciones-y-stack-tecnológico)
9. [Cumplimiento Normativo](#9-cumplimiento-normativo)
10. [Beneficios y Propuesta de Valor](#10-beneficios-y-propuesta-de-valor)
11. [Casos de Uso y Oportunidades](#11-casos-de-uso-y-oportunidades)
12. [Guía de Implementación en Producción](#12-guía-de-implementación-en-producción)
13. [Referencia de Configuración](#13-referencia-de-configuración)
14. [Monitoreo y Operación](#14-monitoreo-y-operación)
15. [Preguntas Frecuentes](#15-preguntas-frecuentes)

---

## 1. Visión General

**VocalisAI MCP Server** es la capa de integración que expone la plataforma de IA conversacional VocalisAI V3 como herramientas nativas del **Model Context Protocol (MCP)**, permitiendo que cualquier cliente LLM compatible (Claude Desktop, Cursor, Cline, agentes personalizados) interactúe con la plataforma de voz multi-agente de VocalisAI de forma directa, tipificada y auditada.

### ¿Qué problema resuelve?

Las clínicas dentales y de salud enfrentan tres cuellos de botella críticos en la atención telefónica:

| Problema | Impacto |
|---|---|
| Líneas ocupadas y tiempos de espera | Pacientes que cuelgan y no reagendan |
| Triaje incorrecto de emergencias | Riesgo clínico y legal |
| Respuestas inconsistentes sobre pagos/seguros | Fricción y pérdida de ingresos |

VocalisAI resuelve los tres con una orquesta de agentes de IA especializados que atienden llamadas 24/7, hablan en español e inglés, y cada respuesta pasa por un filtro ético antes de llegar al paciente.

### ¿Qué es MCP y por qué importa?

El **Model Context Protocol** es el estándar abierto de Anthropic que permite conectar modelos de lenguaje con sistemas externos de forma estructurada. Al exponer VocalisAI como servidor MCP, cualquier LLM puede:

- Consultar el estado de los agentes en tiempo real
- Simular el enrutamiento antes de ponerlo en producción
- Evaluar éticamente respuestas de agentes
- Recuperar transcripciones de sesiones para análisis
- Verificar la salud del servicio en producción

Esto convierte al servidor MCP en la **interfaz de control universal** de la plataforma VocalisAI.

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTES MCP                             │
│   Claude Desktop · Cursor · Cline · Agentes Personalizados      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ stdio (local) / HTTP (remoto)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  VocalisAI MCP Server v1.0                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   7 Tools    │  │ 3 Resources  │  │   FastMCP Framework  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                     │
│  ┌──────▼─────────────────▼────────────────────────────────┐   │
│  │               Módulos Internos                           │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │  Akiva   │  │ TikunOlam   │  │  AGENTS_REGISTRY │   │   │
│  │  │  Router  │  │   Engine    │  │  (fuente única)  │   │   │
│  │  └──────────┘  └──────────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│         ┌─────────────────▼──────────────────┐                 │
│         │         HTTP Client (httpx)         │                 │
│         └─────────────────┬──────────────────┘                 │
└───────────────────────────┼─────────────────────────────────────┘
                            │ HTTPS / REST
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              VocalisAI Platform (Google Cloud Run)              │
│                                                                 │
│  Twilio Voice ─► Gemini Live API ─► Agentes ─► Firestore       │
│  ElevenLabs TTS        GoHighLevel CRM        Firebase Auth     │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de una llamada entrante en producción

```
Paciente llama
      │
      ▼
   Twilio recibe la llamada
      │
      ▼
   Akiva clasifica: ¿idioma? ¿emergencia? ¿facturación?
      │
      ├─── Emergencia ──────► Diana (Triage bilingüe)
      ├─── Facturación ─────► Marco (Billing bilingüe)
      ├─── Español ─────────► Alex (Recepcionista ES)
      └─── Inglés ──────────► Nova (Calificadora EN)
                │
                ▼
         Respuesta del agente
                │
                ▼
         Tikun Olam evalúa (5 dimensiones éticas)
                │
         ┌──────┴──────┐
         ▼             ▼
      APROBADA     RECHAZADA/
      → se entrega  CONDICIONAL
                   → agente reformula
```

### Transportes soportados

| Transporte | Protocolo | Uso recomendado |
|---|---|---|
| `stdio` | stdin/stdout | Claude Desktop, Cursor, Cline (local) |
| `http` | HTTP/REST | Docker, Cloud Run, clientes remotos |

---

## 3. Agentes Especializados

La plataforma cuenta con **7 agentes**, cada uno con rol, voz, idioma y capacidades únicas. Akiva actúa como meta-supervisor interno.

### 3.1 Alex — Recepcionista Principal (ES-MX)

| Atributo | Valor |
|---|---|
| **ID** | `alex` |
| **Voz** | Puck |
| **Idioma** | Español (México) |
| **Rol** | Dental Receptionist |

**Capacidades:**
- Agendamiento de citas (integración con GoHighLevel)
- Lectura de tarjetas de seguro por OCR durante la llamada en vivo
- Detección de emergencias por escala de dolor (≥ 7/10 → handoff a Diana)
- Captación de nuevos pacientes

**Handoffs configurados:** Diana (emergencias), Marco (facturación)

> Alex es el punto de entrada principal para llamadas en español. Combina calidez humana con capacidades técnicas como el OCR de seguros en tiempo real, reduciendo el proceso de verificación de minutos a segundos.

---

### 3.2 Nova — Calificadora en Inglés (EN-US)

| Atributo | Valor |
|---|---|
| **ID** | `nova` |
| **Voz** | Kore |
| **Idioma** | Inglés (EE.UU.) |
| **Rol** | English Qualifier |

**Capacidades:**
- Calificación de leads (pacientes nuevos)
- Verificación de seguros
- Captación de pacientes en inglés

**Handoffs configurados:** Alex (para agendar), Marco (facturación)

---

### 3.3 Diana — Especialista en Triage de Emergencias (Bilingüe)

| Atributo | Valor |
|---|---|
| **ID** | `diana` |
| **Voz** | Aoede |
| **Idioma** | Bilingüe (ES/EN) |
| **Rol** | Emergency Triage Specialist |

**Capacidades:**
- Evaluación de dolor en escala 1-10
- Triage visual: solicita y analiza fotos del paciente en vivo con Gemini Vision
- Instrucciones de primeros auxilios
- Agendamiento de citas de emergencia el mismo día

**Handoffs configurados:** Alex (para confirmar cita)

> Diana es el único agente que maneja imágenes. Durante la llamada puede solicitar al paciente que envíe una foto por SMS/WhatsApp y la analiza en segundos con Gemini Vision, permitiendo un triage visual real sin presencia física.

---

### 3.4 Sara — Coordinadora de Seguimiento Post-Visita (Bilingüe)

| Atributo | Valor |
|---|---|
| **ID** | `sara` |
| **Voz** | Aoede |
| **Idioma** | Bilingüe (ES/EN) |
| **Rol** | Post-Visit Follow-up Coordinator |

**Capacidades:**
- Contacto proactivo 24-48h después de procedimientos
- Detección de complicaciones post-operatorias
- Reactivación de pacientes que no se presentaron
- Encuestas de satisfacción

**Handoffs configurados:** Diana (si detecta complicación), Alex (si requiere reagendamiento)

---

### 3.5 Marco — Especialista en Facturación (Bilingüe)

| Atributo | Valor |
|---|---|
| **ID** | `marco` |
| **Voz** | Fenrir |
| **Idioma** | Bilingüe (ES/EN) |
| **Rol** | Billing Specialist |

**Capacidades:**
- Explicación de costos de tratamientos
- Configuración de planes de pago flexibles
- Asistencia en reclamos de seguro

**Handoffs configurados:** Ninguno (agente terminal para flujos de facturación)

---

### 3.6 Raúl — Coordinador de Salidas (Bilingüe)

| Atributo | Valor |
|---|---|
| **ID** | `raul` |
| **Voz** | Puck |
| **Idioma** | Bilingüe (ES/EN) |
| **Rol** | Outbound Coordinator |

**Capacidades:**
- Campañas de reactivación de pacientes inactivos (6+ meses)
- Recordatorios de citas automatizados
- Engagement proactivo con base de pacientes

**Handoffs configurados:** Alex (cuando el paciente quiere agendar)

---

### 3.7 Akiva — Meta-Supervisor Interno

| Atributo | Valor |
|---|---|
| **ID** | `akiva` |
| **Voz** | Ninguna (sin voz) |
| **Idioma** | Interno |
| **Rol** | Meta-Agent Supervisor |

**Capacidades:**
- Clasificación de intención del mensaje
- Detección de idioma (ES / EN / desconocido)
- Override de emergencia (prioridad alta, ignora idioma)
- Enrutamiento context-aware
- Gestión de estado de sesión entre handoffs

**Handoffs:** Puede derivar a todos los agentes del sistema.

> Akiva nunca habla con el paciente. Es el "cerebro" invisible que decide en milisegundos qué agente debe manejar cada interacción.

---

## 4. Motor de Enrutamiento — Akiva

### Cadena de prioridad

El enrutamiento de Akiva sigue un orden estricto de prioridad:

```
Mensaje del paciente
        │
        ▼
┌───────────────────────────────────────┐
│ 1. ¿Contiene keywords de emergencia?  │──── SÍ ──► Diana (ALTA PRIORIDAD)
│    dolor · pain · sangrado · 7/10...  │           confidence=0.95, override=true
└───────────────────────────────────────┘
        │ NO
        ▼
┌───────────────────────────────────────┐
│ 2. ¿Contiene intención de facturación?│──── SÍ ──► Marco (PRIORIDAD NORMAL)
│    pago · costo · seguro · invoice... │           confidence=0.85
└───────────────────────────────────────┘
        │ NO
        ▼
┌───────────────────────────────────────┐
│ 3. ¿Qué idioma detecta?               │──── ES ──► Alex  (confidence=0.80)
│    Puntuación ES vs EN indicators     │──── EN ──► Nova  (confidence=0.80)
└───────────────────────────────────────┘
        │ DESCONOCIDO
        ▼
┌───────────────────────────────────────┐
│ 4. Default → Alex                     │           confidence=0.50
│   (recepcionista principal)           │
└───────────────────────────────────────┘
```

### Keywords de emergencia (muestra)

**Español:** `dolor`, `urgente`, `sangrado`, `inflamación`, `no puedo respirar`, `fractura`, `severo`

**Inglés:** `pain`, `emergency`, `bleeding`, `swelling`, `severe`, `can't breathe`, `trauma`

**Escala de dolor:** `7/10`, `8/10`, `9/10`, `10/10`

### Detección de idioma

La detección es por puntuación de indicadores lingüísticos. Si el puntaje de ES ≥ EN, se enruta a Alex. Si EN > ES, se enruta a Nova. En empate o sin indicadores, default a Alex.

---

## 5. Marco Ético — Tikun Olam Framework

Este es uno de los diferenciadores más importantes del sistema. Cada respuesta generada por un agente pasa por una **evaluación ética de 5 dimensiones** antes de ser entregada al paciente.

### Las 5 Dimensiones

| Dimensión | Peso | Foco | Proveedor LLM |
|---|---|---|---|
| **Chesed** (Bondad) | 25% | Bienestar emocional y físico del paciente | Gemini |
| **Gevurah** (Límites) | 20% | Límites operativos y clínicos | DeepSeek |
| **Tiferet** (Balance) | 25% | Equilibrio entre todos los intereses | GPT-4o |
| **Netzach** (Efectividad) | 15% | Resolución real de la necesidad | Mistral |
| **Hod** (Honestidad) | 15% | Transparencia y ausencia de manipulación | Grok-3 |

### Umbrales de Aprobación

```
Score ≥ 0.55  →  APPROVED    ✅  Respuesta aprobada para entrega
Score 0.20–0.54 →  CONDITIONAL ⚠️  Requiere modificaciones antes de enviar
Score < 0.20  →  REJECTED    ❌  Debe ser reescrita completamente
Hard Veto = True → REJECTED    ❌  Independientemente del score
```

### Hard Vetoes — Violaciones Críticas

El sistema realiza un escaneo de **veto absoluto** (independiente del score) que bloquea automáticamente respuestas con:

| Veto | Severidad | Descripción |
|---|---|---|
| `attempted_diagnosis` | CRÍTICA | El agente intentó diagnosticar una condición médica |
| `emergency_not_escalated` | CRÍTICA | Emergencia detectada sin derivar a Diana |
| `privacy_violation` | CRÍTICA | Solicitud de SSN, número de tarjeta u otra PII sensible |
| `emotional_manipulation` | ALTA | Lenguaje coercitivo ("si no vienes...", "última oportunidad...") |
| `medical_advice_given` | ALTA | Consejo médico no solicitado ("toma ibuprofeno...") |
| `false_urgency` | MEDIA | Urgencia artificial ("solo hoy", "último lugar") |

### ¿Por qué 5 LLMs distintos en producción?

Cada dimensión es evaluada por un proveedor diferente para eliminar el sesgo de un solo modelo. El **consenso multi-LLM** produce evaluaciones más robustas y difíciles de manipular. En el servidor MCP se usa una implementación heurística determinista que replica los mismos umbrales de decisión.

---

## 6. Herramientas MCP (API)

El servidor expone **7 herramientas** consumibles desde cualquier cliente MCP.

### 6.1 `vocalisai_list_agents`

Lista todos los agentes del registro con roles, idiomas y capacidades.

**Parámetros:**
```json
{
  "include_akiva": true,        // Incluir meta-supervisor (default: true)
  "role_filter": "billing"      // Filtrar por keyword de rol (opcional)
}
```

**Respuesta:**
```json
{
  "total": 7,
  "agents": [...],
  "platform": "VocalisAI V3",
  "deployment": "Google Cloud Run gen2 — us-central1",
  "ethical_engine": "Tikun Olam Framework",
  "mcp_server_version": "1.0.0"
}
```

---

### 6.2 `vocalisai_get_agent`

Retorna el perfil completo de un agente específico.

**Parámetros:**
```json
{
  "agent_id": "diana"   // alex | nova | diana | sara | marco | raul | akiva
}
```

**Respuesta:** JSON con capacidades, voz, idioma, descripción y handoffs configurados.

---

### 6.3 `vocalisai_analyze_call`

**La herramienta más poderosa.** Ejecuta la evaluación ética Tikun Olam sobre un turno de conversación.

**Parámetros:**
```json
{
  "agent_id": "alex",
  "user_message": "Me duele mucho, como 8/10, ¿qué hago?",
  "agent_response": "Entiendo su dolor. La conectaré con Diana inmediatamente.",
  "context": "El paciente llamó hace 3 minutos reportando dolor dental."
}
```

**Respuesta:**
```json
{
  "clearance": "APPROVED",
  "overall_score": 0.872,
  "hard_veto_triggered": false,
  "violations": [],
  "dimensions": {
    "chesed": { "score": 0.88, "assessment": "Empathetic language markers detected..." },
    "gevurah": { "score": 0.82, "assessment": "Response stays within boundaries..." },
    ...
  },
  "recommendation": "Response meets VocalisAI ethical standards."
}
```

---

### 6.4 `vocalisai_route_message`

Simula el enrutamiento Akiva para un mensaje entrante.

**Parámetros:**
```json
{
  "message": "Tengo un dolor terrible, como 9/10, no sé qué hacer",
  "language": "es",   // Opcional. Auto-detectado si se omite
  "explain": true     // Incluir explicación en lenguaje natural
}
```

**Respuesta:**
```json
{
  "routing_decision": {
    "routed_to": "diana",
    "reason": "emergency_keyword_detected",
    "priority": "HIGH",
    "confidence": 0.95,
    "override": true
  },
  "agent_details": { "id": "diana", "role": "Emergency Triage Specialist" },
  "explanation": "Emergency keywords detected. Akiva triggers HIGH-priority override..."
}
```

---

### 6.5 `vocalisai_health_check`

Verifica el estado del servicio en producción (Google Cloud Run).

**Sin parámetros.**

**Respuesta:**
```json
{
  "status": "ok",
  "firebase": true,
  "response_time_ms": 312.4,
  "cold_start": false,
  "endpoint": "https://your-service.run.app/health",
  "checked_at": "2026-04-03T15:30:00Z"
}
```

---

### 6.6 `vocalisai_get_session`

Recupera la transcripción y metadata de una sesión almacenada en Firestore.

**Parámetros:**
```json
{
  "session_id": "session_20260403_153000"
}
```

**Respuesta:** JSON con historial de conversación, agentes involucrados, scores éticos y metadata de la llamada. Las sesiones se almacenan por **90 días**.

---

### 6.7 `vocalisai_platform_info`

Retorna un panorama completo de la plataforma: agentes, framework ético, integraciones, cumplimiento normativo, módulos por industria y versión del servidor MCP.

**Sin parámetros.** Ideal para inicializar el contexto de un LLM.

---

## 7. Recursos MCP

Además de las herramientas, el servidor expone **3 recursos** de solo lectura (acceso eficiente para lookups repetidos):

| URI | Descripción |
|---|---|
| `vocalisai://agents/{agent_id}` | Perfil JSON de un agente específico |
| `vocalisai://ethical-dimensions` | Definición completa de las 5 dimensiones Tikun Olam |
| `vocalisai://platform-info` | Metadata ligera de la plataforma |

---

## 8. Integraciones y Stack Tecnológico

### Stack completo

| Capa | Tecnología |
|---|---|
| **Telefonía** | Twilio Programmable Voice |
| **IA de Voz** | ElevenLabs Conversational AI |
| **IA en Tiempo Real** | Google Gemini Live API |
| **Visión** | Gemini Vision (para triage visual de Diana) |
| **CRM** | GoHighLevel |
| **Base de Datos** | Firebase Firestore |
| **LLM Providers** | Gemini 2.0 Flash, GPT-4o, DeepSeek, Mistral, Grok-3 |
| **Infraestructura** | Google Cloud Run gen2 (us-central1) |
| **Framework MCP** | FastMCP |
| **HTTP Client** | httpx (async) |
| **Validación** | Pydantic v2 + pydantic-settings |
| **Lenguaje** | Python 3.11+ |

### Dependencias del servidor MCP

```toml
mcp>=1.0.0
fastmcp>=0.1.0
httpx>=0.27.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

---

## 9. Cumplimiento Normativo

| Regulación | Estado |
|---|---|
| **HIPAA** (privacidad de datos de salud) | Alineado ✅ |
| **TCPA** (telemarketing) | Cumplido ✅ |
| **DNC Registry** (Do Not Call) | Verificación activa ✅ |
| **PHI Handling** | Encriptado + audit-logged ✅ |

Los hard vetoes del framework Tikun Olam bloquean automáticamente cualquier respuesta que solicite o exponga información sensible (SSN, números de tarjeta), como primera línea de defensa para cumplimiento de HIPAA.

---

## 10. Beneficios y Propuesta de Valor

### Para la clínica dental

| Beneficio | Detalle |
|---|---|
| **Disponibilidad 24/7** | No más llamadas perdidas fuera de horario |
| **Triaje de emergencias correcto** | Diana clasifica y prioriza correctamente, reduciendo riesgo clínico |
| **Verificación de seguros en tiempo real** | Alex lee tarjetas de seguro por OCR durante la llamada |
| **Reducción de no-shows** | Sara y Raúl hacen seguimiento proactivo y recordatorios |
| **Conversión de leads en inglés** | Nova califica pacientes angloparlantes sin barreras |
| **Transparencia en facturación** | Marco explica costos y planes de pago, reduciendo abandono |
| **Cumplimiento ético automático** | Cada respuesta pasa por evaluación antes de llegar al paciente |

### Para equipos de desarrollo e integradores

| Beneficio | Detalle |
|---|---|
| **API estándar MCP** | Integrable con cualquier cliente LLM compatible |
| **Tipado estricto** | Pydantic v2 valida todos los inputs, sin sorpresas |
| **Sin estado en el servidor MCP** | El servidor es stateless; el estado vive en Firestore |
| **Transporte dual** | stdio para local, HTTP para Docker/Cloud |
| **CI/CD incluido** | GitHub Actions con lint (Ruff), tipos (mypy) y tests automáticos |
| **Escaneo de secretos** | TruffleHog integrado en pipeline CI |

### Para la evaluación y auditoría de IA

| Beneficio | Detalle |
|---|---|
| **Evaluación determinista reproducible** | Los mismos inputs producen los mismos resultados |
| **Desglose por dimensión** | Score, peso, contribución y assessment por cada dimensión |
| **Trazabilidad completa** | Cada evaluación incluye timestamp UTC y nombre del agente |
| **Hard vetoes auditables** | Lista explícita de violaciones detectadas en cada análisis |

---

## 11. Casos de Uso y Oportunidades

### Casos de uso inmediatos

#### 1. Integración con Claude Desktop para análisis operativo
Un coordinador de la clínica puede usar Claude Desktop conectado al servidor MCP para:
- Revisar el estado de todos los agentes antes de abrir la clínica
- Analizar conversaciones recientes y verificar que pasaron la evaluación ética
- Simular mensajes de prueba para validar el enrutamiento antes de activar campañas

#### 2. Agente de análisis de calidad en Cursor/Cline
Un equipo de QA puede construir flujos automatizados que:
- Recuperen transcripciones de sesiones del día anterior (`vocalisai_get_session`)
- Las evalúen con Tikun Olam (`vocalisai_analyze_call`)
- Generen reportes de cumplimiento automáticos

#### 3. Dashboard de salud del sistema
Integrar `vocalisai_health_check` en un cron job o dashboard de monitoreo que alerte cuando el servicio Cloud Run esté inaccesible o en cold start.

#### 4. Validación pre-despliegue de scripts de agentes
Antes de actualizar los prompts de un agente, evaluar las nuevas respuestas con `vocalisai_analyze_call` para garantizar que mantengan el estándar ético.

#### 5. Expansión a otras especialidades médicas
Los módulos de industria incluidos soportan: `dental`, `healthcare`, `legal`, `logistics`. El mismo patrón de agentes especializados + evaluación ética puede adaptarse a:
- **Clínicas generales:** triage de síntomas, coordinación con médicos
- **Despachos legales:** calificación de casos, recordatorios de audiencias
- **Logística:** confirmación de entregas, manejo de incidencias

### Oportunidades de expansión

| Oportunidad | Descripción |
|---|---|
| **Más agentes especializados** | Agregar agentes para odontología estética, ortodoncia, implantología con conocimiento específico |
| **Integración con sistemas de citas** | Conexión directa con Dentrix, Eaglesoft o sistemas similares |
| **Análisis de sentimiento en tiempo real** | Agregar scoring de satisfacción del paciente durante la llamada |
| **Multi-clínica** | Akiva puede gestionar routing entre diferentes sucursales |
| **Exportación de métricas** | Pipeline de datos hacia BigQuery para análisis de tendencias |
| **Webhooks de eventos** | Notificaciones en tiempo real a Slack/Teams cuando se detecta una emergencia |

---

## 12. Guía de Implementación en Producción

### Requisitos previos

- Python 3.11 o superior
- Docker (para despliegue en contenedor)
- Cuenta de Google Cloud con Cloud Run habilitado
- Acceso al servidor VocalisAI (URL de Cloud Run + API key si aplica)

---

### Opción A: Instalación local (stdio — Claude Desktop / Cursor)

**Paso 1: Clonar e instalar**

```bash
git clone https://github.com/zoharmx/vocalisai-mcp.git
cd vocalisai-mcp
pip install -e .
```

**Paso 2: Configurar variables de entorno**

```bash
cp .env.example .env
```

Editar `.env`:

```env
VOCALISAI_BASE_URL=https://tu-servicio.run.app
VOCALISAI_API_KEY=tu-api-key-aqui   # Opcional
VOCALISAI_REQUEST_TIMEOUT=15.0
MCP_TRANSPORT=stdio
LOG_LEVEL=INFO
```

**Paso 3: Configurar Claude Desktop**

Agregar en `~/.config/claude/claude_desktop_config.json` (macOS/Linux) o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "vocalisai": {
      "command": "vocalisai-mcp",
      "env": {
        "VOCALISAI_BASE_URL": "https://tu-servicio.run.app",
        "VOCALISAI_API_KEY": "tu-api-key"
      }
    }
  }
}
```

**Paso 4: Reiniciar Claude Desktop**

Las herramientas `vocalisai_*` aparecerán disponibles automáticamente.

---

### Opción B: Docker (HTTP — desarrollo y staging)

**Paso 1: Crear el archivo `.env`** (igual que arriba, con `MCP_TRANSPORT=http`)

**Paso 2: Levantar con Docker Compose**

```bash
docker compose up -d
```

El servidor queda disponible en `http://localhost:8001`.

**Verificar que funciona:**

```bash
curl http://localhost:8001/health
```

**Logs en tiempo real:**

```bash
docker logs -f vocalisai-mcp
```

---

### Opción C: Google Cloud Run (producción)

**Paso 1: Construir y subir imagen**

```bash
gcloud builds submit --tag gcr.io/TU_PROYECTO/vocalisai-mcp:latest
```

**Paso 2: Desplegar en Cloud Run**

```bash
gcloud run deploy vocalisai-mcp \
  --image gcr.io/TU_PROYECTO/vocalisai-mcp:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars "MCP_TRANSPORT=http,VOCALISAI_BASE_URL=https://tu-backend.run.app" \
  --set-secrets "VOCALISAI_API_KEY=vocalisai-api-key:latest" \
  --allow-unauthenticated \
  --port 8080
```

> **Importante:** Cloud Run configura automáticamente la variable `PORT`. El servidor la detecta y la usa en lugar de `MCP_PORT`.

**Paso 3: Verificar el despliegue**

```bash
curl https://tu-mcp-server.run.app/health
```

---

### Configurar Cursor / Cline

Para Cursor, agregar en `.cursor/mcp.json` en la raíz del proyecto:

```json
{
  "mcpServers": {
    "vocalisai": {
      "command": "vocalisai-mcp"
    }
  }
}
```

Para Cline, la configuración es equivalente en su panel de MCP servers.

---

### Ejecutar el servidor directamente (debug)

```bash
# Modo stdio (para pruebas locales)
MCP_TRANSPORT=stdio vocalisai-mcp

# Modo HTTP en puerto 8001
MCP_TRANSPORT=http MCP_PORT=8001 vocalisai-mcp
```

---

### Ejecutar los tests

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Correr toda la suite
pytest tests/ -v

# Solo un módulo
pytest tests/test_ethics.py -v

# Con cobertura
pytest tests/ --cov=vocalisai_mcp
```

**Cobertura de tests incluida:**
- `test_registry.py` — Validación del registro de agentes
- `test_routing.py` — Todos los caminos del router Akiva
- `test_tools.py` — Herramientas MCP
- `test_ethics.py` — Casos del motor Tikun Olam (aprobación, veto, condicional)

---

## 13. Referencia de Configuración

### Variables de entorno completas

| Variable | Default | Descripción |
|---|---|---|
| `VOCALISAI_BASE_URL` | `""` | URL base del servidor VocalisAI en Cloud Run |
| `VOCALISAI_API_KEY` | `None` | API key para endpoints autenticados (opcional) |
| `VOCALISAI_REQUEST_TIMEOUT` | `15.0` | Timeout HTTP en segundos |
| `MCP_TRANSPORT` | `"stdio"` | Modo de transporte: `stdio` o `http` |
| `MCP_PORT` | `8001` | Puerto para modo HTTP (Cloud Run usa `PORT` automáticamente) |
| `LOG_LEVEL` | `"INFO"` | Nivel de logging: DEBUG, INFO, WARNING, ERROR, CRITICAL |

> **Seguridad:** La API key se maneja como `SecretStr` de Pydantic — nunca aparece en logs ni en respuestas de error.

---

## 14. Monitoreo y Operación

### Health Check

El endpoint más importante para monitoreo:

```bash
# Herramienta MCP
vocalisai_health_check()

# HTTP directo
curl https://tu-servicio.run.app/health
```

Respuesta exitosa:
```json
{
  "status": "ok",
  "firebase": true,
  "response_time_ms": 245.0,
  "cold_start": false
}
```

**Cold start:** Cloud Run puede tardar ~10 segundos en la primera solicitud después de inactividad. El health check lo detecta y lo reporta en el campo `cold_start`.

### Logs

El servidor escribe todos los logs a **stderr** (nunca a stdout, que está reservado para el protocolo MCP):

```
2026-04-03 15:30:00 [INFO] vocalisai_mcp: Starting VocalisAI MCP Server v1.0.0 | transport=http host=0.0.0.0 port=8080
2026-04-03 15:30:15 [INFO] vocalisai_mcp: vocalisai_analyze_call | agent=alex clearance=APPROVED score=0.872 veto=False
2026-04-03 15:30:16 [WARNING] vocalisai_mcp: Hard veto triggered: attempted_diagnosis | agent=Alex
```

### Pipeline CI/CD (GitHub Actions)

| Job | Qué hace |
|---|---|
| `lint` | Ruff (estilo + imports) + mypy (tipos estáticos) |
| `test` | pytest en Python 3.11 y 3.12 en paralelo |
| `docker-build` | Valida que la imagen Docker construye correctamente |
| `secrets-scan` | TruffleHog detecta credenciales accidentalmente commiteadas |

---

## 15. Preguntas Frecuentes

**¿Puedo usar el servidor MCP sin el backend VocalisAI?**
Sí, parcialmente. Las herramientas `vocalisai_list_agents`, `vocalisai_get_agent`, `vocalisai_analyze_call`, `vocalisai_route_message` y `vocalisai_platform_info` funcionan completamente offline (no hacen llamadas HTTP). Solo `vocalisai_health_check` y `vocalisai_get_session` requieren conectividad con el backend.

**¿El servidor MCP almacena datos de pacientes?**
No. El servidor MCP es stateless. Todos los datos de sesión y conversaciones viven en Firebase Firestore del backend VocalisAI.

**¿Cómo se actualiza el registro de agentes?**
El registro `AGENTS_REGISTRY` está en `src/vocalisai_mcp/registry.py`. Es la fuente única de verdad. Para agregar un agente, basta con agregar una entrada al diccionario y redesplegar.

**¿Qué pasa si el backend de VocalisAI está caído?**
Las herramientas offline siguen funcionando. Las que requieren HTTP retornan un JSON de error estructurado con el motivo y sugerencias de recuperación, nunca lanzan excepciones sin capturar.

**¿Puede el servidor MCP correr en Windows?**
Sí. Python 3.11+ en Windows es compatible. El modo stdio funciona perfectamente con Claude Desktop para Windows.

**¿El framework Tikun Olam usa LLMs en el servidor MCP?**
No. La implementación en el servidor MCP usa heurísticas deterministas que replican los mismos umbrales que el motor multi-LLM de producción. El motor multi-LLM real (Gemini, GPT-4o, etc.) corre en el backend VocalisAI.

**¿Cómo extender el servidor con nuevas herramientas?**
Agregar una función decorada con `@mcp.tool()` en `server.py`, con su modelo de input Pydantic. FastMCP registra la herramienta automáticamente.

---

*Documentación generada para VocalisAI MCP Server v1.0.0 — Abril 2026*
*Repositorio: https://github.com/zoharmx/vocalisai-mcp*
