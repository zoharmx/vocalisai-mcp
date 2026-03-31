"""Tests for the static agent/dimension registry."""

import pytest
from vocalisai_mcp.registry import (
    AGENTS_REGISTRY,
    ETHICAL_DIMENSIONS,
    HARD_VETO_CATALOG,
    HARD_VETO_PATTERNS,
)

EXPECTED_AGENTS = {"alex", "nova", "diana", "sara", "marco", "raul", "akiva"}
EXPECTED_DIMENSIONS = {"chesed", "gevurah", "tiferet", "netzach", "hod"}
EXPECTED_VETO_KEYS = {
    "attempted_diagnosis",
    "emergency_not_escalated",
    "emotional_manipulation",
    "medical_advice_given",
    "false_urgency",
    "privacy_violation",
}


class TestAgentRegistry:
    def test_all_expected_agents_present(self):
        assert set(AGENTS_REGISTRY.keys()) == EXPECTED_AGENTS

    @pytest.mark.parametrize("agent_id", list(EXPECTED_AGENTS))
    def test_agent_has_required_fields(self, agent_id):
        agent = AGENTS_REGISTRY[agent_id]
        assert "id" in agent
        assert "name" in agent
        assert "language" in agent
        assert "role" in agent
        assert "capabilities" in agent
        assert "description" in agent
        assert isinstance(agent["capabilities"], list)
        assert len(agent["capabilities"]) > 0

    @pytest.mark.parametrize("agent_id", list(EXPECTED_AGENTS))
    def test_agent_id_matches_key(self, agent_id):
        assert AGENTS_REGISTRY[agent_id]["id"] == agent_id

    def test_akiva_has_no_voice(self):
        assert AGENTS_REGISTRY["akiva"]["voice"] is None

    def test_all_agents_except_akiva_have_voice(self):
        for agent_id, agent in AGENTS_REGISTRY.items():
            if agent_id != "akiva":
                assert agent["voice"] is not None, f"{agent_id} missing voice"

    def test_bilingual_agents(self):
        bilingual = {"diana", "sara", "marco", "raul"}
        for aid in bilingual:
            assert AGENTS_REGISTRY[aid]["language"] == "Bilingual"


class TestEthicalDimensions:
    def test_all_dimensions_present(self):
        assert set(ETHICAL_DIMENSIONS.keys()) == EXPECTED_DIMENSIONS

    def test_weights_sum_to_one(self):
        total = sum(d["weight"] for d in ETHICAL_DIMENSIONS.values())
        assert abs(total - 1.0) < 1e-9

    @pytest.mark.parametrize("dim", list(EXPECTED_DIMENSIONS))
    def test_dimension_has_required_fields(self, dim):
        d = ETHICAL_DIMENSIONS[dim]
        assert "weight" in d
        assert "focus" in d
        assert "provider" in d
        assert 0 < d["weight"] <= 1


class TestHardVetoCatalog:
    def test_all_veto_patterns_present(self):
        assert set(HARD_VETO_CATALOG.keys()) == EXPECTED_VETO_KEYS

    def test_hard_veto_patterns_list_matches_catalog(self):
        assert set(HARD_VETO_PATTERNS) == EXPECTED_VETO_KEYS

    def test_emergency_veto_has_user_keywords(self):
        veto = HARD_VETO_CATALOG["emergency_not_escalated"]
        assert "user_keywords" in veto
        assert len(veto["user_keywords"]) > 0
