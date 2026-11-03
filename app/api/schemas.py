from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


class AnalyzeResponse(BaseModel):
    request_id: str
    question: str
    report: str
    plan: dict[str, Any] = Field(default_factory=dict)
    sql: str | None = None
    sql_explanation: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    analysis: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, str]] = Field(default_factory=list)
    attempts: int = 0
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    openai_key_configured: bool
    model: str

