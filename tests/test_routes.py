import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.routes import analyze
from app.api.schemas import AnalyzeRequest


def test_follow_up_analysis_passes_parent_context_and_persists_result() -> None:
    parent = SimpleNamespace(status="completed", result={"report": "parent"})
    context = {"question": "parent question", "report": "parent"}
    state = {
        "report": "follow-up report",
        "plan": {},
        "rows": [{"channel": "Organic"}],
        "review": {"approved": True, "confidence": 0.9},
        "trace": [],
        "attempts": 1,
    }
    settings = SimpleNamespace(has_openai_key=True, openai_model="test-model")

    with (
        patch("app.api.routes.get_settings", return_value=settings),
        patch("app.api.routes.get_analysis_run", return_value=parent),
        patch("app.api.routes.build_follow_up_context", return_value=context),
        patch("app.api.routes.create_analysis_run") as create_run,
        patch("app.api.routes.complete_analysis_run") as complete_run,
        patch("app.api.routes.run_agent", return_value=state) as run_agent,
    ):
        response = asyncio.run(
            analyze(AnalyzeRequest(question="继续分析地区差异", parent_request_id="parent-id"))
        )

    assert response.parent_request_id == "parent-id"
    assert response.report == "follow-up report"
    assert run_agent.call_args.args[2] == context
    assert create_run.call_args.kwargs["parent_request_id"] == "parent-id"
    complete_run.assert_called_once()


def test_follow_up_rejects_unknown_parent() -> None:
    settings = SimpleNamespace(has_openai_key=True, openai_model="test-model")
    with (
        patch("app.api.routes.get_settings", return_value=settings),
        patch("app.api.routes.get_analysis_run", return_value=None),
    ):
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                analyze(AnalyzeRequest(question="继续分析地区差异", parent_request_id="missing"))
            )

    assert error.value.status_code == 404


def test_provider_failure_marks_run_as_failed() -> None:
    settings = SimpleNamespace(has_openai_key=True, openai_model="test-model")
    with (
        patch("app.api.routes.get_settings", return_value=settings),
        patch("app.api.routes.create_analysis_run"),
        patch("app.api.routes.fail_analysis_run") as fail_run,
        patch("app.api.routes.run_agent", side_effect=RuntimeError("provider unavailable")),
    ):
        with pytest.raises(HTTPException) as error:
            asyncio.run(analyze(AnalyzeRequest(question="分析最近渠道收入")))

    assert error.value.status_code == 502
    fail_run.assert_called_once()
