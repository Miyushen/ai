import operator
from typing import Annotated, Any, TypedDict


class TraceEvent(TypedDict):
    node: str
    status: str
    detail: str


class AgentState(TypedDict, total=False):
    request_id: str
    question: str
    plan: dict[str, Any]
    schema: dict[str, Any]
    sql: str
    sql_explanation: str
    attempts: int
    review_iterations: int
    columns: list[str]
    rows: list[dict[str, Any]]
    analysis: dict[str, Any]
    review: dict[str, Any]
    report: str
    error: str | None
    trace: Annotated[list[TraceEvent], operator.add]

