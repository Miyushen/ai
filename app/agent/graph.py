from functools import lru_cache
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.agent.nodes import (
    analysis_node,
    execute_sql_node,
    failure_node,
    plan_node,
    report_node,
    review_node,
    schema_node,
    sql_generation_node,
    validate_sql_node,
)
from app.agent.state import AgentState
from app.core.config import get_settings


def _retry_transient_model_error(exc: Exception) -> bool:
    """Retry provider transport failures and 5xx responses, but never bad requests."""
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        status_code = getattr(current, "status_code", None)
        response = getattr(current, "response", None)
        if status_code is None and response is not None:
            status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and status_code >= 500:
            return True
        if type(current).__name__ in {
            "APIConnectionError",
            "APITimeoutError",
            "OpenAIConnectionError",
        }:
            return True
        current = current.__cause__ or current.__context__
    return False


def _model_retry_policy() -> RetryPolicy:
    return RetryPolicy(
        initial_interval=1.0,
        backoff_factor=2.0,
        max_interval=8.0,
        max_attempts=get_settings().model_node_max_attempts,
        retry_on=_retry_transient_model_error,
    )


def _after_validation(state: AgentState) -> Literal["execute", "retry", "fail"]:
    if not state.get("error"):
        return "execute"
    if state.get("attempts", 0) < get_settings().max_agent_retries:
        return "retry"
    return "fail"


def _after_execution(state: AgentState) -> Literal["analyze", "retry", "fail"]:
    if not state.get("error"):
        return "analyze"
    if state.get("attempts", 0) < get_settings().max_agent_retries:
        return "retry"
    return "fail"


def _after_review(state: AgentState) -> Literal["report", "retry"]:
    if state.get("review", {}).get("approved", False):
        return "report"
    if state.get("attempts", 0) < get_settings().max_agent_retries:
        return "retry"
    return "report"


@lru_cache
def get_graph():
    builder = StateGraph(AgentState)
    model_retry = _model_retry_policy()
    builder.add_node("plan", plan_node, retry_policy=model_retry)
    builder.add_node("schema", schema_node)
    builder.add_node("generate_sql", sql_generation_node, retry_policy=model_retry)
    builder.add_node("validate_sql", validate_sql_node)
    builder.add_node("execute_sql", execute_sql_node)
    builder.add_node("analyze", analysis_node, retry_policy=model_retry)
    builder.add_node("review", review_node, retry_policy=model_retry)
    builder.add_node("report", report_node, retry_policy=model_retry)
    builder.add_node("failure", failure_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "schema")
    builder.add_edge("schema", "generate_sql")
    builder.add_edge("generate_sql", "validate_sql")
    builder.add_conditional_edges(
        "validate_sql",
        _after_validation,
        {"execute": "execute_sql", "retry": "generate_sql", "fail": "failure"},
    )
    builder.add_conditional_edges(
        "execute_sql",
        _after_execution,
        {"analyze": "analyze", "retry": "generate_sql", "fail": "failure"},
    )
    builder.add_edge("analyze", "review")
    builder.add_conditional_edges(
        "review",
        _after_review,
        {"report": "report", "retry": "generate_sql"},
    )
    builder.add_edge("report", END)
    builder.add_edge("failure", END)
    return builder.compile()


def run_agent(question: str, request_id: str) -> AgentState:
    initial: AgentState = {
        "request_id": request_id,
        "question": question,
        "trace": [],
    }
    return get_graph().invoke(initial)
