"""Tests for HTML rendering."""

from __future__ import annotations

import json
import re

from agentcanvas.models import WorkflowReport
from agentcanvas.render import render_html


def _run_line(html: str) -> str:
    match = re.search(r"const RUN = (.+);", html)  # payload is a single line
    assert match, "embedded RUN payload not found"
    return match.group(1)


def _embedded_payload(html: str) -> dict:
    return json.loads(_run_line(html))


def test_render_is_self_contained_html(report: WorkflowReport) -> None:
    html = render_html(report)
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert "<script src=" not in html  # no external JS
    assert report.meta.trace_id in html


def test_embedded_payload_matches_report(report: WorkflowReport) -> None:
    payload = _embedded_payload(render_html(report))
    assert payload["meta"]["trace_id"] == report.meta.trace_id
    assert payload["totals"]["num_tools"] == report.totals.num_tools
    assert len(payload["turns"]) == len(report.turns)


def test_closing_script_tags_are_escaped(report: WorkflowReport) -> None:
    # "</" inside the JSON must be escaped so it cannot close the <script> early.
    assert "</" not in _run_line(render_html(report))
