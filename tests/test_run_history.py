from types import SimpleNamespace

from app.services.run_history import build_follow_up_context


def test_build_follow_up_context_limits_evidence_rows() -> None:
    run = SimpleNamespace(
        id="parent-id",
        question="哪个渠道收入最高？",
        result={
            "report": "Organic 最高。",
            "sql": "SELECT channel, revenue FROM result",
            "columns": ["channel", "revenue"],
            "rows": [{"row": index} for index in range(50)],
        },
    )

    context = build_follow_up_context(run)

    assert context["request_id"] == "parent-id"
    assert context["question"] == "哪个渠道收入最高？"
    assert len(context["rows"]) == 30
    assert context["rows"][-1] == {"row": 29}
