"""Parse raw Logfire spans into a typed :class:`WorkflowReport`.

Logfire spans form a tree via ``parent_span_id``. We turn that tree into a
recursive structure that naturally supports multiple conversation turns,
arbitrarily deep nested agents-as-tools, per-call reasoning, token usage and
exact cost. Relies on Pydantic AI v2's OpenTelemetry GenAI span names:
``invoke_agent <name>``, ``chat <model>``, ``execute_tool <name>``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .models import (
    AgentRun,
    ConversationMessage,
    Meta,
    ModelCall,
    ToolCall,
    ToolDefinition,
    Totals,
    WorkflowReport,
)
from .pricing import price_request

Span = dict[str, Any]
ChildIndex = dict[str | None, list[Span]]


def _maybe_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _stringify(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


@dataclass
class _Part:
    kind: str
    role: str | None = None
    content: str | None = None
    name: str | None = None


def _parts(raw: Any) -> list[_Part]:
    """Flatten a GenAI message list into ordered parts (text/thinking/tool_call)."""
    messages = _maybe_json(raw)
    out: list[_Part] = []
    if not isinstance(messages, list):
        return out
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        for part in message.get("parts", []):
            if not isinstance(part, dict):
                continue
            ptype = part.get("type", "")
            if ptype == "tool_call":
                out.append(_Part("tool_call", role, name=part.get("name")))
            elif ptype in ("text", "thinking") and part.get("content"):
                out.append(_Part(ptype, role, content=part.get("content")))
    return out


def _user_prompt(chat_attrs: dict[str, Any]) -> str | None:
    """The last user-authored text in a request's input — the turn's prompt."""
    for part in reversed(_parts(chat_attrs.get("gen_ai.input.messages"))):
        if part.kind == "text" and part.role == "user" and part.content:
            return part.content
    return None


def _conversation(all_messages: Any) -> list[ConversationMessage]:
    """Flatten the full message history into a human-readable transcript."""
    messages = _maybe_json(all_messages)
    out: list[ConversationMessage] = []
    if not isinstance(messages, list):
        return out
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        texts: list[str] = []
        thinking: list[str] = []
        tool_calls: list[str] = []
        tool_results: list[str] = []
        for part in message.get("parts", []):
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            content = part.get("content")
            if ptype == "text" and content:
                texts.append(content)
            elif ptype == "thinking" and content:
                thinking.append(content)
            elif ptype == "tool_call" and part.get("name"):
                tool_calls.append(part["name"])
            elif ptype == "tool_call_response" and part.get("name"):
                tool_results.append(part["name"])
        if role == "user" and texts:
            out.append(ConversationMessage(role="user", text="\n".join(texts)))
        elif role == "user" and tool_results:
            out.append(
                ConversationMessage(
                    role="tool", text="Returned results from: " + ", ".join(tool_results)
                )
            )
        elif role == "assistant":
            out.append(
                ConversationMessage(
                    role="assistant",
                    text="\n".join(texts),
                    thinking=thinking,
                    tool_calls=tool_calls,
                )
            )
    return out


def _child_index(spans: list[Span]) -> ChildIndex:
    children: ChildIndex = {}
    for span in spans:
        children.setdefault(span.get("parent_span_id"), []).append(span)
    for siblings in children.values():
        siblings.sort(key=lambda s: s.get("start_timestamp") or "")
    return children


def _kind(span: Span) -> str:
    name = span["span_name"]
    if name.startswith("invoke_agent"):
        return "agent"
    if name.startswith("chat "):
        return "model"
    if name.startswith("execute_tool "):
        return "tool"
    return "other"


def _parse_model_call(span: Span) -> ModelCall:
    attrs = span["attributes"]
    model = attrs.get("gen_ai.request.model") or attrs.get("gen_ai.response.model") or ""
    input_tokens = int(attrs.get("gen_ai.usage.input_tokens", 0) or 0)
    output_tokens = int(attrs.get("gen_ai.usage.output_tokens", 0) or 0)
    cost = price_request(model, input_tokens, output_tokens)

    parts = _parts(attrs.get("gen_ai.output.messages"))
    finish = attrs.get("gen_ai.response.finish_reasons") or []
    if isinstance(finish, str):
        finish = [finish]

    request_params = _maybe_json(attrs.get("model_request_parameters"))
    available = []
    thinking_config = None
    if isinstance(request_params, dict):
        thinking_config = request_params.get("thinking")
        for tool in request_params.get("function_tools") or []:
            if isinstance(tool, dict):
                available.append(
                    ToolDefinition(name=tool.get("name"), description=tool.get("description"))
                )

    return ModelCall(
        model=model,
        provider=attrs.get("gen_ai.provider.name") or attrs.get("gen_ai.system"),
        server=attrs.get("server.address"),
        response_id=attrs.get("gen_ai.response.id"),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=int(attrs.get("gen_ai.usage.details.reasoning_tokens", 0) or 0),
        cost_usd=cost.total_usd,
        cost_input_usd=cost.input_usd,
        cost_output_usd=cost.output_usd,
        finish_reasons=list(finish),
        duration_s=float(span.get("duration") or 0.0),
        thinking=[p.content for p in parts if p.kind == "thinking" and p.content],
        text_out=[p.content for p in parts if p.kind == "text" and p.content],
        decided_tool_calls=[p.name for p in parts if p.kind == "tool_call" and p.name],
        available_tools=available,
        thinking_config=thinking_config,
    )


def _parse_tool(span: Span, index: ChildIndex) -> ToolCall:
    attrs = span["attributes"]
    nested: AgentRun | None = None
    for child in index.get(span["span_id"], []):
        if _kind(child) == "agent":
            nested = _parse_agent(child, index)
            break
    return ToolCall(
        name=attrs.get("gen_ai.tool.name", span["span_name"].replace("execute_tool ", "")),
        arguments=_maybe_json(attrs.get("gen_ai.tool.call.arguments")),
        result=_stringify(attrs.get("gen_ai.tool.call.result")),
        duration_s=float(span.get("duration") or 0.0),
        nested=nested,
    )


def _parse_agent(span: Span, index: ChildIndex) -> AgentRun:
    attrs = span["attributes"]
    rounds: list[ModelCall] = []
    current: ModelCall | None = None
    user_prompt: str | None = None

    for child in index.get(span["span_id"], []):
        kind = _kind(child)
        if kind == "model":
            current = _parse_model_call(child)
            rounds.append(current)
            if user_prompt is None:
                user_prompt = _user_prompt(child["attributes"])
        elif kind == "tool":
            if current is None:
                current = ModelCall()
                rounds.append(current)
            current.tools.append(_parse_tool(child, index))

    return AgentRun(
        agent_name=attrs.get("gen_ai.agent.name", span["span_name"].replace("invoke_agent ", "")),
        model=attrs.get("model_name", ""),
        final_output=_stringify(_maybe_json(attrs.get("final_result"))),
        user_prompt=user_prompt,
        rounds=rounds,
    )


@dataclass
class _Acc:
    input: int = 0
    output: int = 0
    reasoning: int = 0
    cost: float = 0.0
    cost_known: bool = False
    model_calls: int = 0
    tools: int = 0
    nested_agents: int = 0


def _accumulate(agent: AgentRun, acc: _Acc) -> None:
    for call in agent.rounds:
        acc.input += call.input_tokens
        acc.output += call.output_tokens
        acc.reasoning += call.reasoning_tokens
        if call.model:
            acc.model_calls += 1
        if call.cost_usd is not None:
            acc.cost += call.cost_usd
            acc.cost_known = True
        for tool in call.tools:
            acc.tools += 1
            if tool.nested is not None:
                acc.nested_agents += 1
                _accumulate(tool.nested, acc)


def parse_run(spans: list[Span], trace_id: str) -> WorkflowReport:
    """Build a :class:`WorkflowReport` from the spans of a single trace."""
    index = _child_index(spans)
    tool_ids = {s["span_id"] for s in spans if _kind(s) == "tool"}
    top_agents = sorted(
        (s for s in spans if _kind(s) == "agent" and s.get("parent_span_id") not in tool_ids),
        key=lambda s: s.get("start_timestamp") or "",
    )

    turns = [_parse_agent(span, index) for span in top_agents]

    acc = _Acc()
    for turn in turns:
        _accumulate(turn, acc)

    roots = index.get(None, [])
    duration = max((float(s.get("duration") or 0.0) for s in roots), default=0.0)
    conversation = (
        _conversation(top_agents[-1]["attributes"].get("pydantic_ai.all_messages"))
        if top_agents
        else []
    )
    model = next((t.model for t in turns if t.model), "")

    return WorkflowReport(
        meta=Meta(
            trace_id=trace_id,
            model=model,
            duration_s=duration,
            num_turns=len(turns),
            cost_known=acc.cost_known,
        ),
        totals=Totals(
            total_tokens=acc.input + acc.output,
            total_cost_usd=acc.cost if acc.cost_known else None,
            reasoning_tokens=acc.reasoning,
            num_model_calls=acc.model_calls,
            num_tools=acc.tools,
            num_nested_agents=acc.nested_agents,
            num_turns=len(turns),
        ),
        conversation=conversation,
        turns=turns,
    )
