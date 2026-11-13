from types import SimpleNamespace

from app.services.model_usage import extract_usage_event, summarize_model_usage


def test_extract_usage_event_reads_langchain_usage_metadata() -> None:
    message = SimpleNamespace(
        usage_metadata={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
        response_metadata={},
    )

    assert extract_usage_event("planner", message) == {
        "node": "planner",
        "input_tokens": 120,
        "output_tokens": 30,
        "total_tokens": 150,
        "usage_available": True,
    }


def test_extract_usage_event_supports_openai_token_usage_shape() -> None:
    message = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "token_usage": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100}
        },
    )

    result = extract_usage_event("reporter", message)

    assert result["input_tokens"] == 80
    assert result["output_tokens"] == 20
    assert result["total_tokens"] == 100
    assert result["usage_available"] is True


def test_summarize_model_usage_calculates_optional_cost() -> None:
    events = [
        {
            "node": "planner",
            "input_tokens": 1_000,
            "output_tokens": 200,
            "total_tokens": 1_200,
            "usage_available": True,
        },
        {
            "node": "reporter",
            "input_tokens": 500,
            "output_tokens": 300,
            "total_tokens": 800,
            "usage_available": True,
        },
    ]

    result = summarize_model_usage(events, input_cost_per_1m=2.0, output_cost_per_1m=8.0)

    assert result["model_calls"] == 2
    assert result["total_tokens"] == 2_000
    assert result["estimated_cost_usd"] == 0.007


def test_summarize_model_usage_does_not_invent_unknown_cost() -> None:
    result = summarize_model_usage(
        [
            {
                "node": "planner",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "usage_available": False,
            }
        ]
    )

    assert result["model_calls"] == 1
    assert result["usage_available"] is False
    assert result["estimated_cost_usd"] is None
