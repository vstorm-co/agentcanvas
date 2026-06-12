"""Tests for token-based cost calculation."""

from __future__ import annotations

from agentcanvas.pricing import _model_ref, price_request


def test_model_ref_strips_provider_prefix() -> None:
    assert _model_ref("openai/gpt-5.5") == "gpt-5.5"
    assert _model_ref("gpt-4o") == "gpt-4o"
    assert _model_ref("") == ""


def test_empty_model_is_unknown() -> None:
    cost = price_request("", 100, 50)
    assert cost.known is False
    assert cost.total_usd is None


def test_unknown_model_is_unknown() -> None:
    cost = price_request("definitely-not-a-real-model-xyz", 100, 50)
    assert cost.known is False


def test_known_model_prices_input_and_output() -> None:
    cost = price_request("gpt-4o", 1000, 500)
    assert cost.known is True
    assert cost.total_usd is not None and cost.total_usd > 0
    assert cost.input_usd is not None and cost.output_usd is not None
    # output tokens are pricier than input for this model
    assert cost.output_usd > 0 and cost.input_usd > 0
