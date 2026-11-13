from typing import Any


def extract_usage_event(node: str, message: Any) -> dict[str, Any]:
    usage = getattr(message, "usage_metadata", None) or {}
    response_metadata = getattr(message, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}

    input_tokens = _integer_value(
        usage.get("input_tokens"),
        token_usage.get("input_tokens"),
        token_usage.get("prompt_tokens"),
    )
    output_tokens = _integer_value(
        usage.get("output_tokens"),
        token_usage.get("output_tokens"),
        token_usage.get("completion_tokens"),
    )
    total_tokens = _integer_value(
        usage.get("total_tokens"),
        token_usage.get("total_tokens"),
    )
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    return {
        "node": node,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "usage_available": bool(input_tokens or output_tokens or total_tokens),
    }


def summarize_model_usage(
    events: list[dict[str, Any]],
    input_cost_per_1m: float = 0,
    output_cost_per_1m: float = 0,
) -> dict[str, Any]:
    input_tokens = sum(int(event.get("input_tokens", 0) or 0) for event in events)
    output_tokens = sum(int(event.get("output_tokens", 0) or 0) for event in events)
    total_tokens = sum(int(event.get("total_tokens", 0) or 0) for event in events)
    usage_available = any(event.get("usage_available", False) for event in events)
    estimated_cost_usd = None
    if usage_available and (input_cost_per_1m > 0 or output_cost_per_1m > 0):
        estimated_cost_usd = round(
            input_tokens * input_cost_per_1m / 1_000_000
            + output_tokens * output_cost_per_1m / 1_000_000,
            6,
        )
    return {
        "model_calls": len(events),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "usage_available": usage_available,
        "estimated_cost_usd": estimated_cost_usd,
    }


def _integer_value(*values: Any) -> int:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and value >= 0:
            return int(value)
    return 0
