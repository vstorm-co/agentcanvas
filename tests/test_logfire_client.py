"""Tests for the Logfire client helpers (no network required)."""

from __future__ import annotations

import pytest

from agentcanvas.logfire_client import (
    DEFAULT_BASE_URL,
    LogfireClient,
    _columns_to_rows,
    _ensure_dict,
    _sql_str,
)


def test_columns_to_rows_transposes() -> None:
    payload = {
        "columns": [
            {"name": "a", "values": [1, 2]},
            {"name": "b", "values": ["x", "y"]},
        ]
    }
    assert _columns_to_rows(payload) == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


def test_columns_to_rows_empty() -> None:
    assert _columns_to_rows({"columns": []}) == []
    assert _columns_to_rows({}) == []


def test_ensure_dict_variants() -> None:
    assert _ensure_dict(None) == {}
    assert _ensure_dict({"k": 1}) == {"k": 1}
    assert _ensure_dict('{"k": 1}') == {"k": 1}
    assert _ensure_dict("not json") == {}
    assert _ensure_dict(42) == {}


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_READ_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        LogfireClient()


def test_sql_str_escapes_quotes() -> None:
    assert _sql_str("019eb6") == "'019eb6'"
    # an injection attempt is escaped into an inert string literal
    assert _sql_str("'; DROP TABLE records;--") == "'''; DROP TABLE records;--'"


def test_empty_trace_id_rejected() -> None:
    with pytest.raises(ValueError):
        LogfireClient(read_token="dummy").fetch_trace("")


def test_base_url_is_trimmed() -> None:
    client = LogfireClient(read_token="dummy", base_url="https://example.com/")
    assert client.base_url == "https://example.com"


def test_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGFIRE_BASE_URL", "https://logfire-eu.pydantic.dev/")
    assert LogfireClient(read_token="dummy").base_url == "https://logfire-eu.pydantic.dev"


def test_explicit_base_url_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGFIRE_BASE_URL", "https://logfire-eu.pydantic.dev")
    client = LogfireClient(read_token="dummy", base_url="https://custom.example")
    assert client.base_url == "https://custom.example"


def test_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_BASE_URL", raising=False)
    assert LogfireClient(read_token="dummy").base_url == DEFAULT_BASE_URL
