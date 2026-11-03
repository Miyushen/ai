import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from app.agent.graph import run_agent
from app.api.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.core.config import get_settings
from app.db.base import engine
from app.services.schema_service import get_business_schema

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


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    if not settings.has_openai_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Add it to .env and restart the API.",
        )

    request_id = str(uuid4())
    try:
        state = await run_in_threadpool(run_agent, payload.question, request_id)
    except Exception as exc:
        logger.warning("Agent execution failed with %s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail=(
                "Model provider request failed. Check OPENAI_API_KEY, model access, "
                "and API billing, then retry."
            ),
        ) from exc

    return AnalyzeResponse(
        request_id=request_id,
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
        error=state.get("error"),
    )

