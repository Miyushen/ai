from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    parent_request_id: str | None = Field(default=None, max_length=36)


class TraceEvent(BaseModel):
    node: str
    status: str
    detail: str
    duration_ms: float = Field(default=0, ge=0)


class AnalyzeResponse(BaseModel):
    request_id: str
    parent_request_id: str | None = None
    question: str
    report: str
    plan: dict[str, Any] = Field(default_factory=dict)
    sql: str | None = None
    sql_explanation: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    analysis: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    trace: list[TraceEvent] = Field(default_factory=list)
    attempts: int = 0
    total_duration_ms: float = Field(default=0, ge=0)
    error: str | None = None


class AnalysisRunSummary(BaseModel):
    request_id: str
    parent_request_id: str | None = None
    question: str
    status: Literal["running", "completed", "failed"]
    model: str
    total_duration_ms: float | None = None
    created_at: datetime
    completed_at: datetime | None = None
    approved: bool | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    openai_key_configured: bool
    model: str

