import os
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="InsightAgent", page_icon="IA", layout="wide")
st.title("InsightAgent")
st.caption("Autonomous business data analysis with inspectable SQL, evidence, and review")


def get_health() -> dict[str, Any]:
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        return {"status": "offline", "database": "unknown", "error": str(exc)}


def render_chart(rows: list[dict[str, Any]], spec: dict[str, Any] | None) -> None:
    if not rows or not spec:
        return
    frame = pd.DataFrame(rows)
    if spec.get("x") not in frame.columns or spec.get("y") not in frame.columns:
        return
    chart_type = spec.get("type")
    if chart_type == "line":
        figure = px.line(frame, x=spec["x"], y=spec["y"], title=spec.get("title"))
    elif chart_type == "scatter":
        figure = px.scatter(frame, x=spec["x"], y=spec["y"], title=spec.get("title"))
    else:
        figure = px.bar(frame, x=spec["x"], y=spec["y"], title=spec.get("title"))
    figure.update_layout(margin=dict(l=10, r=10, t=48, b=10))
    st.plotly_chart(figure, use_container_width=True)


health = get_health()
status_columns = st.columns(4)
status_columns[0].metric("API", health.get("status", "unknown"))
status_columns[1].metric("Database", health.get("database", "unknown"))
status_columns[2].metric("OpenAI key", "ready" if health.get("openai_key_configured") else "missing")
status_columns[3].metric("Model", health.get("model", "unknown"))

examples = [
    "过去30天哪个地区的销售额下降最明显？请给出证据。",
    "电子产品退款率是否出现异常？主要原因是什么？",
    "Paid Search 最近30天的广告投入是否带来了匹配的业务增长？",
    "按渠道比较最近90天的收入趋势，并指出值得关注的变化。",
]

selected_example = st.selectbox("Example questions", ["Custom question", *examples])
default_question = "" if selected_example == "Custom question" else selected_example
question = st.text_area("Business question", value=default_question, height=90)
run_clicked = st.button("Run analysis", type="primary", use_container_width=False)

if run_clicked:
    if len(question.strip()) < 5:
        st.warning("Enter a business question with at least five characters.")
    else:
        with st.status("Agent is analyzing the data...", expanded=True) as status:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/analyze",
                    json={"question": question.strip()},
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()
                status.update(label="Analysis complete", state="complete", expanded=False)
                st.session_state["last_result"] = result
            except requests.RequestException as exc:
                detail = exc.response.text if getattr(exc, "response", None) is not None else str(exc)
                status.update(label="Analysis failed", state="error", expanded=True)
                st.error(detail)

result = st.session_state.get("last_result")
if result:
    review = result.get("review", {})
    summary_columns = st.columns(4)
    summary_columns[0].metric("SQL attempts", result.get("attempts", 0))
    summary_columns[1].metric("Evidence rows", len(result.get("rows", [])))
    summary_columns[2].metric("Reviewer", "approved" if review.get("approved") else "needs review")
    summary_columns[3].metric("Confidence", f"{review.get('confidence', 0):.0%}")

    report_tab, evidence_tab, trace_tab, review_tab = st.tabs(
        ["Report", "Evidence", "Execution trace", "Reviewer"]
    )
    with report_tab:
        st.markdown(result.get("report", ""))
        render_chart(result.get("rows", []), result.get("analysis", {}).get("chart"))
    with evidence_tab:
        st.code(result.get("sql") or "No SQL generated", language="sql")
        if result.get("sql_explanation"):
            st.caption(result["sql_explanation"])
        if result.get("rows"):
            st.dataframe(pd.DataFrame(result["rows"]), use_container_width=True, hide_index=True)
    with trace_tab:
        trace_frame = pd.DataFrame(result.get("trace", []))
        if not trace_frame.empty:
            st.dataframe(trace_frame, use_container_width=True, hide_index=True)
        st.json(result.get("plan", {}))
    with review_tab:
        st.json(review)
        st.json(result.get("analysis", {}))

