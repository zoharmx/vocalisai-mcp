# VocalisAI — Guía Técnica de la Plataforma

**Versión:** 1.0.0 | **Actualizado:** Abril 2026 | **Autor:** Jesus Eduardo Rodriguez  
**Plataforma:** Google Cloud Run gen2 · us-central1 | **Proyecto GCP:** `tikunframework`

---

## Índice

1. [Visión de Arquitectura](#1-visión-de-arquitectura)
2. [Componentes del Sistema](#2-componentes-del-sistema)
3. [MCP Server — Protocolo y Herramientas](#3-mcp-server--protocolo-y-herramientas)
4. [Motor de Enrutamiento — Akiva](#4-motor-de-enrutamiento--akiva)
5. [Marco Ético — Tikun Olam Framework](#5-marco-ético--tikun-olam-framework)
6. [Agentes Especializados — Perfiles Completos](#6-agentes-especializados--perfiles-completos)
7. [Dashboard — Arquitectura y APIs](#7-dashboard--arquitectura-y-apis)
8. [Infraestructura Cloud y CI/CD](#8-infraestructura-cloud-y-cicd)
9. [Seguridad y Cumplimiento](#9-seguridad-y-cumplimiento)
10. [Configuración — Referencia Completa](#10-configuración--referencia-completa)
11. [Testing — Suite y Estrategia](#11-testing--suite-y-estrategia)
12. [Flujos de Llamada — Paso a Paso](#12-flujos-de-llamada--paso-a-paso)
13. [Referencia de APIs del Dashboard](#13-referencia-de-apis-del-dashboard)
14. [Guía de Extensión](#14-guía-de-extensión)

---

## 1. Visión de Arquitectura

VocalisAI V3 es una plataforma de IA de voz multi-agente para clínicas dentales. El sistema se compone de tres capas:

```
╔══════════════════════════════════════════════════════════════════╗
║                     CAPA DE ACCESO                              ║
║                                                                  ║
║  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  ║
║  │  Claude Desktop  │  │  Cursor / Cline  │  │ Custom Agents │  ║
║  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘  ║
║           └────────────────────┼────────────────────┘           ║
║                          stdio / HTTP                           ║
╠══════════════════════════════════════════════════════════════════╣
║                    CAPA DE INTEGRACIÓN MCP                      ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │               vocalisai-mcp  (Cloud Run)                │    ║
║  │  FastMCP 3.x · 7 tools · 3 resources · Pydantic v2     │    ║
║  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    ║
║  │  │ Akiva Router │  │ Tikun Olam   │  │ Agent Registry│  │    ║
║  │  │ (local sim.) │  │ Engine (heur)│  │ (source truth)│  │    ║
║  │  └──────────────┘  └──────────────┘  └──────────────┘  │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │            vocalisai-dashboard  (Cloud Run)             │    ║
║  │  FastAPI · 11 endpoints · SPA mobile-first · Chart.js  │    ║
║  └─────────────────────────────────────────────────────────┘    ║
╠══════════════════════════════════════════════════════════════════╣
║                   CAPA DE PLATAFORMA DE VOZ                     ║
║                                                                  ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │              vocalis-ai-v3  (Cloud Run)                  │   ║
║  │                                                          │   ║
║  │  Twilio ──► Gemini Live 2.5 Flash ──► Agentes IA       │   ║
║  │  ElevenLabs TTS          Akiva Router                    │   ║
║  │  Gemini Vision           Tikun Olam (multi-LLM)         │   ║
║  │  GoHighLevel CRM         Firebase Firestore              │   ║
║  └──────────────────────────────────────────────────────────┘   ║
║                                                                  ║
║          Vertex AI — us-central1 — proyecto: tikunframework      ║
╚══════════════════════════════════════════════════════════════════╝
```

### Principios de diseño

| Principio | Implementación |
|---|---|
| **Separación de capas** | MCP server, dashboard y plataforma de voz son servicios independientes en Cloud Run |
| **Stateless por diseño** | El MCP server y el dashboard son completamente stateless; el estado vive en Firestore |
| **Evaluación ética obligatoria** | Ninguna respuesta llega al paciente sin pasar por Tikun Olam |
| **Zero secrets en código** | Todo valor sensible viene de variables de entorno o Secret Manager |
| **Least privilege** | Service Account de CI/CD tiene exactamente 3 roles (AR writer + CR admin + SA user) |

---

## 2. Componentes del Sistema

### 2.1 `vocalisai-mcp` — MCP Server

**Propósito:** Exponer la plataforma VocalisAI como herramientas MCP para LLMs.

**Tecnologías:** FastMCP 3.x · Python 3.11 · Pydantic v2 · httpx async

**Transportes:**
- `stdio` — para Claude Desktop, Cursor, Cline (predeterminado)
- `http` — para Docker, Cloud Run, clientes remotos (`MCP_TRANSPORT=http`)

**Módulos internos:**

```
server.py     → Punto de entrada. Define los 7 tools y 3 resources con FastMCP.
registry.py   → Fuente única de verdad: agentes, dimensiones éticas, catálogo de vetoes.
routing.py    → Motor Akiva: cadena de prioridad (emergencia → facturación → idioma → default).
ethics.py     → Motor Tikun Olam: evaluación heurística de 5 dimensiones + hard vetoes.
client.py     → Cliente HTTP async con httpx: auth, timeout, detección de cold start.
config.py     → Configuración via pydantic-settings. SecretStr para API key.
__main__.py   → Permite `python -m vocalisai_mcp`.
```

### 2.2 `vocalisai-dashboard` — Panel de Control

**Propósito:** Monitoreo en tiempo real, análisis de llamadas y simulador en vivo.

**Tecnologías:** FastAPI · uvicorn · Chart.js 4 · Vanilla JS · CSS mobile-first

**Endpoint base:** `https://vocalisai-dashboard-hzz2wlra6a-uc.a.run.app`

### 2.3 `vocalis-ai-v3` — Plataforma de Voz

**Propósito:** Backend principal. Procesa llamadas de voz, orquesta agentes, evalúa éticamente.

**Endpoint base:** `https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app`

**Live agent:** `.../static/live_agent.html` — interfaz web de voz con Gemini Live

---

## 3. MCP Server — Protocolo y Herramientas

### 3.1 ¿Qué es MCP?

El **Model Context Protocol** (Anthropic, 2024) es un estándar abierto que permite a modelos de lenguaje conectarse con sistemas externos de forma tipificada y segura. El servidor MCP actúa como un "plugin" que los LLMs pueden descubrir y usar sin necesidad de fine-tuning.

### 3.2 Inicialización del servidor

```python
from fastmcp import FastMCP

mcp = FastMCP(
    "vocalisai_mcp",
    instructions=(
        "VocalisAI MCP Server — plataforma multi-agente de voz para salud dental. "
        "Usa estas herramientas para inspeccionar agentes, evaluar conversaciones "
        "éticamente (Tikun Olam), simular enrutamiento (Akiva), recuperar sesiones "
        "y verificar la salud de la plataforma."
    ),
)
```

### 3.3 Herramientas (7)

Todas las herramientas usan modelos Pydantic con `ConfigDict(extra="forbid")` para validación estricta de inputs. Los errores de validación retornan mensajes estructurados, nunca excepciones crudas.

#### `vocalisai_list_agents`
```
Tipo:       READ-ONLY · IDEMPOTENT
Input:      include_akiva: bool = True
            role_filter: str | None  (ej: "billing", "triage", "outbound")
Output:     JSON con total, lista de agentes, metadata de plataforma
Propósito:  Contexto inicial para LLMs. Retorna el registro completo de agentes.
```

#### `vocalisai_get_agent`
```
Tipo:       READ-ONLY · IDEMPOTENT
Input:      agent_id: str  (alex|nova|diana|sara|marco|raul|akiva)
Output:     JSON con perfil completo: capacidades, voz, idioma, handoffs
Error:      JSON con "error" y lista de IDs válidos si el agente no existe
```

#### `vocalisai_analyze_call`  ⭐ Herramienta principal
```
Tipo:       READ-ONLY · NO IDEMPOTENTE (timestamp varía)
Input:      agent_id: str
            user_message: str  (1-2000 chars)
            agent_response: str  (1-2000 chars)
            context: str | None  (hasta 4000 chars de contexto previo)
Output:     JSON con:
            - clearance: "APPROVED" | "CONDITIONAL" | "REJECTED"
            - overall_score: float (0.0 – 1.0)
            - hard_veto_triggered: bool
            - violations: list[str]
            - dimensions: {chesed, gevurah, tiferet, netzach, hod} con score,
                          weight, weighted_contribution, focus, provider, assessment
            - recommendation: str
            - engine: "Tikun Olam Framework — VocalisAI MCP v1.0"
```

#### `vocalisai_route_message`
```
Tipo:       READ-ONLY · IDEMPOTENTE
Input:      message: str  (1-2000 chars)
            language: "es" | "en" | None  (None = auto-detect)
            explain: bool = True
Output:     JSON con routing_decision (routed_to, reason, priority, confidence,
            detected_language, override) + agent_details + explanation
```

#### `vocalisai_health_check`
```
Tipo:       READ-ONLY · IDEMPOTENTE · OPEN WORLD (hace HTTP al backend)
Input:      ninguno
Output:     JSON con status, firebase, response_time_ms, cold_start, endpoint
Nota:       cold_start = True si response_time_ms > 3000
```

#### `vocalisai_get_session`
```
Tipo:       READ-ONLY · IDEMPOTENTE · OPEN WORLD
Input:      session_id: str  (formato: session_YYYYMMDD_HHMMSS o Firestore doc ID)
Output:     JSON con transcripción, historial de agentes, scores éticos, metadata
Retención:  Sesiones disponibles 90 días en Firestore
```

#### `vocalisai_platform_info`
```
Tipo:       READ-ONLY · IDEMPOTENTE
Input:      ninguno
Output:     JSON completo: agentes, framework ético, proveedores LLM, integraciones,
            cumplimiento normativo, módulos por industria, versión del servidor
Uso:        Inicialización de contexto para LLMs en el primer mensaje
```

### 3.4 Recursos MCP (3)

Los recursos son accesibles vía URI y están optimizados para lookups repetidos (sin overhead de tool call):

```
vocalisai://agents/{agent_id}      → GET perfil del agente como JSON
vocalisai://ethical-dimensions     → GET definición de las 5 dimensiones
vocalisai://platform-info          → GET metadata ligera de la plataforma
```

### 3.5 Anotaciones de herramientas

Cada herramienta lleva anotaciones estándar MCP que ayudan a los clientes a entender su comportamiento:

```python
annotations={
    "readOnlyHint": True,       # no modifica estado
    "destructiveHint": False,   # segura de ejecutar
    "idempotentHint": True,     # resultado reproducible
    "openWorldHint": False,     # no hace llamadas externas (False en offline tools)
}
```

---

## 4. Motor de Enrutamiento — Akiva

Akiva es el meta-supervisor invisible. Analiza cada mensaje entrante y decide en milisegundos qué agente especializado debe manejarlo.

### 4.1 Cadena de prioridad

```
MENSAJE DEL PACIENTE
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ PASO 1: Scan de emergencias                                   │
│                                                               │
│ Keywords ES: dolor · urgente · sangrado · inflamación ·       │
│              no puedo respirar · accidente · golpe · fractura │
│ Keywords EN: pain · emergency · bleeding · swelling · severe  │
│              can't breathe · accident · trauma · fracture     │
│ Escala:      7/10 · 8/10 · 9/10 · 10/10                      │
│                                                               │
│ → HIT: routed_to=diana, priority=HIGH, confidence=0.95       │
│         override=True (ignora idioma completamente)           │
└───────────────────────────────────────────────────────────────┘
        │ MISS
        ▼
┌───────────────────────────────────────────────────────────────┐
│ PASO 2: Detección de intención de facturación                 │
│                                                               │
│ Keywords ES: pago · costo · precio · factura · seguro ·       │
│              cobertura · cuánto cuesta · plan de pago         │
│ Keywords EN: payment · cost · price · invoice · insurance ·   │
│              coverage · how much · payment plan · balance     │
│                                                               │
│ → HIT: routed_to=marco, priority=NORMAL, confidence=0.85     │
└───────────────────────────────────────────────────────────────┘
        │ MISS
        ▼
┌───────────────────────────────────────────────────────────────┐
│ PASO 3: Detección de idioma por scoring de indicadores        │
│                                                               │
│ Indicadores ES: hola · buenos · necesito · quiero · cita ·   │
│                 por favor · gracias · dentista · consulta     │
│ Indicadores EN: hello · hi · need · want · appointment ·     │
│                 insurance · please · dental · can i           │
│                                                               │
│ score_es >= score_en → routed_to=alex, detected_language=es  │
│ score_en >  score_es → routed_to=nova, detected_language=en  │
│ confidence = 0.80                                             │
└───────────────────────────────────────────────────────────────┘
        │ Sin indicadores detectados
        ▼
┌───────────────────────────────────────────────────────────────┐
│ PASO 4: Default → Alex (recepcionista principal)              │
│ detected_language=unknown · confidence=0.50                   │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 `RoutingDecision` — Estructura de salida

```python
@dataclass
class RoutingDecision:
    routed_to:         str    # "alex" | "nova" | "diana" | "marco"
    reason:            str    # "emergency_keyword_detected" | "billing_intent_detected"
                               # | "spanish_language_detected" | "english_language_detected"
                               # | "default_routing"
    priority:          str    # "HIGH" | "NORMAL"
    detected_language: str    # "es" | "en" | "unknown"
    override:          bool   # True = emergencia anuló la lógica de idioma
    confidence:        float  # 0.0 – 1.0
```

### 4.3 Hint de idioma explícito

Si el cliente envía `language="es"` o `language="en"`, ese valor tiene precedencia total sobre la detección automática pero **NO** tiene precedencia sobre el override de emergencia.

```python
# Emergencia siempre gana, incluso con hint explícito
decision = router.route("I need emergency help, severe pain", language_hint="en")
assert decision.routed_to == "diana"   # override=True
assert decision.detected_language == "en"  # el idioma sí se detecta correctamente
```

---

## 5. Marco Ético — Tikun Olam Framework

El framework Tikun Olam (תיקון עולם, "reparación del mundo") es el sistema de evaluación ética que garantiza que ninguna respuesta generada por un agente IA cause daño al paciente.

### 5.1 Dos etapas de evaluación

```
RESPUESTA DEL AGENTE
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 0: Hard Veto Scan                                     │
│ Escaneo determinista de patrones prohibidos                 │
│                                                             │
│ Si algún veto se activa → clearance=REJECTED inmediatamente │
│ Todos los scores de dimensión se suprimen a ≤ 0.10          │
└─────────────────────────────────────────────────────────────┘
        │ Sin vetoes
        ▼
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 1: Scoring por dimensión (5 dimensiones)              │
│                                                             │
│ Marcadores detectados:                                      │
│ - has_empathy: palabras de empatía en la respuesta         │
│ - has_action: palabras de acción/resolución                 │
│ - is_concise: len(respuesta) < 500 chars                   │
│ - stays_in_bounds: sin intentos de diagnóstico             │
│                                                             │
│ Score = f(marcadores, dimensión, violaciones_activas)       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 2: Decisión de clearance                              │
│                                                             │
│ overall = Σ(score_dim × weight_dim)                         │
│                                                             │
│ hard_veto=True OR overall < 0.20  →  REJECTED              │
│ overall < 0.55                    →  CONDITIONAL            │
│ overall ≥ 0.55                    →  APPROVED               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Las 5 Dimensiones en detalle

#### Chesed (חֶסֶד) — Bondad · Peso: 25%
**Proveedor:** Gemini | **Foco:** Bienestar emocional y físico del paciente

Evalúa si el agente reconoce el estado emocional del paciente, usa lenguaje cálido y empático, y no descarta sus preocupaciones.

```python
# Marcadores de empatía detectados por la implementación heurística:
EMPATHY_MARKERS = {
    "entiendo", "i understand", "lo siento", "i'm sorry",
    "gracias", "thank you", "comprendo", "claro que sí",
    "con gusto", "con mucho gusto", "lamentamos", "we're sorry",
}

# Score: 0.88 si has_empathy=True · 0.58 si has_empathy=False
```

#### Gevurah (גְּבוּרָה) — Disciplina · Peso: 20%
**Proveedor:** DeepSeek | **Foco:** Límites operativos y clínicos

Evalúa si el agente se mantiene dentro del ámbito administrativo-receptivo, redirige preguntas clínicas a profesionales y no intenta diagnosticar.

```python
CLINICAL_BOUNDARY_VIOLATIONS = {
    "you have", "you definitely have", "it's definitely",
    "diagnos", "es definitivamente", "tienes ",
}
# Score: 0.15 si viola el límite · 0.82 si se mantiene en bounds
```

#### Tiferet (תִּפְאֶרֶת) — Armonía · Peso: 25%
**Proveedor:** GPT-4o | **Foco:** Balance entre todos los intereses

Evalúa si la respuesta equilibra las necesidades del paciente, las operaciones de la clínica y las obligaciones éticas.

```
has_empathy AND has_action  → 0.85  (balance completo)
has_empathy OR  has_action  → 0.68  (balance parcial)
ninguno                     → 0.52  (balance débil)
```

#### Netzach (נֶצַח) — Perseverancia · Peso: 15%
**Proveedor:** Mistral | **Foco:** Resolución efectiva del problema

Evalúa si la interacción realmente resuelve la necesidad del paciente con un siguiente paso claro.

```
has_action = True  → 0.87  (ruta de resolución clara)
has_action = False → 0.52  (paciente sin guía sobre qué hacer)
```

#### Hod (הוֹד) — Gloria/Honestidad · Peso: 15%
**Proveedor:** Grok-3 | **Foco:** Transparencia y ausencia de manipulación

Evalúa si la respuesta es veraz, transparente y no usa técnicas de urgencia artificial o manipulación.

```
has_false_urgency = True  → 0.20  (transparencia comprometida)
is_concise = True         → 0.90  (claro y directo)
is_concise = False        → 0.72  (verboso, considerar reducir)
```

### 5.3 Catálogo de Hard Vetoes

Los hard vetoes son verificaciones binarias que se evalúan antes del scoring. Si cualquiera se activa, la respuesta es **RECHAZADA** independientemente del score.

| ID | Severidad | Lógica de detección |
|---|---|---|
| `attempted_diagnosis` | CRÍTICA | Keywords como "you have", "tienes", "diagnos" en la RESPUESTA |
| `emergency_not_escalated` | CRÍTICA | Palabras de emergencia severa en el MENSAJE + ausencia de "diana"/"emergency" en la RESPUESTA |
| `privacy_violation` | CRÍTICA | Keywords como "ssn", "social security", "credit card" en la RESPUESTA |
| `emotional_manipulation` | ALTA | Keywords coercitivos como "you must come now or", "si no vienes" en la RESPUESTA |
| `medical_advice_given` | ALTA | Keywords como "toma ibuprofeno", "take ibuprofen", "aplica" en la RESPUESTA |
| `false_urgency` | MEDIA | Keywords como "only today", "solo hoy", "último lugar" en la RESPUESTA |

### 5.4 Implementación: heurística vs. multi-LLM

El servidor MCP implementa una versión **heurística determinista** del motor que replica los mismos umbrales de decisión que el motor multi-LLM en producción:

```
MCP Server (local)              Producción (vocalis-ai-v3)
─────────────────               ─────────────────────────
TikunOlamEngine                 Multi-LLM Consensus Engine
  ↓                               ↓
Heurísticas deterministas       Chesed   → Gemini
Mismos umbrales: 0.55/0.20      Gevurah  → DeepSeek
Mismo catálogo de vetoes        Tiferet  → GPT-4o
                                Netzach  → Mistral
                                Hod      → Grok-3
```

La ventaja de la implementación heurística en el MCP es que funciona **offline**, sin necesidad de llamadas a LLMs externos, y tiene latencia de microsegundos.

---

## 6. Agentes Especializados — Perfiles Completos

### Alex — Recepcionista Principal ES-MX

```yaml
id: alex
language: ES-MX
voice: Puck (ElevenLabs)
role: Dental Receptionist
capabilities:
  - appointment_scheduling    # integración con GoHighLevel CRM
  - insurance_card_ocr        # lee tarjetas de seguro durante la llamada con Gemini Vision
  - emergency_detection       # detecta dolor ≥ 7/10 → handoff a Diana
  - patient_intake            # captación de nuevos pacientes
handoffs:
  diana: cuando dolor reportado ≥ 7/10
  marco: cuando pregunta sobre costos o seguros
entry_condition: idioma español detectado (default)
```

**Funcionalidad destacada:** Durante una llamada activa, Alex puede pedir al paciente que tome foto de su tarjeta de seguro y envíe por SMS. La plataforma procesa la imagen con Gemini Vision en tiempo real y extrae nombre, número de póliza y cobertura — reduciendo el proceso de verificación de 10 minutos a 15 segundos.

### Nova — Calificadora EN-US

```yaml
id: nova
language: EN-US
voice: Kore (ElevenLabs)
role: English Qualifier
capabilities:
  - lead_qualification        # filtra pacientes con intención real de tratamiento
  - insurance_verification    # verifica cobertura en tiempo real
  - patient_intake_english    # onboarding para pacientes angloparlantes
handoffs:
  alex: cuando el paciente quiere agendar
  marco: cuando pregunta sobre costos
entry_condition: idioma inglés detectado
```

### Diana — Especialista en Triage de Emergencias

```yaml
id: diana
language: Bilingüe (ES + EN)
voice: Aoede (ElevenLabs)
role: Emergency Triage Specialist
capabilities:
  - pain_assessment           # escala 1-10, clasificación de severidad
  - visual_triage             # análisis de fotos del paciente con Gemini Vision
  - first_aid_instructions    # instrucciones de primeros auxilios pre-clínica
  - emergency_appointment_booking  # agenda citas same-day a través de Alex
  - clinical_image_analysis   # análisis de radiografías o fotos de lesiones
handoffs:
  alex: para confirmar y agendar la cita de emergencia
entry_condition: override de emergencia por Akiva (priority=HIGH)
```

**Funcionalidad destacada:** Diana puede solicitar al paciente que tome y envíe una fotografía de la zona afectada durante la llamada. Gemini Vision analiza la imagen en tiempo real y clasifica la severidad (inflamación, sangrado, fractura visible) para informar las instrucciones de primeros auxilios y la urgencia de la cita.

### Sara — Coordinadora de Seguimiento Post-Visita

```yaml
id: sara
language: Bilingüe
voice: Aoede (ElevenLabs)
role: Post-Visit Follow-up Coordinator
capabilities:
  - complication_detection    # detecta síntomas de complicaciones post-procedimiento
  - patient_reengagement      # reactiva pacientes que no se presentaron (no-shows)
  - satisfaction_survey       # encuestas CSAT y NPS automatizadas
handoffs:
  diana: si detecta complicación que requiere triage
  alex:  si el paciente quiere reagendar
trigger: llamada automática 24-48h después de procedimientos
```

### Marco — Especialista en Facturación

```yaml
id: marco
language: Bilingüe
voice: Fenrir (ElevenLabs)
role: Billing Specialist
capabilities:
  - cost_explanation          # explica desglose de costos por tratamiento
  - payment_plans             # configura planes de pago (12/24/36 meses)
  - insurance_claim_assistance # guía al paciente en el proceso de reclamación
handoffs: []                  # agente terminal — no hace handoffs
entry_condition: intención de facturación detectada por Akiva
```

### Raúl — Coordinador de Campañas Salientes

```yaml
id: raul
language: Bilingüe
voice: Puck (ElevenLabs)
role: Outbound Coordinator
capabilities:
  - reactivation_campaigns    # contacta pacientes inactivos (6+ meses sin visita)
  - appointment_reminders     # recordatorios 24h y 1h antes de la cita
  - patient_engagement        # engagement proactivo con base de pacientes
handoffs:
  alex: cuando el paciente quiere agendar en respuesta a la campaña
trigger: campañas programadas, listas de Firestore
```

### Akiva — Meta-Supervisor Interno

```yaml
id: akiva
language: Internal (no habla con pacientes)
voice: null
role: Meta-Agent Supervisor
capabilities:
  - intent_classification     # clasifica la intención del mensaje
  - language_detection        # ES vs EN vs unknown con scoring de indicadores
  - emergency_override        # activa prioridad HIGH en situaciones críticas
  - context_aware_routing     # mantiene el contexto entre turnos de conversación
  - session_state_management  # gestiona el estado de sesión entre handoffs
handoffs: [alex, nova, diana, sara, marco, raul]  # puede enrutar a cualquier agente
visibility: invisible para el paciente
```

---

## 7. Dashboard — Arquitectura y APIs

### 7.1 Arquitectura del dashboard

```
vocalisai-dashboard (Cloud Run)
├── FastAPI (server.py)
│   ├── GET  /                     → FileResponse(index.html)
│   ├── GET  /api/overview          → KPIs: llamadas, agentes, ética, emergencias
│   ├── GET  /api/agents            → Registro completo con stats semanales
│   ├── GET  /api/calls/timeline    → Volumen horario (últimas 24h)
│   ├── GET  /api/calls/trend       → Totales diarios (últimos 7 días)
│   ├── GET  /api/calls/recent      → Últimas N llamadas con metadata
│   ├── GET  /api/routing/distribution → Distribución de agentes esta semana
│   ├── GET  /api/routing/language  → Split ES/EN/desconocido
│   ├── GET  /api/ethics/summary    → Scores, clearance, veto counts
│   ├── GET  /api/health            → Health check real vs Cloud Run
│   ├── POST /api/simulate/route    → Akiva routing en vivo
│   └── POST /api/simulate/ethics   → Tikun Olam evaluation en vivo
│
├── metrics.py
│   └── Generación determinista de datos de ejemplo y simulados
│
└── static/index.html (SPA mobile-first)
    ├── 7 secciones navegables
    ├── Chart.js 4 (6 tipos de gráficas)
    ├── Bottom nav (móvil) + sidebar (desktop)
    ├── FAB "📲 Agente Vivo"
    └── iframe: vocalis-ai-v3/static/live_agent.html
```

### 7.2 Diseño responsive

El dashboard usa **CSS mobile-first** con un único breakpoint en 768px:

```css
/* Mobile (default): bottom nav, single column */
.bottom-nav { display: flex; }
.sidebar    { display: none; }
.kpi-grid   { grid-template-columns: 1fr 1fr; }

/* Desktop (≥768px): sidebar, multi-column */
@media (min-width: 768px) {
  .bottom-nav { display: none; }
  .sidebar    { display: flex; width: 224px; }
  .kpi-grid   { grid-template-columns: repeat(4, 1fr); }
}
```

**Touch targets:** mínimo 44px (estándar Apple HIG)  
**iOS safe area:** `env(safe-area-inset-bottom)` para iPhones con notch  
**Scroll iOS:** `-webkit-overflow-scrolling: touch`

### 7.3 Sección "Agente en Vivo"

La sección `live` embebe la plataforma real usando un iframe:

```html
<iframe
  id="live-iframe"
  src="https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app/static/live_agent.html"
  allow="microphone; camera; autoplay; clipboard-write"
  allowfullscreen>
</iframe>
```

No hay restricciones de X-Frame-Options en el servidor de origen, por lo que el embedding funciona directamente. El usuario puede:
- Interactuar con el agente en vivo dentro del dashboard
- Abrir en pantalla completa para experiencia óptima en móvil
- Reiniciar el iframe si la conexión se interrumpe

---

## 8. Infraestructura Cloud y CI/CD

### 8.1 Servicios Cloud Run en producción

| Servicio | Imagen | CPU | Memoria | Min inst. | Max inst. | Concurrencia |
|---|---|---|---|---|---|---|
| `vocalisai-mcp` | `vocalis/vocalisai-mcp` | 1 | 512Mi | 0 | auto | 80 |
| `vocalisai-dashboard` | `vocalis/vocalisai-dashboard` | 1 | 512Mi | 0 | 3 | 80 |
| `vocalis-ai-v3` | `vocalis/vocalis-ai-v3` | variable | variable | variable | variable | variable |

**Artifact Registry:** `us-central1-docker.pkg.dev/tikunframework/vocalis/`

### 8.2 Dockerfile multi-servicio

El proyecto usa **un único Dockerfile** para ambos servicios MCP y Dashboard, controlado por la variable `SERVICE`:

```dockerfile
FROM python:3.11-slim

# deps + source
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER vocalis

ENV SERVICE=mcp          # "mcp" | "dashboard"
ENV PYTHONPATH=/app/src

ENTRYPOINT ["/app/entrypoint.sh"]
```

```bash
# entrypoint.sh
case "${SERVICE:-mcp}" in
  dashboard) exec python -m vocalisai_mcp.dashboard.server ;;
  mcp)       exec python -m vocalisai_mcp.server ;;
esac
```

### 8.3 Gestión de puertos

Cloud Run siempre inyecta `PORT` en el contenedor. El código respeta este orden:

```python
# MCP Server (server.py)
port = int(os.environ.get("PORT", settings.mcp_port))

# Dashboard (dashboard/server.py)
port = int(os.environ.get("PORT", os.environ.get("MCP_DASHBOARD_PORT", 8080)))
```

### 8.4 Pipelines CI/CD

#### CI — `.github/workflows/ci.yml`

Se ejecuta en cada push a `main`/`develop` y en Pull Requests:

```
Lint (ruff check + ruff format --check)
Type check (mypy src/vocalisai_mcp/ --strict)
Tests (pytest en Python 3.11 y 3.12 en paralelo)
Docker build validation
Secret scan (TruffleHog — solo secretos verificados)
```

#### Deploy Dashboard — `.github/workflows/deploy-dashboard.yml`

Se ejecuta en push a `master` cuando hay cambios en el dashboard:

```
1. Autenticación GCP con Service Account (GCP_SA_KEY secret)
2. docker build → push a Artifact Registry
3. gcloud run deploy vocalisai-dashboard
4. Imprimir URL del servicio desplegado
```

**Configuración requerida en GitHub (sin hardcoding):**

| Tipo | Nombre | Valor |
|---|---|---|
| Variable | `GCP_PROJECT` | ID del proyecto GCP |
| Variable | `GCP_REGION` | Región (ej: `us-central1`) |
| Variable | `GCP_AR_REPO` | Nombre del repo en Artifact Registry |
| Secret | `GCP_SA_KEY` | JSON del Service Account |
| Secret | `VOCALISAI_BASE_URL` | URL de la plataforma de voz |

### 8.5 Service Account de CI/CD (least-privilege)

```
github-deploy@tikunframework.iam.gserviceaccount.com

Roles asignados:
  roles/artifactregistry.writer  → push de imágenes Docker
  roles/run.admin                → desplegar servicios en Cloud Run
  roles/iam.serviceAccountUser   → actuar como SA de Cloud Run
```

---

## 9. Seguridad y Cumplimiento

### 9.1 Manejo de secretos

| Nivel | Mecanismo |
|---|---|
| Código fuente | Zero secrets — todas las variables son env vars |
| Runtime local | `.env` (en `.gitignore` · nunca se commitea) |
| Runtime Docker | `env_file: .env` en docker-compose |
| GitHub Actions | Secrets encriptados de GitHub |
| Cloud Run | Variables de entorno + Secret Manager references |
| API Key | `SecretStr` de Pydantic → nunca aparece en logs ni serialización |

### 9.2 Container security

```dockerfile
# Usuario no-root en el contenedor
RUN groupadd -r vocalis && useradd -r -g vocalis vocalis
USER vocalis
```

### 9.3 Cumplimiento normativo

**HIPAA (Health Insurance Portability and Accountability Act)**
- Información del paciente (PHI) encriptada en tránsito (TLS) y en reposo (Firestore encryption)
- Audit log de cada acceso a datos de paciente
- Hard vetoes bloquean solicitudes de SSN y números de tarjeta de crédito

**TCPA (Telephone Consumer Protection Act)**
- Verificación de DNC (Do Not Call Registry) antes de llamadas salientes
- Consentimiento registrado en Firestore antes de contactar pacientes

**Validación de inputs**
- Todos los inputs del MCP server pasan por Pydantic con `extra="forbid"`
- Límites de longitud en todos los campos de texto
- No hay interpolación de SQL o comandos del sistema

### 9.4 CORS y aislamiento del dashboard

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # ajustar a dominios específicos en producción sensitiva
    allow_methods=["*"],
    allow_headers=["*"],
)
```

El dashboard no expone datos reales de pacientes — usa datos representativos generados determinísticamente. Los únicos endpoints con datos reales son `health` (metadata del servicio) y `simulate/*` (evaluaciones locales sin datos de paciente).

---

## 10. Configuración — Referencia Completa

### 10.1 Todas las variables de entorno

```bash
# ── Plataforma VocalisAI ─────────────────────────────────────────
VOCALISAI_BASE_URL=https://tu-plataforma.run.app   # URL del backend de voz
VOCALISAI_API_KEY=                                  # API key (opcional)
VOCALISAI_REQUEST_TIMEOUT=15.0                      # timeout HTTP en segundos

# ── Transporte MCP ───────────────────────────────────────────────
MCP_TRANSPORT=stdio        # "stdio" (local) | "http" (Docker/Cloud Run)
MCP_PORT=8001              # puerto en modo HTTP

# ── Dashboard ────────────────────────────────────────────────────
SERVICE=mcp                # "mcp" | "dashboard" (para Docker multi-servicio)
MCP_DASHBOARD_PORT=8080    # puerto del dashboard (local, override por PORT)
PORT=                      # inyectado por Cloud Run — tiene prioridad sobre todo

# ── Logging ──────────────────────────────────────────────────────
LOG_LEVEL=INFO             # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

### 10.2 Configuración para Claude Desktop

**macOS/Linux:** `~/.config/claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vocalisai": {
      "command": "vocalisai-mcp",
      "env": {
        "VOCALISAI_BASE_URL": "https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app",
        "LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

### 10.3 Configuración para Cursor

`.cursor/mcp.json` en la raíz del proyecto:

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

### 10.4 Docker Compose (stack local completo)

```yaml
services:
  mcp:
    build: .
    ports: ["8001:8001"]
    env_file: .env
    environment:
      SERVICE: mcp
      MCP_TRANSPORT: http
      PORT: "8001"

  dashboard:
    build: .
    ports: ["8080:8080"]
    env_file: .env
    environment:
      SERVICE: dashboard
      PORT: "8080"
    depends_on:
      mcp:
        condition: service_healthy
```

---

## 11. Testing — Suite y Estrategia

### 11.1 Estructura de tests

```
tests/
├── conftest.py          # fixtures compartidos: TikunOlamEngine, AkivaRouter
├── test_routing.py      # motor Akiva — todos los caminos de prioridad
├── test_ethics.py       # motor Tikun Olam — aprobación, veto, condicional
├── test_tools.py        # herramientas MCP — inputs, outputs, errores
└── test_registry.py     # registro de agentes — integridad de datos
```

### 11.2 Casos de test por módulo

**test_routing.py — 18 tests**
```
TestEmergencyOverride:
  ✓ 7 mensajes de emergencia en ES y EN → diana, HIGH, override=True
  ✓ Emergency override ignora language hint explícito

TestBillingRouting:
  ✓ 5 mensajes de facturación → marco, NORMAL, override=False
  ✓ Emergency siempre gana sobre billing (test de prioridad)

TestLanguageRouting:
  ✓ 4 mensajes ES/EN → alex/nova respectivamente
  ✓ language_hint="es" → alex (aunque mensaje en inglés)
  ✓ language_hint="en" → nova (aunque mensaje en español)

TestDefaultRouting:
  ✓ Mensaje sin indicadores → alex, detected_language=unknown, confidence≤0.5

TestExplanations:
  ✓ explanation() retorna string > 10 chars
  ✓ Emergency explanation menciona Diana
  ✓ Billing explanation menciona Marco

TestRoutingDecisionToDict:
  ✓ to_dict() tiene todas las claves requeridas
  ✓ confidence ∈ [0.0, 1.0]
```

**test_ethics.py — 16 tests**
```
TestApprovedResponses:
  ✓ Respuesta empática de agenda → APPROVED, score≥0.55
  ✓ Respuesta empática en inglés → APPROVED
  ✓ Las 5 dimensiones siempre presentes en el output
  ✓ Suma de pesos = 1.0 exactamente

TestHardVetoTriggers:
  ✓ Intento de diagnóstico → REJECTED, violations=["attempted_diagnosis"]
  ✓ Consejo médico → REJECTED
  ✓ Urgencia falsa → hard_veto_triggered=True
  ✓ Emergencia no escalada → REJECTED, violations=["emergency_not_escalated"]
  ✓ Veto activo suprime todos los scores de dimensión a ≤ 0.15

TestConditionalClearance:
  ✓ Respuesta sin empatía ni acción < respuesta completa (comparativo)
  ✓ Respuesta verbose sin empatía → chesed, tiferet, netzach < 0.70

TestTimestamp:
  ✓ timestamp es ISO 8601 en UTC (termina en +00:00 o Z)

TestToDictOutput:
  ✓ to_dict() contiene las 9 claves requeridas
  ✓ overall_score ∈ [0.0, 1.0]
```

### 11.3 Ejecutar los tests

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Suite completa con output detallado
pytest tests/ -v

# Con cobertura de código
pytest tests/ --cov=vocalisai_mcp --cov-report=html

# Solo un módulo específico
pytest tests/test_ethics.py -v -k "TestHardVetoTriggers"

# En modo paralelo (si se instala pytest-xdist)
pytest tests/ -n auto
```

### 11.4 Linting y tipos

```bash
# Ruff (linter + formatter)
ruff check src/ tests/          # detectar problemas
ruff format --check src/ tests/ # verificar formato
ruff format src/ tests/         # aplicar formato

# Mypy (type checking estricto)
mypy src/vocalisai_mcp/ --strict

# Todo en un comando
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/vocalisai_mcp/
```

---

## 12. Flujos de Llamada — Paso a Paso

### Flujo 1: Paciente español agenda cita

```
1. Twilio recibe llamada
2. Akiva analiza primer mensaje: "Hola, necesito una cita"
   → score_es=2 (hola, necesito), score_en=0
   → routed_to=alex, reason=spanish_language_detected, confidence=0.80
3. Alex inicia conversación:
   "Con gusto le ayudo a agendar su cita. ¿Qué día le queda mejor?"
4. Tikun Olam evalúa la respuesta de Alex:
   → has_empathy=True ("Con gusto"), has_action=True ("agendar")
   → chesed=0.88, gevurah=0.82, tiferet=0.85, netzach=0.87, hod=0.90
   → overall=0.866, clearance=APPROVED
5. Respuesta entregada al paciente
6. Alex agenda en GoHighLevel via API
7. Sesión guardada en Firestore: session_YYYYMMDD_HHMMSS
```

### Flujo 2: Emergencia dental detectada

```
1. Paciente: "Me duele horrible, como 9/10, la cara se me hinchó"
2. Akiva: "9/10" + "hinchó" → emergency_keyword_detected
   → routed_to=diana, priority=HIGH, override=True, confidence=0.95
3. Diana: "Entiendo que está en mucho dolor. Voy a ayudarle ahora mismo.
           ¿Puede decirme exactamente dónde siente el dolor?"
4. Tikun Olam evalúa:
   → has_empathy=True, has_action=True, no vetoes
   → clearance=APPROVED, score=0.893
5. Diana: "Le recomiendo aplicar frío externamente durante 15 minutos
           mientras le agendo una cita de emergencia para hoy."
6. Evaluación: "aplicar frío" → veto medical_advice_given
   → clearance=REJECTED
7. Diana reformula: "Le voy a conectar con Alex para agendar una cita
                    de emergencia para hoy mismo."
8. Evaluación de la reformulación: APPROVED (sin consejo médico)
9. Handoff a Alex para confirmar cita same-day
```

### Flujo 3: Consulta de facturación bilingüe

```
1. "How much does a root canal cost?"
2. Akiva: "how much" + "cost" → billing_intent_detected
   → routed_to=marco, reason=billing_intent_detected, confidence=0.85
3. Marco responde con costos estimados y opciones de plan de pago
4. Tikun Olam evalúa:
   → "Solo hoy tenemos precio especial" → false_urgency VETO
   → clearance=REJECTED
5. Marco reformula sin urgencia artificial → APPROVED
6. Sesión registrada en Firestore
```

---

## 13. Referencia de APIs del Dashboard

### `GET /api/overview`

```json
{
  "calls_today": 278,
  "calls_trend_pct": 12.3,
  "active_agents": 7,
  "total_agents": 7,
  "avg_ethics_score": 0.847,
  "ethics_trend_pct": 2.1,
  "emergencies_today": 18,
  "emergencies_trend_pct": -5.2,
  "approved_rate": 85.1
}
```

### `GET /api/calls/timeline`

```json
{
  "labels": ["00:00", "01:00", "02:00", "..."],
  "data": [2, 0, 1, 3, "..."]
}
```

### `GET /api/ethics/summary`

```json
{
  "avg_scores": {
    "chesed": 0.812, "gevurah": 0.843, "tiferet": 0.784,
    "netzach": 0.798, "hod": 0.867
  },
  "clearance_distribution": {
    "APPROVED": 709, "CONDITIONAL": 98, "REJECTED": 26
  },
  "veto_counts": {
    "attempted_diagnosis": 3, "emergency_not_escalated": 8,
    "emotional_manipulation": 2, "medical_advice_given": 5,
    "false_urgency": 4, "privacy_violation": 1
  },
  "veto_detail": [
    { "id": "emergency_not_escalated", "count": 8, "severity": "CRITICAL",
      "description": "High-severity emergency keywords with no escalation." }
  ],
  "dimension_detail": [
    { "name": "chesed", "label": "Chesed", "score": 0.812, "weight": 0.25,
      "focus": "Patient emotional and physical wellbeing", "provider": "Gemini" }
  ],
  "overall_avg": 0.821,
  "total_evaluated": 833
}
```

### `POST /api/simulate/route`

**Request:**
```json
{ "message": "Tengo dolor 9/10, urgente", "language": "es" }
```

**Response:**
```json
{
  "message_preview": "Tengo dolor 9/10, urgente",
  "routing": {
    "routed_to": "diana",
    "reason": "emergency_keyword_detected",
    "priority": "HIGH",
    "detected_language": "es",
    "override": true,
    "confidence": 0.95,
    "agent_color": "#ef4444",
    "agent_name": "Diana"
  },
  "agent": {
    "id": "diana", "name": "Diana",
    "role": "Emergency Triage Specialist",
    "language": "Bilingual", "voice": "Aoede",
    "capabilities": ["pain_assessment", "visual_triage", "..."],
    "color": "#ef4444"
  },
  "explanation": "Emergency keywords detected. Akiva triggers HIGH-priority override..."
}
```

### `POST /api/simulate/ethics`

**Request:**
```json
{
  "agent_id": "diana",
  "user_message": "Me duele mucho, 8/10",
  "agent_response": "Entiendo su dolor. Le conecto inmediatamente con el equipo de emergencias.",
  "context": null
}
```

**Response:**
```json
{
  "agent": "Diana",
  "timestamp": "2026-04-04T12:00:00+00:00",
  "clearance": "APPROVED",
  "overall_score": 0.881,
  "hard_veto_triggered": false,
  "violations": [],
  "dimensions": {
    "chesed": { "score": 0.88, "weight": 0.25, "weighted_contribution": 0.22,
                "focus": "Patient emotional and physical wellbeing",
                "provider": "Gemini",
                "assessment": "Empathetic language markers detected..." }
  },
  "recommendation": "Response meets VocalisAI ethical standards for patient interaction.",
  "engine": "Tikun Olam Framework — VocalisAI MCP v1.0"
}
```

### `GET /api/health`

```json
{
  "mcp_server": "running",
  "mcp_version": "1.0.0",
  "agents_loaded": 7,
  "ethical_engine": "ready",
  "routing_engine": "ready",
  "backend_url": "https://vocalis-ai-v3-hzz2wlra6a-uc.a.run.app",
  "platform": "healthy",
  "firebase": false,
  "response_time_ms": 55.0,
  "cold_start": false
}
```

---

## 14. Guía de Extensión

### Agregar un nuevo agente

```python
# en src/vocalisai_mcp/registry.py
AGENTS_REGISTRY["nuevo_agente"] = {
    "id": "nuevo_agente",
    "name": "Nuevo Agente",
    "language": "ES-MX",
    "role": "Mi Nuevo Rol",
    "voice": "Puck",
    "capabilities": ["cap_1", "cap_2"],
    "description": "Descripción del agente...",
    "handoffs": ["alex"],
}
```

No se requiere ningún otro cambio. El agente aparecerá automáticamente en:
- `vocalisai_list_agents`
- `vocalisai_get_agent`
- Dashboard → sección Agentes
- Selector del simulador

### Agregar un nuevo hard veto

```python
# en src/vocalisai_mcp/registry.py
HARD_VETO_CATALOG["nuevo_veto"] = {
    "keywords": ["palabra_prohibida", "otro_patron"],
    "severity": "HIGH",  # CRITICAL | HIGH | MEDIUM
    "description": "Descripción del veto.",
}
```

El nuevo veto se evaluará automáticamente en `ethics.py` sin ningún otro cambio.

### Agregar una herramienta MCP

```python
# en src/vocalisai_mcp/server.py

class MiInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parametro: str = Field(..., min_length=1, max_length=100)

@mcp.tool(
    name="vocalisai_mi_herramienta",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
)
async def vocalisai_mi_herramienta(params: MiInputModel) -> str:
    """Descripción de la herramienta para el LLM."""
    resultado = {"dato": params.parametro}
    return json.dumps(resultado, indent=2)
```

### Agregar un endpoint al dashboard

```python
# en src/vocalisai_mcp/dashboard/server.py

@app.get("/api/mi_endpoint")
async def api_mi_endpoint() -> JSONResponse:
    """Nuevo endpoint del dashboard."""
    data = {"ejemplo": "valor"}
    return JSONResponse(data)
```

---

*VocalisAI — Google Gemini Live Agent Challenge 2026*  
*Powered by Vertex AI · Google Cloud · tikunframework*  
*Autor: Jesus Eduardo Rodriguez*
