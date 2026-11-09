from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import AnalysisRun


def create_analysis_run(
    request_id: str,
    question: str,
    model: str,
    parent_request_id: str | None = None,
) -> None:
    with SessionLocal.begin() as session:
        session.add(
            AnalysisRun(
                id=request_id,
                parent_request_id=parent_request_id,
                question=question,
                status="running",
                model=model,
            )
        )


def complete_analysis_run(
    request_id: str,
    result: dict[str, Any],
    total_duration_ms: float,
) -> None:
    with SessionLocal.begin() as session:
        run = session.get(AnalysisRun, request_id)
        if run is None:
            return
        run.status = "completed"
        run.result = result
        run.total_duration_ms = total_duration_ms
        run.completed_at = datetime.now(timezone.utc)
        run.error = None


def fail_analysis_run(request_id: str, error: str, total_duration_ms: float) -> None:
    with SessionLocal.begin() as session:
        run = session.get(AnalysisRun, request_id)
        if run is None:
            return
        run.status = "failed"
        run.error = error
        run.total_duration_ms = total_duration_ms
        run.completed_at = datetime.now(timezone.utc)


def get_analysis_run(request_id: str) -> AnalysisRun | None:
    with SessionLocal() as session:
        run = session.get(AnalysisRun, request_id)
        if run is None:
            return None
        session.expunge(run)
        return run


def list_analysis_runs(limit: int = 20) -> list[AnalysisRun]:
    with SessionLocal() as session:
        runs = list(
            session.scalars(
                select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit)
            )
        )
        for run in runs:
            session.expunge(run)
        return runs


def build_follow_up_context(run: AnalysisRun) -> dict[str, Any]:
    result = run.result or {}
    return {
        "request_id": run.id,
        "question": run.question,
        "report": result.get("report", ""),
        "sql": result.get("sql"),
        "columns": result.get("columns", []),
        "rows": result.get("rows", [])[:30],
    }
