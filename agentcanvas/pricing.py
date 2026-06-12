"""Compute exact per-request model costs from token counts via ``genai-prices``.

Logfire records token counts but not a dollar amount; this fills that gap using
Pydantic's local price database. If the model is unknown (or the library is
unavailable), the cost is reported as not known rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostBreakdown:
    total_usd: float | None
    input_usd: float | None
    output_usd: float | None
    known: bool


_UNKNOWN = CostBreakdown(None, None, None, False)


def _model_ref(model: str) -> str:
    """``openai/gpt-5.5`` -> ``gpt-5.5`` (genai-prices resolves the bare name)."""
    return model.split("/")[-1] if model else model


def price_request(model: str, input_tokens: int, output_tokens: int) -> CostBreakdown:
    """Return the cost breakdown of a single model request."""
    if not model:
        return _UNKNOWN
    try:
        from genai_prices import calc_price
        from genai_prices.types import Usage

        calc = calc_price(
            Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            model_ref=_model_ref(model),
        )
    except Exception:
        return _UNKNOWN

    total = float(calc.total_price)
    input_price = float(getattr(calc, "input_price", 0) or 0)
    output_price = float(getattr(calc, "output_price", 0) or 0)
    if input_price == 0 and output_price == 0 and total:
        total_tokens = max(input_tokens + output_tokens, 1)
        input_price = total * input_tokens / total_tokens
        output_price = total * output_tokens / total_tokens
    return CostBreakdown(total, input_price, output_price, True)
