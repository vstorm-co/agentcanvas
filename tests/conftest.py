"""Shared fixtures: a real, captured Logfire trace parsed offline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentcanvas.models import WorkflowReport
from agentcanvas.parser import parse_run

FIXTURE = Path(__file__).parent / "fixtures" / "trace_conversation.json"


@pytest.fixture(scope="session")
def trace() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def report(trace: dict[str, Any]) -> WorkflowReport:
    return parse_run(trace["spans"], trace["trace_id"])
