"""
Akiva Routing Engine — local simulation of the meta-agent supervisor.

Replicates the routing logic running in the VocalisAI production orchestrator:
priority override for emergencies → billing detection → language detection → default.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .registry import AGENTS_REGISTRY

logger = logging.getLogger(__name__)

# ─── Keyword Sets ─────────────────────────────────────────────────────────────

_EMERGENCY_KEYWORDS = frozenset([
    # Spanish
    "dolor", "urgente", "sangrado", "inflamación", "inflamacion",
    "no puedo respirar", "accidente", "golpe", "caída", "caida",
    "fractura", "severo", "severa",
    # English
    "pain", "emergency", "bleeding", "swelling", "severe",
    "can't breathe", "accident", "trauma", "fracture",
    # Pain scale
    "7/10", "8/10", "9/10", "10/10",
])

_SPANISH_INDICATORS = frozenset([
    "hola", "buenos", "buenas", "necesito", "quiero", "tengo",
    "cita", "dolor", "me", "mi", "por favor", "gracias",
    "cuánto", "cuanto", "dentista", "consulta",
])

_ENGLISH_INDICATORS = frozenset([
    "hello", "hi", "need", "want", "have", "appointment",
    "insurance", "please", "how much", "dentist", "dental",
    "can i", "i'd like", "i would",
])

_BILLING_KEYWORDS = frozenset([
    # Spanish
    "pago", "costo", "precio", "factura", "seguro", "cobertura",
    "cuánto cuesta", "plan de pago", "adeudo",
    # English
    "payment", "cost", "price", "invoice", "insurance", "coverage",
    "how much", "payment plan", "balance", "bill",
])


# ─── Result ───────────────────────────────────────────────────────────────────


@dataclass
class RoutingDecision:
    routed_to: str
    reason: str
    priority: str           # HIGH | NORMAL
    detected_language: str  # es | en | unknown
    override: bool          # True when emergency overrides language routing
    confidence: float       # 0.0 – 1.0

    def to_dict(self) -> dict[str, object]:
        return {
            "routed_to": self.routed_to,
            "reason": self.reason,
            "priority": self.priority,
            "detected_language": self.detected_language,
            "override": self.override,
            "confidence": self.confidence,
        }


# ─── Router ───────────────────────────────────────────────────────────────────


class AkivaRouter:
    """
    Local simulation of Akiva's routing logic.

    Priority chain:
        1. Emergency override  → Diana (HIGH priority, ignores language)
        2. Billing intent      → Marco (NORMAL priority)
        3. Language detection  → Alex (ES) | Nova (EN)
        4. Default             → Alex (ES)
    """

    def route(self, message: str, language_hint: str | None = None) -> RoutingDecision:
        """Determine which agent should handle this incoming patient message."""
        msg_lower = message.lower()

        detected_lang = self._detect_language(msg_lower, language_hint)

        # ── 1. Emergency override ─────────────────────────────────────────────
        emergency_matches = [kw for kw in _EMERGENCY_KEYWORDS if kw in msg_lower]
        if emergency_matches:
            logger.info(
                "Emergency override triggered | keywords=%s | agent=diana",
                emergency_matches[:3],
            )
            return RoutingDecision(
                routed_to="diana",
                reason="emergency_keyword_detected",
                priority="HIGH",
                detected_language=detected_lang,
                override=True,
                confidence=0.95,
            )

        # ── 2. Billing intent ──────────────────────────────────────────────────
        billing_matches = [kw for kw in _BILLING_KEYWORDS if kw in msg_lower]
        if billing_matches:
            logger.info("Billing intent detected | keywords=%s | agent=marco", billing_matches[:3])
            return RoutingDecision(
                routed_to="marco",
                reason="billing_intent_detected",
                priority="NORMAL",
                detected_language=detected_lang,
                override=False,
                confidence=0.85,
            )

        # ── 3. Language routing ────────────────────────────────────────────────
        if detected_lang == "es":
            return RoutingDecision(
                routed_to="alex",
                reason="spanish_language_detected",
                priority="NORMAL",
                detected_language="es",
                override=False,
                confidence=0.80,
            )

        if detected_lang == "en":
            return RoutingDecision(
                routed_to="nova",
                reason="english_language_detected",
                priority="NORMAL",
                detected_language="en",
                override=False,
                confidence=0.80,
            )

        # ── 4. Default (unknown language → Spanish receptionist) ──────────────
        logger.info("Language undetermined — defaulting to alex")
        return RoutingDecision(
            routed_to="alex",
            reason="default_routing",
            priority="NORMAL",
            detected_language="unknown",
            override=False,
            confidence=0.50,
        )

    @staticmethod
    def _detect_language(msg_lower: str, hint: str | None) -> str:
        """Score Spanish vs English indicators to detect message language."""
        if hint in ("es", "en"):
            return hint

        es_score = sum(1 for kw in _SPANISH_INDICATORS if kw in msg_lower)
        en_score = sum(1 for kw in _ENGLISH_INDICATORS if kw in msg_lower)

        if es_score == 0 and en_score == 0:
            return "unknown"
        return "es" if es_score >= en_score else "en"

    @staticmethod
    def explanation(decision: RoutingDecision) -> str:
        """Return a human-readable routing explanation for MCP clients."""
        agent = AGENTS_REGISTRY.get(decision.routed_to, {})
        agent_name = agent.get("name", decision.routed_to)
        agent_role = agent.get("role", "")

        explanations: dict[str, str] = {
            "emergency_keyword_detected": (
                f"Emergency keywords detected in patient message. "
                f"Akiva triggers HIGH-priority override and routes directly to {agent_name} "
                f"({agent_role}) regardless of language. Emergency protocol active."
            ),
            "billing_intent_detected": (
                f"Billing or payment-related intent detected. "
                f"Routed to {agent_name} ({agent_role}) for cost explanation or payment plan setup."
            ),
            "spanish_language_detected": (
                f"Spanish language indicators detected (confidence={decision.confidence:.0%}). "
                f"Routed to {agent_name} ({agent_role})."
            ),
            "english_language_detected": (
                f"English language indicators detected (confidence={decision.confidence:.0%}). "
                f"Routed to {agent_name} ({agent_role})."
            ),
            "default_routing": (
                f"Language could not be determined. "
                f"Defaulting to {agent_name} ({agent_role}) as primary receptionist."
            ),
        }
        return explanations.get(decision.reason, "Standard context-based routing.")
