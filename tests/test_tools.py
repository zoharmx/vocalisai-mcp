"""Integration tests for MCP tool functions (no network calls)."""

import json

import pytest

from vocalisai_mcp.server import (
    vocalisai_get_agent,
    vocalisai_list_agents,
    vocalisai_analyze_call,
    vocalisai_route_message,
    vocalisai_platform_info,
    AnalyzeCallInput,
    GetAgentInput,
    ListAgentsInput,
    RouteMessageInput,
)


class TestListAgentsTool:
    @pytest.mark.asyncio
    async def test_returns_all_agents_by_default(self):
        params = ListAgentsInput()
        raw = await vocalisai_list_agents(params)
        data = json.loads(raw)
        assert data["total"] == 7
        assert len(data["agents"]) == 7

    @pytest.mark.asyncio
    async def test_exclude_akiva(self):
        params = ListAgentsInput(include_akiva=False)
        raw = await vocalisai_list_agents(params)
        data = json.loads(raw)
        assert data["total"] == 6
        ids = [a["id"] for a in data["agents"]]
        assert "akiva" not in ids

    @pytest.mark.asyncio
    async def test_role_filter_billing(self):
        params = ListAgentsInput(role_filter="billing")
        raw = await vocalisai_list_agents(params)
        data = json.loads(raw)
        assert data["total"] >= 1
        ids = [a["id"] for a in data["agents"]]
        assert "marco" in ids

    @pytest.mark.asyncio
    async def test_role_filter_no_match_returns_empty(self):
        params = ListAgentsInput(role_filter="nonexistent_role_xyz")
        raw = await vocalisai_list_agents(params)
        data = json.loads(raw)
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_response_has_platform_key(self):
        params = ListAgentsInput()
        raw = await vocalisai_list_agents(params)
        data = json.loads(raw)
        assert "platform" in data
        assert "ethical_engine" in data


class TestGetAgentTool:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("agent_id", ["alex", "nova", "diana", "sara", "marco", "raul", "akiva"])
    async def test_get_known_agent(self, agent_id):
        params = GetAgentInput(agent_id=agent_id)
        raw = await vocalisai_get_agent(params)
        data = json.loads(raw)
        assert "error" not in data
        assert data["id"] == agent_id

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_error(self):
        params = GetAgentInput(agent_id="unknown_agent")
        raw = await vocalisai_get_agent(params)
        data = json.loads(raw)
        assert "error" in data
        assert "available_agents" in data

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(self):
        params = GetAgentInput(agent_id="ALEX")
        raw = await vocalisai_get_agent(params)
        data = json.loads(raw)
        assert data["id"] == "alex"


class TestAnalyzeCallTool:
    @pytest.mark.asyncio
    async def test_approved_empathetic_response(self):
        params = AnalyzeCallInput(
            agent_id="alex",
            user_message="Necesito una cita para limpieza",
            agent_response="Con gusto le ayudo a agendar su cita. ¿Qué día le queda bien?",
        )
        raw = await vocalisai_analyze_call(params)
        data = json.loads(raw)
        assert data["clearance"] == "APPROVED"
        assert data["hard_veto_triggered"] is False
        assert "dimensions" in data
        assert len(data["dimensions"]) == 5

    @pytest.mark.asyncio
    async def test_rejected_diagnosis_response(self):
        params = AnalyzeCallInput(
            agent_id="alex",
            user_message="Me duele una muela",
            agent_response="You have a cavity, you definitely need a root canal.",
        )
        raw = await vocalisai_analyze_call(params)
        data = json.loads(raw)
        assert data["clearance"] == "REJECTED"
        assert data["hard_veto_triggered"] is True

    @pytest.mark.asyncio
    async def test_result_includes_all_required_fields(self):
        params = AnalyzeCallInput(
            agent_id="nova",
            user_message="Hi, I need an appointment",
            agent_response="I'd be happy to help you schedule one. When works for you?",
        )
        raw = await vocalisai_analyze_call(params)
        data = json.loads(raw)
        required = {"agent", "clearance", "overall_score", "hard_veto_triggered",
                    "violations", "dimensions", "recommendation"}
        assert required.issubset(data.keys())

    @pytest.mark.asyncio
    async def test_unknown_agent_still_evaluates(self):
        params = AnalyzeCallInput(
            agent_id="unknown",
            user_message="hello",
            agent_response="I understand and will help you schedule.",
        )
        raw = await vocalisai_analyze_call(params)
        data = json.loads(raw)
        assert "clearance" in data


class TestRouteMessageTool:
    @pytest.mark.asyncio
    async def test_emergency_routes_to_diana(self):
        params = RouteMessageInput(message="Tengo dolor severo 9/10", explain=True)
        raw = await vocalisai_route_message(params)
        data = json.loads(raw)
        assert data["routing_decision"]["routed_to"] == "diana"
        assert data["routing_decision"]["priority"] == "HIGH"
        assert "explanation" in data

    @pytest.mark.asyncio
    async def test_spanish_routes_to_alex(self):
        params = RouteMessageInput(message="Hola, necesito una cita", explain=False)
        raw = await vocalisai_route_message(params)
        data = json.loads(raw)
        assert data["routing_decision"]["routed_to"] == "alex"
        assert "explanation" not in data

    @pytest.mark.asyncio
    async def test_billing_routes_to_marco(self):
        params = RouteMessageInput(message="¿Cuánto cuesta una limpieza?")
        raw = await vocalisai_route_message(params)
        data = json.loads(raw)
        assert data["routing_decision"]["routed_to"] == "marco"

    @pytest.mark.asyncio
    async def test_response_includes_agent_details(self):
        params = RouteMessageInput(message="Hello, I need an appointment")
        raw = await vocalisai_route_message(params)
        data = json.loads(raw)
        assert "agent_details" in data
        assert data["agent_details"]["id"] is not None


class TestPlatformInfoTool:
    @pytest.mark.asyncio
    async def test_platform_info_structure(self):
        raw = await vocalisai_platform_info()
        data = json.loads(raw)
        assert "platform" in data
        assert "agents" in data
        assert "ethical_framework" in data
        assert "integrations" in data
        assert "compliance" in data
        assert "mcp_tools" in data

    @pytest.mark.asyncio
    async def test_mcp_tools_list_complete(self):
        raw = await vocalisai_platform_info()
        data = json.loads(raw)
        tools = data["mcp_tools"]
        assert "vocalisai_analyze_call" in tools
        assert "vocalisai_route_message" in tools
        assert len(tools) == 7
