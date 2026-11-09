import logging
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from app.agent.graph import run_agent
from app.api.schemas import AnalysisRunSummary, AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.core.config import get_settings
from app.db.base import engine
from app.services.schema_service import get_business_schema
from app.services.run_history import (
    build_follow_up_context,
    complete_analysis_run,
    create_analysis_run,
    fail_analysis_run,
    get_analysis_run,
    list_analysis_runs,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database_status = "unavailable"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        pass
    settings = get_settings()
    return HealthResponse(
        status="ok" if database_status == "ok" else "degraded",
        database=database_status,
        openai_key_configured=settings.has_openai_key,
        model=settings.openai_model,
    )


@router.get("/schema")
def schema() -> dict:
    return get_business_schema()


@router.get("/runs", response_model=list[AnalysisRunSummary])
def runs(limit: int = 20) -> list[AnalysisRunSummary]:
    bounded_limit = min(max(limit, 1), 100)
    return [
        AnalysisRunSummary(
            request_id=run.id,
            parent_request_id=run.parent_request_id,
            question=run.question,
            status=run.status,
            model=run.model,
            total_duration_ms=run.total_duration_ms,
            created_at=run.created_at,
            completed_at=run.completed_at,
            approved=(run.result or {}).get("review", {}).get("approved"),
            error=run.error,
        )
        for run in list_analysis_runs(bounded_limit)
    ]


@router.get("/runs/{request_id}", response_model=AnalyzeResponse)
def run_detail(request_id: str) -> AnalyzeResponse:
    run = get_analysis_run(request_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run was not found.")
    if run.status != "completed" or not run.result:
        raise HTTPException(status_code=409, detail=f"Analysis run is {run.status}.")
    return AnalyzeResponse.model_validate(run.result)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    if not settings.has_openai_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Add it to .env and restart the API.",
        )

    request_id = str(uuid4())
    previous_analysis = None
    if payload.parent_request_id:
        parent_run = get_analysis_run(payload.parent_request_id)
        if parent_run is None:
            raise HTTPException(status_code=404, detail="Parent analysis run was not found.")
        if parent_run.status != "completed" or not parent_run.result:
            raise HTTPException(status_code=409, detail="Parent analysis run is not completed.")
        previous_analysis = build_follow_up_context(parent_run)

    create_analysis_run(
        request_id=request_id,
        question=payload.question,
        model=settings.openai_model,
        parent_request_id=payload.parent_request_id,
    )
    started_at = perf_counter()
    try:
        state = await run_in_threadpool(
            run_agent,
            payload.question,
            request_id,
            previous_analysis,
        )
    except Exception as exc:
        logger.warning("Agent execution failed with %s", type(exc).__name__)
        total_duration_ms = round((perf_counter() - started_at) * 1000, 2)
        fail_analysis_run(
            request_id,
            f"Model provider request failed ({type(exc).__name__}).",
            total_duration_ms,
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "Model provider request failed. Check OPENAI_API_KEY, model access, "
                "and API billing, then retry."
            ),
        ) from exc

    total_duration_ms = round((perf_counter() - started_at) * 1000, 2)
    logger.info(
        "Agent execution completed request_id=%s duration_ms=%.2f attempts=%s",
        request_id,
        total_duration_ms,
        state.get("attempts", 0),
    )

    response = AnalyzeResponse(
        request_id=request_id,
        parent_request_id=payload.parent_request_id,
        question=payload.question,
        report=state.get("report", ""),
        plan=state.get("plan", {}),
        sql=state.get("sql"),
        sql_explanation=state.get("sql_explanation"),
        columns=state.get("columns", []),
        rows=state.get("rows", []),
        analysis=state.get("analysis", {}),
        review=state.get("review", {}),
        trace=state.get("trace", []),
        attempts=state.get("attempts", 0),
        total_duration_ms=total_duration_ms,
        error=state.get("error"),
    )
    complete_analysis_run(
        request_id,
        response.model_dump(mode="json"),
        total_duration_ms,
    )
    return response

