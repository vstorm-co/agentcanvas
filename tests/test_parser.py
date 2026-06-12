"""Tests for the span-tree parser against a real captured trace."""

from __future__ import annotations

from typing import Any

from agentcanvas.models import AgentRun, WorkflowReport
from agentcanvas.parser import parse_run


def test_top_level_shape(report: WorkflowReport) -> None:
    assert report.meta.trace_id
    assert report.meta.model == "openai/gpt-5.5"
    assert report.totals.num_turns == 2
    assert len(report.turns) == 2


def test_totals_are_aggregated(report: WorkflowReport) -> None:
    t = report.totals
    assert t.num_model_calls == 6
    assert t.num_tools == 7
    assert t.num_nested_agents == 1
    assert t.total_tokens > 0
    assert t.reasoning_tokens > 0
    assert report.meta.cost_known is True
    assert t.total_cost_usd is not None and t.total_cost_usd > 0


def test_first_turn_has_prompt_and_tools(report: WorkflowReport) -> None:
    turn = report.turns[0]
    assert turn.agent_name == "assistant"
    assert turn.user_prompt and "Introduce me" in turn.user_prompt
    tool_names = [t.name for r in turn.rounds for t in r.tools]
    assert {"get_user_profile", "calculate_birth_year", "roll_dice"} <= set(tool_names)


def test_nested_agent_is_recursive(report: WorkflowReport) -> None:
    nested = [
        tool.nested
        for turn in report.turns
        for call in turn.rounds
        for tool in call.tools
        if tool.nested is not None
    ]
    assert len(nested) == 1
    sub = nested[0]
    assert isinstance(sub, AgentRun)
    assert sub.agent_name == "trip_planner"
    assert sub.rounds, "nested agent should have its own model calls"
    sub_tools = [t.name for r in sub.rounds for t in r.tools]
    assert "get_weather" in sub_tools


def test_reasoning_is_captured(report: WorkflowReport) -> None:
    thinking = [t for turn in report.turns for r in turn.rounds for t in r.thinking]
    assert any(thinking), "at least one model call should expose reasoning text"


def test_conversation_alternates_user_and_assistant(report: WorkflowReport) -> None:
    roles = [m.role for m in report.conversation]
    assert roles.count("user") >= 2
    assert roles.count("assistant") >= 2
    assert roles[0] == "user"


def test_empty_trace_is_handled() -> None:
    report = parse_run([], "abc123")
    assert report.totals.num_turns == 0
    assert report.turns == []
    assert report.meta.cost_known is False


def test_synthetic_round_when_tool_has_no_preceding_chat() -> None:
    spans: list[dict[str, Any]] = [
        {
            "span_id": "a",
            "parent_span_id": None,
            "span_name": "invoke_agent solo",
            "start_timestamp": "1",
            "duration": 1.0,
            "attributes": {"gen_ai.agent.name": "solo"},
        },
        {
            "span_id": "t",
            "parent_span_id": "a",
            "span_name": "execute_tool ping",
            "start_timestamp": "2",
            "duration": 0.1,
            "attributes": {"gen_ai.tool.name": "ping", "gen_ai.tool.call.result": "pong"},
        },
    ]
    report = parse_run(spans, "deadbeef")
    assert report.totals.num_tools == 1
    assert report.turns[0].rounds[0].tools[0].result == "pong"
