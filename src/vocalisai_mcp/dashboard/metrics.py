"""
Mock metrics and data generation for the VocalisAI Dashboard.

All timestamps are UTC. Data is generated deterministically from the current
date so the dashboard looks consistent within the same day.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

# ─── Constants ────────────────────────────────────────────────────────────────

AGENT_COLORS: dict[str, str] = {
    "alex":  "#3b82f6",   # blue
    "nova":  "#8b5cf6",   # violet
    "diana": "#ef4444",   # red
    "sara":  "#10b981",   # emerald
    "marco": "#f59e0b",   # amber
    "raul":  "#06b6d4",   # cyan
    "akiva": "#6366f1",   # indigo
}

AGENT_NAMES: dict[str, str] = {
    "alex":  "Alex",
    "nova":  "Nova",
    "diana": "Diana",
    "sara":  "Sara",
    "marco": "Marco",
    "raul":  "Raúl",
    "akiva": "Akiva",
}

# Realistic routing weights for a US-Hispanic dental clinic
ROUTING_WEIGHTS: dict[str, float] = {
    "alex":  0.44,
    "nova":  0.14,
    "marco": 0.20,
    "diana": 0.09,
    "sara":  0.08,
    "raul":  0.05,
}

# Real-world sample calls for the recent calls table
SAMPLE_CALLS: list[dict[str, Any]] = [
    {
        "message": "Hola, me duele mucho el diente, como 8/10, necesito ayuda urgente",
        "agent": "diana", "language": "es", "priority": "HIGH",
        "clearance": "APPROVED", "score": 0.881, "duration_s": 187,
    },
    {
        "message": "Hi, I'd like to schedule a teeth cleaning for next week",
        "agent": "nova", "language": "en", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.862, "duration_s": 134,
    },
    {
        "message": "¿Cuánto cuesta una corona dental? ¿Aceptan Delta Dental?",
        "agent": "marco", "language": "es", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.845, "duration_s": 212,
    },
    {
        "message": "Necesito cancelar mi cita de mañana a las 10am por favor",
        "agent": "alex", "language": "es", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.879, "duration_s": 89,
    },
    {
        "message": "I need to check my insurance coverage for orthodontics",
        "agent": "marco", "language": "en", "priority": "NORMAL",
        "clearance": "CONDITIONAL", "score": 0.432, "duration_s": 198,
    },
    {
        "message": "Tengo hinchazón severa en la mandíbula desde anoche",
        "agent": "diana", "language": "es", "priority": "HIGH",
        "clearance": "APPROVED", "score": 0.893, "duration_s": 245,
    },
    {
        "message": "Buenas tardes, quiero agendar una limpieza dental",
        "agent": "alex", "language": "es", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.867, "duration_s": 156,
    },
    {
        "message": "Hello, I haven't visited in over a year, I'd like to come back",
        "agent": "nova", "language": "en", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.854, "duration_s": 178,
    },
    {
        "message": "¿Cuáles son sus horarios? ¿Abren los sábados?",
        "agent": "alex", "language": "es", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.891, "duration_s": 67,
    },
    {
        "message": "Tuve una extracción ayer y sigo sangrando un poco",
        "agent": "diana", "language": "es", "priority": "HIGH",
        "clearance": "APPROVED", "score": 0.904, "duration_s": 312,
    },
    {
        "message": "Can I get a payment plan for my root canal treatment?",
        "agent": "marco", "language": "en", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.858, "duration_s": 267,
    },
    {
        "message": "Me gustaría reagendar mi cita del próximo lunes",
        "agent": "alex", "language": "es", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.876, "duration_s": 112,
    },
    {
        "message": "Do you accept Medicaid for children's dental care?",
        "agent": "nova", "language": "en", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.843, "duration_s": 145,
    },
    {
        "message": "Fractura en diente frontal por accidente, sangrado",
        "agent": "diana", "language": "es", "priority": "HIGH",
        "clearance": "APPROVED", "score": 0.912, "duration_s": 398,
    },
    {
        "message": "¿Pueden enviarme el resumen de mi último tratamiento?",
        "agent": "alex", "language": "es", "priority": "NORMAL",
        "clearance": "APPROVED", "score": 0.868, "duration_s": 98,
    },
]


# ─── Deterministic pseudo-random ─────────────────────────────────────────────

def _prand(seed: int, lo: float = 0.0, hi: float = 1.0) -> float:
    """Deterministic float in [lo, hi] from integer seed."""
    x = abs(math.sin(seed * 9_301 + 49_297)) % 1.0
    return lo + x * (hi - lo)


# ─── Data generators ──────────────────────────────────────────────────────────

def generate_call_timeline_24h() -> dict[str, Any]:
    """Hourly call volume for the past 24 hours."""
    now = datetime.now(timezone.utc)
    labels: list[str] = []
    data: list[int] = []

    for h in range(23, -1, -1):
        ts = (now - timedelta(hours=h)).replace(minute=0, second=0, microsecond=0)
        hod = ts.hour

        if 9 <= hod <= 12:
            base = 23
        elif 14 <= hod <= 17:
            base = 20
        elif 7 <= hod < 9 or 12 < hod < 14:
            base = 13
        elif 17 < hod <= 19:
            base = 9
        elif 6 <= hod < 7:
            base = 5
        else:
            base = 2

        noise = _prand(ts.day * 100 + hod, 0.70, 1.30)
        labels.append(ts.strftime("%H:%M"))
        data.append(max(0, round(base * noise)))

    return {"labels": labels, "data": data}


def generate_7day_trend() -> dict[str, Any]:
    """Daily call totals for the past 7 days."""
    now = datetime.now(timezone.utc)
    labels: list[str] = []
    data: list[int] = []
    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    for d in range(6, -1, -1):
        day = now - timedelta(days=d)
        is_weekend = day.weekday() >= 5
        base = 85 if is_weekend else 210
        noise = _prand(day.day * 31 + day.month, 0.85, 1.15)
        labels.append(f"{day_names[day.weekday()]} {day.strftime('%d/%m')}")
        data.append(round(base * noise))

    return {"labels": labels, "data": data}


def generate_routing_distribution() -> dict[str, Any]:
    """Routing counts per agent this week."""
    total = 833
    agents = list(ROUTING_WEIGHTS.keys())
    raw = [round(total * ROUTING_WEIGHTS[a] * _prand(hash(a) % 999, 0.93, 1.07)) for a in agents]
    factor = total / max(sum(raw), 1)
    counts = [round(c * factor) for c in raw]

    return {
        "agents": agents,
        "names": [AGENT_NAMES[a] for a in agents],
        "counts": counts,
        "total": sum(counts),
        "colors": [AGENT_COLORS[a] for a in agents],
    }


def generate_ethics_summary() -> dict[str, Any]:
    """Aggregated ethics scores and clearance distribution."""
    total = 833
    avg_scores = {
        "chesed":  0.812,
        "gevurah": 0.843,
        "tiferet": 0.784,
        "netzach": 0.798,
        "hod":     0.867,
    }
    clearance = {
        "APPROVED":    round(total * 0.851),
        "CONDITIONAL": round(total * 0.118),
        "REJECTED":    total - round(total * 0.851) - round(total * 0.118),
    }
    veto_counts = {
        "attempted_diagnosis":     3,
        "emergency_not_escalated": 8,
        "emotional_manipulation":  2,
        "medical_advice_given":    5,
        "false_urgency":           4,
        "privacy_violation":       1,
    }
    return {
        "avg_scores": avg_scores,
        "clearance_distribution": clearance,
        "veto_counts": veto_counts,
        "overall_avg": round(sum(avg_scores.values()) / len(avg_scores), 3),
        "total_evaluated": total,
    }


def generate_language_split() -> dict[str, Any]:
    return {
        "labels": ["Español", "English", "Desconocido"],
        "data":   [64.8, 30.2, 5.0],
        "colors": ["#3b82f6", "#8b5cf6", "#64748b"],
    }


def generate_kpi_overview() -> dict[str, Any]:
    """KPI cards data — scales with time of day."""
    now = datetime.now(timezone.utc)
    h = now.hour

    if h < 8:
        calls_today = h * 3
    elif h < 12:
        calls_today = round((24 + (h - 8) * 22) * _prand(now.day, 0.9, 1.1))
    elif h < 18:
        calls_today = round((112 + (h - 12) * 20) * _prand(now.day + 1, 0.9, 1.1))
    else:
        calls_today = round((232 + (h - 18) * 8) * _prand(now.day + 2, 0.9, 1.1))

    return {
        "calls_today":         calls_today,
        "calls_trend_pct":     12.3,
        "active_agents":       7,
        "total_agents":        7,
        "avg_ethics_score":    0.847,
        "ethics_trend_pct":    2.1,
        "emergencies_today":   round(calls_today * 0.063),
        "emergencies_trend_pct": -5.2,
        "approved_rate":       85.1,
    }


def generate_recent_calls(n: int = 15) -> list[dict[str, Any]]:
    """Generate N recent call entries with deterministic timestamps."""
    now = datetime.now(timezone.utc)
    calls: list[dict[str, Any]] = []

    for i in range(n):
        sample = SAMPLE_CALLS[i % len(SAMPLE_CALLS)]
        gap_minutes = i * 8 + _prand(i * 7 + 3, 1, 12)
        ts = now - timedelta(minutes=gap_minutes)
        call_id = f"session_{ts.strftime('%Y%m%d_%H%M%S')}_{i:02d}"
        calls.append({
            "id":               call_id,
            "timestamp":        ts.isoformat(),
            "timestamp_display": ts.strftime("%H:%M:%S"),
            "agent":            sample["agent"],
            "agent_name":       AGENT_NAMES[sample["agent"]],
            "agent_color":      AGENT_COLORS[sample["agent"]],
            "language":         sample["language"],
            "priority":         sample["priority"],
            "clearance":        sample["clearance"],
            "score":            sample["score"],
            "duration_s":       sample["duration_s"],
            "message_preview":  sample["message"][:80] + ("…" if len(sample["message"]) > 80 else ""),
        })

    return calls
