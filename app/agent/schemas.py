from typing import Literal

from pydantic import BaseModel, Field


class PlanOutput(BaseModel):
    objective: str
    steps: list[str] = Field(min_length=1, max_length=6)
    assumptions: list[str] = Field(default_factory=list, max_length=5)
    required_metrics: list[str] = Field(default_factory=list, max_length=8)


class SqlOutput(BaseModel):
    sql: str
    explanation: str


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "scatter"]
    x: str
    y: str
    title: str


class AnalysisOutput(BaseModel):
    summary: str
    findings: list[str] = Field(min_length=1, max_length=6)
    caveats: list[str] = Field(default_factory=list, max_length=5)
    chart: ChartSpec | None = None


class ReviewOutput(BaseModel):
    approved: bool
    confidence: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list, max_length=6)
    retry_instruction: str | None = None

