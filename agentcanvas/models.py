"""Typed models for a parsed agent workflow.

These mirror exactly the data the HTML renderer consumes. ``WorkflowReport`` is
serialised to JSON and embedded in the report; nothing outside these fields is
emitted, so the payload stays lean and the renderer stays in sync.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """A tool the model was offered for a request (name + description)."""

    name: str | None = None
    description: str | None = None


class ToolCall(BaseModel):
    """A single tool execution. ``nested`` is set when the tool is itself an agent."""

    name: str
    arguments: Any = None
    result: str | None = None
    duration_s: float = 0.0
    nested: AgentRun | None = None


class ModelCall(BaseModel):
    """One request to the model (a ``chat`` span) plus the tools it triggered."""

    model: str = ""
    provider: str | None = None
    server: str | None = None
    response_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float | None = None
    cost_input_usd: float | None = None
    cost_output_usd: float | None = None
    finish_reasons: list[str] = Field(default_factory=list)
    duration_s: float = 0.0
    thinking: list[str] = Field(default_factory=list)
    text_out: list[str] = Field(default_factory=list)
    decided_tool_calls: list[str] = Field(default_factory=list)
    available_tools: list[ToolDefinition] = Field(default_factory=list)
    thinking_config: Any = None
    tools: list[ToolCall] = Field(default_factory=list)


class AgentRun(BaseModel):
    """One agent invocation: a conversation turn, or a nested sub-agent."""

    agent_name: str = "agent"
    model: str = ""
    final_output: str | None = None
    user_prompt: str | None = None
    rounds: list[ModelCall] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    """One entry in the human-readable transcript."""

    role: str
    text: str = ""
    thinking: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)


class Meta(BaseModel):
    trace_id: str
    model: str = ""
    duration_s: float = 0.0
    num_turns: int = 0
    cost_known: bool = False


class Totals(BaseModel):
    total_tokens: int = 0
    total_cost_usd: float | None = None
    reasoning_tokens: int = 0
    num_model_calls: int = 0
    num_tools: int = 0
    num_nested_agents: int = 0
    num_turns: int = 0


class WorkflowReport(BaseModel):
    """The complete, renderable workflow."""

    meta: Meta
    totals: Totals
    conversation: list[ConversationMessage] = Field(default_factory=list)
    turns: list[AgentRun] = Field(default_factory=list)


# Resolve the ToolCall <-> AgentRun forward reference.
ToolCall.model_rebuild()
