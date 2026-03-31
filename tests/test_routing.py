"""Tests for the Akiva routing engine."""

import pytest
from vocalisai_mcp.routing import AkivaRouter


@pytest.fixture
def router():
    return AkivaRouter()


class TestEmergencyOverride:
    @pytest.mark.parametrize("message", [
        "Tengo dolor severo, es 9/10",
        "I have severe pain",
        "Tengo sangrado en la boca",
        "There is bleeding and swelling",
        "No puedo respirar bien",
        "Tengo 10/10 de dolor",
        "Emergency — my mouth won't stop bleeding",
    ])
    def test_emergency_routes_to_diana(self, router, message):
        decision = router.route(message)
        assert decision.routed_to == "diana"
        assert decision.priority == "HIGH"
        assert decision.override is True
        assert decision.reason == "emergency_keyword_detected"

    def test_emergency_overrides_language(self, router):
        """Emergency override must ignore language hints."""
        decision = router.route("I need emergency help, severe pain", language_hint="en")
        assert decision.routed_to == "diana"
        assert decision.override is True


class TestBillingRouting:
    @pytest.mark.parametrize("message", [
        "¿Cuánto cuesta una limpieza?",
        "Necesito información sobre pago",
        "What is the cost of a crown?",
        "Do you have payment plans available?",
        "Tengo una duda sobre mi factura",
    ])
    def test_billing_routes_to_marco(self, router, message):
        decision = router.route(message)
        assert decision.routed_to == "marco"
        assert decision.priority == "NORMAL"
        assert decision.override is False

    def test_billing_does_not_override_emergency(self, router):
        """Emergency always wins over billing keywords."""
        decision = router.route("Dolor severo 9/10 y quiero saber el costo")
        assert decision.routed_to == "diana"
        assert decision.priority == "HIGH"


class TestLanguageRouting:
    @pytest.mark.parametrize("message,expected_agent", [
        ("Hola, necesito una cita por favor", "alex"),
        ("Buenos días, tengo una consulta", "alex"),
        ("Hello, I'd like to schedule a dentist appointment", "nova"),
        ("Hi, I need to book an appointment please", "nova"),
    ])
    def test_language_routing(self, router, message, expected_agent):
        decision = router.route(message)
        assert decision.routed_to == expected_agent
        assert decision.priority == "NORMAL"
        assert decision.override is False

    def test_spanish_hint_routes_to_alex(self, router):
        decision = router.route("I need appointment", language_hint="es")
        assert decision.routed_to == "alex"

    def test_english_hint_routes_to_nova(self, router):
        decision = router.route("Necesito cita", language_hint="en")
        assert decision.routed_to == "nova"


class TestDefaultRouting:
    def test_unknown_language_defaults_to_alex(self, router):
        decision = router.route("xyzzy foo bar")
        assert decision.routed_to == "alex"
        assert decision.detected_language == "unknown"
        assert decision.confidence <= 0.5


class TestExplanations:
    def test_explanation_returns_string(self, router):
        decision = router.route("Hola necesito cita")
        explanation = router.explanation(decision)
        assert isinstance(explanation, str)
        assert len(explanation) > 10

    def test_emergency_explanation_mentions_diana(self, router):
        decision = router.route("Tengo dolor 9/10")
        explanation = router.explanation(decision)
        assert "Diana" in explanation or "diana" in explanation.lower()

    def test_billing_explanation_mentions_marco(self, router):
        decision = router.route("¿Cuánto cuesta una extracción?")
        explanation = router.explanation(decision)
        assert "Marco" in explanation or "marco" in explanation.lower()


class TestRoutingDecisionToDict:
    def test_to_dict_has_all_keys(self, router):
        decision = router.route("Hola, necesito una cita")
        d = decision.to_dict()
        assert {"routed_to", "reason", "priority", "detected_language",
                "override", "confidence"}.issubset(d.keys())

    def test_confidence_in_range(self, router):
        decision = router.route("Hello, I need an appointment")
        assert 0.0 <= decision.confidence <= 1.0
