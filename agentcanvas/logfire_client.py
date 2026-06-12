"""A thin client for the Logfire Query API (read spans via SQL + read token)."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

# Default region; override with LOGFIRE_BASE_URL (e.g. https://logfire-eu.pydantic.dev).
DEFAULT_BASE_URL = "https://logfire-us.pydantic.dev"

# Columns the parser needs. `attributes` carries the whole GenAI payload.
_SPAN_COLUMNS = (
    "span_id, parent_span_id, span_name, "
    "start_timestamp, end_timestamp, duration, "
    "otel_status_code, otel_status_message, attributes"
)


def _sql_str(value: str) -> str:
    """Quote a value as a SQL string literal, escaping embedded quotes (ANSI style)."""
    return "'" + value.replace("'", "''") + "'"


class LogfireClient:
    """Runs SQL queries against Logfire and returns rows as a list of dicts."""

    def __init__(self, read_token: str | None = None, base_url: str | None = None):
        self.read_token = read_token or os.environ.get("LOGFIRE_READ_TOKEN")
        if not self.read_token:
            raise RuntimeError(
                "Missing Logfire read token. Set LOGFIRE_READ_TOKEN in .env or pass read_token=..."
            )
        resolved = base_url or os.environ.get("LOGFIRE_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = resolved.rstrip("/")

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Run SQL and return rows (Logfire returns columns — we transpose here)."""
        resp = httpx.get(
            f"{self.base_url}/v1/query",
            params={"sql": sql},
            headers={
                "Authorization": f"Bearer {self.read_token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        return _columns_to_rows(payload)

    def latest_trace_id(self) -> str | None:
        """Latest trace that is an actual agent run (has an `invoke_agent` span)."""
        rows = self.query(
            "SELECT trace_id FROM records WHERE span_name LIKE 'invoke_agent%' "
            "ORDER BY start_timestamp DESC LIMIT 1"
        )
        return rows[0]["trace_id"] if rows else None

    def list_recent_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent agent runs (by the invoke_agent span)."""
        return self.query(
            "SELECT trace_id, span_name, start_timestamp, duration "
            "FROM records WHERE span_name LIKE 'invoke_agent%' "
            f"ORDER BY start_timestamp DESC LIMIT {int(limit)}"
        )

    def fetch_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """All spans of a given trace, sorted chronologically."""
        if not trace_id:
            raise ValueError("trace_id must not be empty")
        rows = self.query(
            f"SELECT {_SPAN_COLUMNS} FROM records "
            f"WHERE trace_id = {_sql_str(trace_id)} ORDER BY start_timestamp ASC"
        )
        for row in rows:
            row["attributes"] = _ensure_dict(row.get("attributes"))
        return rows


def _columns_to_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cols = payload.get("columns", [])
    if not cols:
        return []
    names = [c["name"] for c in cols]
    values = [c["values"] for c in cols]
    n = len(values[0]) if values else 0
    return [{names[c]: values[c][i] for c in range(len(names))} for i in range(n)]


def _ensure_dict(value: Any) -> dict[str, Any]:
    """The `attributes` column may come back as a JSON string or a native object."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}
