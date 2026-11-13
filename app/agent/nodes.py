import json
from functools import wraps
from time import perf_counter
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.schemas import AnalysisOutput, PlanOutput, ReviewOutput, SqlOutput
from app.agent.state import AgentState
from app.core.config import get_settings
from app.services.model_usage import extract_usage_event
from app.services.schema_service import get_business_schema
from app.services.sql_executor import execute_read_only
from app.services.sql_guard import SqlValidationError, validate_and_rewrite_sql


def _llm() -> ChatOpenAI:
    settings = get_settings()
    if not settings.has_openai_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    model_options: dict[str, Any] = {}
    if settings.openai_reasoning_effort:
        model_options["reasoning_effort"] = settings.openai_reasoning_effort
    if settings.openai_verbosity:
        model_options["verbosity"] = settings.openai_verbosity
    if settings.openai_max_completion_tokens > 0:
        model_options["max_completion_tokens"] = settings.openai_max_completion_tokens
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        openai_api_base=settings.openai_base_url,
        use_responses_api=settings.openai_use_responses_api,
        output_version="responses/v1",
        timeout=45,
        # LangGraph owns retries so each attempt remains visible and configurable.
        max_retries=0,
        **model_options,
    )


def _trace(node: str, status: str, detail: str) -> list[dict[str, Any]]:
    return [{"node": node, "status": status, "detail": detail}]


def _timed_node(node: str):
    """Attach wall-clock duration to every completed graph node event."""

    def decorate(function):
        @wraps(function)
        def wrapped(state: AgentState) -> dict[str, Any]:
            started_at = perf_counter()
            result = function(state)
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            for event in result.get("trace", []):
                event.setdefault("node", node)
                event.setdefault("duration_ms", duration_ms)
            return result

        return wrapped

    return decorate


def _message_text(message: Any) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(getattr(block, "text", None), str):
                parts.append(block.text)
        if parts:
            return "\n".join(parts)
    return str(content)


def _invoke_structured(
    node: str,
    schema: Any,
    messages: list[Any],
) -> tuple[Any, list[dict[str, Any]]]:
    result = _llm().with_structured_output(schema, include_raw=True).invoke(messages)
    if not isinstance(result, dict):
        return result, []
    parsed = result.get("parsed")
    if parsed is None:
        error = result.get("parsing_error")
        raise error or RuntimeError(f"{node} returned no structured output.")
    return parsed, [extract_usage_event(node, result.get("raw"))]


@_timed_node("planner")
def plan_node(state: AgentState) -> dict[str, Any]:
    output, usage = _invoke_structured(
        "planner",
        PlanOutput,
        [
            SystemMessage(
                content=(
                    "You are a senior business analyst. Decompose the user's question into a "
                    "small evidence-driven analysis plan. Do not invent unavailable data."
                )
            ),
            HumanMessage(
                content=json.dumps(
                    {
                        "question": state["question"],
                        "previous_analysis": state.get("previous_analysis", {}),
                    },
                    ensure_ascii=False,
                    default=str,
                )
            ),
        ],
    )
    return {
        "plan": output.model_dump(),
        "attempts": 0,
        "review_iterations": 0,
        "error": None,
        "trace": _trace("planner", "ok", f"Created {len(output.steps)} analysis steps."),
        "model_usage_events": usage,
    }


@_timed_node("schema")
def schema_node(_: AgentState) -> dict[str, Any]:
    schema = get_business_schema()
    return {
        "schema": schema,
        "trace": _trace("schema", "ok", f"Loaded {len(schema)} allowlisted tables."),
    }


@_timed_node("sql_generator")
def sql_generation_node(state: AgentState) -> dict[str, Any]:
    previous_error = state.get("error") or "none"
    review = state.get("review", {})
    prompt = {
        "question": state["question"],
        "plan": state["plan"],
        "database_schema": state["schema"],
        "previous_error": previous_error,
        "review_feedback": review.get("retry_instruction") or review.get("issues", []),
        "previous_analysis": state.get("previous_analysis", {}),
    }
    output, usage = _invoke_structured(
        "sql_generator",
        SqlOutput,
        [
            SystemMessage(
                content=(
                    "Generate one PostgreSQL SELECT query that answers the question. Use only the "
                    "provided tables and columns. Prefer explicit joins, clear aliases, and evidence "
                    "that can be inspected. Never emit INSERT, UPDATE, DELETE, DDL, comments, or "
                    "multiple statements. Metric definitions are business guidance, not executable SQL. "
                    "For relative periods such as recent 30 days, anchor the window to the relevant "
                    "table's max_date from data_coverage, never CURRENT_DATE, unless the user explicitly "
                    "requests the system date. "
                    "Use business_metrics as authoritative metric definitions. For Chinese '收入' or "
                    "English 'revenue', use the revenue definition; use net_revenue only when the user "
                    "explicitly asks for net revenue or revenue after refunds. "
                    "When the question asks for highest, lowest, top, or bottom groups, compute ranks "
                    "over the complete grouped result in a CTE and filter to the requested extrema "
                    "before the final SELECT so the server row limit cannot hide a required extreme. "
                    "Use exactly the comparison group or time period requested by the user; do not "
                    "invent historical cohorts, alternate metric definitions, or significance tests. "
                    "Keep the query concise with no more than three CTEs."
                )
            ),
            HumanMessage(content=json.dumps(prompt, ensure_ascii=False, default=str)),
        ],
    )
    attempt = state.get("attempts", 0) + 1
    return {
        "sql": output.sql,
        "sql_explanation": output.explanation,
        "attempts": attempt,
        "error": None,
        "trace": _trace("sql_generator", "ok", f"Generated SQL attempt {attempt}."),
        "model_usage_events": usage,
    }


@_timed_node("sql_guard")
def validate_sql_node(state: AgentState) -> dict[str, Any]:
    settings = get_settings()
    try:
        safe_sql = validate_and_rewrite_sql(state["sql"], settings.max_sql_rows)
    except SqlValidationError as exc:
        return {
            "error": str(exc),
            "trace": _trace("sql_guard", "retry", str(exc)),
        }
    return {
        "sql": safe_sql,
        "error": None,
        "trace": _trace("sql_guard", "ok", "SQL passed AST and allowlist checks."),
    }


@_timed_node("executor")
def execute_sql_node(state: AgentState) -> dict[str, Any]:
    try:
        columns, rows = execute_read_only(state["sql"])
    except Exception as exc:  # Database errors become repair feedback for the agent.
        return {
            "error": f"Database execution failed: {exc}",
            "trace": _trace("executor", "retry", str(exc)),
        }
    if not rows:
        error = "Query returned no evidence rows; revise the filters, joins, or aggregation."
        return {
            "columns": columns,
            "rows": [],
            "error": error,
            "trace": _trace("executor", "retry", error),
        }
    return {
        "columns": columns,
        "rows": rows,
        "error": None,
        "trace": _trace("executor", "ok", f"Returned {len(rows)} rows."),
    }


@_timed_node("analyst")
def analysis_node(state: AgentState) -> dict[str, Any]:
    evidence = {
        "question": state["question"],
        "plan": state["plan"],
        "sql": state["sql"],
        "columns": state.get("columns", []),
        "rows": state.get("rows", [])[:80],
    }
    output, usage = _invoke_structured(
        "analyst",
        AnalysisOutput,
        [
            SystemMessage(
                content=(
                    "Analyze only the supplied query results. Every numerical claim must be supported "
                    "by a visible row. State caveats when the data is insufficient. Provide a chart only "
                    "when its x and y fields exactly match returned column names."
                )
            ),
            HumanMessage(content=json.dumps(evidence, ensure_ascii=False, default=str)),
        ],
    )
    analysis = output.model_dump()
    chart = analysis.get("chart")
    if chart and (chart["x"] not in state["columns"] or chart["y"] not in state["columns"]):
        analysis["chart"] = None
        analysis["caveats"].append("Requested chart fields were not present in the result set.")
    return {
        "analysis": analysis,
        "trace": _trace("analyst", "ok", f"Produced {len(output.findings)} findings."),
        "model_usage_events": usage,
    }


@_timed_node("reviewer")
def review_node(state: AgentState) -> dict[str, Any]:
    review_payload = {
        "question": state["question"],
        "sql": state["sql"],
        "rows": state.get("rows", [])[:80],
        "analysis": state["analysis"],
    }
    output, usage = _invoke_structured(
        "reviewer",
        ReviewOutput,
        [
            SystemMessage(
                content=(
                    "Act as an independent reviewer. Approve only when the SQL results support the "
                    "analysis, no conclusion overreaches the evidence, and the original question is "
                    "answered. Give a concrete retry instruction when rejecting."
                )
            ),
            HumanMessage(content=json.dumps(review_payload, ensure_ascii=False, default=str)),
        ],
    )
    iteration = state.get("review_iterations", 0) + 1
    return {
        "review": output.model_dump(),
        "review_iterations": iteration,
        "trace": _trace(
            "reviewer",
            "ok" if output.approved else "retry",
            f"Approved={output.approved}; confidence={output.confidence:.2f}.",
        ),
        "model_usage_events": usage,
    }


@_timed_node("reporter")
def report_node(state: AgentState) -> dict[str, Any]:
    analysis = state["analysis"]
    review = state.get("review", {})
    report_prompt = {
        "question": state["question"],
        "analysis": analysis,
        "review": review,
        "sql": state["sql"],
        "previous_question": state.get("previous_analysis", {}).get("question"),
    }
    response = _llm().invoke(
        [
            SystemMessage(
                content=(
                    "Write a concise Chinese business analysis report with sections for conclusion, "
                    "evidence, recommendations, and limitations. Do not add facts beyond the payload."
                )
            ),
            HumanMessage(content=json.dumps(report_prompt, ensure_ascii=False, default=str)),
        ]
    )
    return {
        "report": _message_text(response),
        "trace": _trace("reporter", "ok", "Generated the final evidence-linked report."),
        "model_usage_events": [extract_usage_event("reporter", response)],
    }


@_timed_node("failure")
def failure_node(state: AgentState) -> dict[str, Any]:
    error = state.get("error") or "The agent could not complete the analysis."
    return {
        "report": f"分析未完成。原因：{error}",
        "trace": _trace("failure", "failed", error),
    }

