"""agentcanvas — visualize a Pydantic AI agent workflow from Logfire logs.

Reads the OpenTelemetry (GenAI) spans emitted by Pydantic AI's instrumentation,
parses them into a typed :class:`WorkflowReport` (turns, rounds, tools, nested
agents), prices each model call with ``genai-prices``, and renders a
self-contained, interactive HTML report.
"""

from .logfire_client import LogfireClient
from .models import AgentRun, ModelCall, ToolCall, WorkflowReport
from .parser import parse_run
from .render import render_html

__all__ = [
    "LogfireClient",
    "WorkflowReport",
    "AgentRun",
    "ModelCall",
    "ToolCall",
    "parse_run",
    "render_html",
]
