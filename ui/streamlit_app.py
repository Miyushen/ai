import html
import json
import os
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

EXAMPLES = {
    "地区趋势": "过去30天哪个地区的销售额下降最明显？请与之前30天比较。",
    "退款异常": "最近45天电子产品退款率是否异常？请与其他品类比较。",
    "广告效率": "Paid Search 最近30天广告投入是否带来了匹配的访问和销售增长？",
    "渠道收入": "按渠道比较最近90天收入，并指出贡献最高和最低的渠道。",
}

NODE_LABELS = {
    "planner": "问题规划",
    "schema": "读取结构",
    "sql_generator": "生成 SQL",
    "sql_guard": "安全校验",
    "executor": "执行查询",
    "analyst": "证据分析",
    "reviewer": "质量复核",
    "reporter": "生成报告",
    "failure": "执行终止",
}

st.set_page_config(
    page_title="InsightAgent | 数据分析工作台",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #202226;
        --muted: #686d73;
        --line: #e2e4e7;
        --panel: #ffffff;
        --canvas: #f7f8fa;
        --green: #147a61;
        --green-soft: #eaf4f0;
        --amber: #a96612;
        --red: #b94a3d;
        --red-soft: #faece9;
    }
    html, body, [class*="css"] {
        font-family: Inter, "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
        letter-spacing: 0 !important;
    }
    .stApp { background: var(--canvas); color: var(--ink); }
    .block-container { max-width: 1320px; padding: 1.35rem 2.25rem 3rem; }
    header[data-testid="stHeader"], #MainMenu, footer { display: none; }
    [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }

    section[data-testid="stSidebar"] {
        background: #f1f3f4; border-right: 1px solid var(--line);
        min-width: 280px; max-width: 280px;
    }
    section[data-testid="stSidebar"] .block-container { padding: 1.3rem 1rem 2rem; }
    .ia-brand { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 1.6rem; }
    .ia-mark {
        width: 34px; height: 34px; display: grid; place-items: center;
        background: var(--ink); color: white; border-radius: 6px;
        font-size: 0.78rem; font-weight: 800;
    }
    .ia-brand-name { font-size: 1rem; line-height: 1.1; font-weight: 750; }
    .ia-brand-meta { color: var(--muted); font-size: 0.72rem; margin-top: 0.2rem; }
    .ia-section-label {
        color: #767b81; font-size: 0.72rem; font-weight: 700;
        text-transform: uppercase; margin: 1.35rem 0 0.55rem;
    }
    .ia-status-list { border-top: 1px solid var(--line); }
    .ia-status-row {
        min-height: 38px; display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid var(--line); color: #4a4e53; font-size: 0.8rem;
    }
    .ia-status-value { display: inline-flex; align-items: center; gap: 0.4rem; font-weight: 650; color: var(--ink); }
    .ia-dot { width: 7px; height: 7px; border-radius: 50%; background: #9ca1a6; }
    .ia-dot.ok { background: var(--green); }
    .ia-dot.bad { background: var(--red); }

    .ia-header {
        display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: end;
        padding-bottom: 1rem; margin-bottom: 1.15rem; border-bottom: 1px solid var(--line);
    }
    .ia-eyebrow { color: var(--green); font-size: 0.74rem; font-weight: 750; margin-bottom: 0.25rem; }
    .ia-title { font-size: 1.65rem; line-height: 1.2; font-weight: 760; color: var(--ink); }
    .ia-subtitle { color: var(--muted); font-size: 0.86rem; margin-top: 0.35rem; }
    .ia-live {
        display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.35rem 0.55rem;
        border: 1px solid #bdd7cd; border-radius: 5px; background: var(--green-soft);
        color: #0d654f; font-size: 0.76rem; font-weight: 700;
    }

    .ia-prompt-label { font-size: 0.82rem; font-weight: 700; color: #3f4348; margin-bottom: 0.35rem; }
    div[data-testid="stForm"] {
        background: var(--panel); border: 1px solid var(--line); border-radius: 7px;
        padding: 0.8rem 0.95rem 0.9rem; box-shadow: 0 1px 2px rgba(32,34,38,0.04);
    }
    div[data-testid="stTextArea"] textarea {
        min-height: 96px; background: #fbfbfc; border: 1px solid #d8dbde;
        border-radius: 5px; color: var(--ink); font-size: 0.94rem; line-height: 1.55;
    }
    div[data-testid="stTextArea"] textarea:focus { border-color: var(--green); box-shadow: 0 0 0 1px var(--green); }

    .stButton button, .stDownloadButton button, div[data-testid="stFormSubmitButton"] button {
        border-radius: 5px; min-height: 38px; font-weight: 680; letter-spacing: 0;
    }
    button[kind="primary"] { background: var(--green) !important; border-color: var(--green) !important; }
    button[kind="primary"]:hover { background: #0f6751 !important; border-color: #0f6751 !important; }
    section[data-testid="stSidebar"] .stButton button {
        width: 100%; justify-content: flex-start; border: 0; background: transparent;
        color: #4f5459; font-weight: 550; padding-left: 0.45rem;
    }
    section[data-testid="stSidebar"] .stButton button:hover { background: #e6e9e8; color: var(--ink); }
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: var(--green) !important; border-color: var(--green) !important;
        color: #ffffff !important; justify-content: center;
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
        background: #0f6751 !important; color: #ffffff !important;
    }

    div[data-testid="stMetric"] {
        min-height: 96px; background: var(--panel); border: 1px solid var(--line);
        border-radius: 6px; padding: 0.8rem 0.9rem; box-shadow: 0 1px 2px rgba(32,34,38,0.03);
    }
    div[data-testid="stMetric"] label { color: var(--muted); font-size: 0.76rem; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.45rem; font-weight: 720; }
    div[data-testid="stStatusWidget"] { border: 1px solid var(--line); border-radius: 6px; background: var(--panel); }

    .ia-result-head {
        display: flex; align-items: center; justify-content: space-between;
        margin: 1.6rem 0 0.65rem;
    }
    .ia-result-title { font-size: 1rem; font-weight: 740; }
    .ia-request-id { color: #858a90; font-family: monospace; font-size: 0.7rem; }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 1.2rem; border-bottom: 1px solid var(--line); }
    div[data-testid="stTabs"] [data-baseweb="tab"] { height: 44px; padding: 0; font-weight: 650; color: #666b71; }
    div[data-testid="stTabs"] [aria-selected="true"] { color: var(--green); }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: 1rem; }

    .ia-section-title { font-size: 0.88rem; font-weight: 730; margin: 0.2rem 0 0.7rem; }
    .ia-findings { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--line); }
    .ia-findings li { padding: 0.68rem 0; border-bottom: 1px solid var(--line); font-size: 0.86rem; line-height: 1.5; }
    .ia-findings li::before {
        content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
        background: var(--green); margin-right: 0.55rem; vertical-align: 0.12rem;
    }

    .ia-timeline { border-left: 2px solid #d9dcdf; margin: 0.4rem 0 0 0.45rem; }
    .ia-trace-row {
        position: relative; display: grid; grid-template-columns: 125px 1fr;
        gap: 0.8rem; padding: 0 0 1rem 1.25rem;
    }
    .ia-trace-row::before {
        content: ""; position: absolute; left: -6px; top: 3px; width: 10px; height: 10px;
        border-radius: 50%; background: var(--green); border: 2px solid var(--canvas);
    }
    .ia-trace-row.retry::before { background: var(--amber); }
    .ia-trace-row.failed::before { background: var(--red); }
    .ia-trace-node { color: var(--ink); font-size: 0.82rem; font-weight: 720; }
    .ia-trace-detail { color: var(--muted); font-size: 0.8rem; line-height: 1.45; }

    .ia-review-banner {
        display: flex; align-items: center; justify-content: space-between; gap: 1rem;
        padding: 0.85rem 1rem; border-radius: 6px; border: 1px solid #bdd7cd;
        background: var(--green-soft); color: #0d654f;
    }
    .ia-review-banner.rejected { border-color: #e6bcb6; background: var(--red-soft); color: #94392f; }
    .ia-review-main { font-weight: 740; }
    .ia-review-score { font-size: 1.2rem; font-weight: 780; }
    .ia-empty {
        margin-top: 1.25rem; padding: 2.4rem 1rem; text-align: center;
        border-top: 1px solid var(--line); color: var(--muted);
    }
    .ia-empty-title { color: #474b50; font-weight: 700; font-size: 0.92rem; }
    .ia-empty-meta { margin-top: 0.35rem; font-size: 0.78rem; }

    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
    [data-testid="stCode"] { border-radius: 6px; }
    [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 6px; background: var(--panel); }
    [data-testid="stPlotlyChart"] { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }

    @media (max-width: 800px) {
        .block-container { padding: 1rem 0.85rem 2rem; }
        .ia-header { grid-template-columns: 1fr; align-items: start; }
        .ia-title { font-size: 1.35rem; }
        .ia-trace-row { grid-template-columns: 1fr; gap: 0.2rem; }
        .ia-request-id { display: none; }
        .ia-review-banner { align-items: flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10, show_spinner=False)
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
    common = {"data_frame": frame, "x": spec["x"], "y": spec["y"], "title": spec.get("title")}
    if spec.get("type") == "line":
        figure = px.line(**common, markers=True)
    elif spec.get("type") == "scatter":
        figure = px.scatter(**common)
    else:
        figure = px.bar(**common)
    figure.update_traces(marker_color="#147a61")
    figure.update_layout(
        margin=dict(l=20, r=20, t=54, b=20), paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff", font=dict(color="#34383d"), title_font=dict(size=15),
        xaxis=dict(gridcolor="#eceeef"), yaxis=dict(gridcolor="#eceeef"),
    )
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def render_trace(trace: list[dict[str, str]]) -> None:
    if not trace:
        st.info("本次运行没有执行轨迹。")
        return
    rows = []
    for event in trace:
        status = event.get("status", "ok")
        css_status = status if status in {"retry", "failed"} else "ok"
        node = NODE_LABELS.get(event.get("node", ""), event.get("node", "未知节点"))
        rows.append(
            f'<div class="ia-trace-row {css_status}">'
            f'<div class="ia-trace-node">{html.escape(node)}</div>'
            f'<div class="ia-trace-detail">{html.escape(event.get("detail", ""))}</div></div>'
        )
    st.markdown(f'<div class="ia-timeline">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_findings(items: list[str]) -> None:
    if items:
        content = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        st.markdown(f'<ul class="ia-findings">{content}</ul>', unsafe_allow_html=True)


def run_analysis(question: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/api/v1/analyze", json={"question": question}, timeout=600
    )
    if not response.ok:
        try:
            detail = response.json().get("detail", "分析服务返回错误。")
        except ValueError:
            detail = "分析服务返回错误。"
        raise RuntimeError(detail)
    return response.json()


def remember_result(result: dict[str, Any]) -> None:
    history = st.session_state.setdefault("run_history", [])
    history.insert(
        0,
        {
            "request_id": result.get("request_id", ""),
            "question": result.get("question", "未命名分析"),
            "result": result,
            "created_at": datetime.now().strftime("%H:%M"),
        },
    )
    st.session_state["run_history"] = history[:6]
    st.session_state["last_result"] = result


if "question_input" not in st.session_state:
    st.session_state["question_input"] = EXAMPLES["地区趋势"]
if "run_history" not in st.session_state:
    st.session_state["run_history"] = []

health = get_health()
is_online = health.get("status") == "ok" and health.get("database") == "ok"

with st.sidebar:
    st.markdown(
        """
        <div class="ia-brand"><div class="ia-mark">IA</div><div>
        <div class="ia-brand-name">InsightAgent</div>
        <div class="ia-brand-meta">数据分析工作台</div></div></div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("新建分析", icon=":material/add:", type="primary", width="stretch"):
        st.session_state["last_result"] = None
        st.session_state["question_input"] = ""
        st.session_state["quick_select"] = None
        st.rerun()

    st.markdown('<div class="ia-section-label">最近任务</div>', unsafe_allow_html=True)
    history = st.session_state.get("run_history", [])
    if history:
        for index, item in enumerate(history):
            label = item["question"] if len(item["question"]) <= 24 else f'{item["question"][:23]}…'
            if st.button(
                label, key=f'history_{item["request_id"]}_{index}', icon=":material/history:",
                help=item["question"], width="stretch",
            ):
                st.session_state["last_result"] = item["result"]
                st.rerun()
    else:
        st.caption("暂无历史任务")

    st.markdown('<div class="ia-section-label">系统状态</div>', unsafe_allow_html=True)
    api_ok = health.get("status") == "ok"
    db_ok = health.get("database") == "ok"
    key_ok = health.get("openai_key_configured", False)
    st.markdown(
        f"""
        <div class="ia-status-list">
        <div class="ia-status-row"><span>分析服务</span><span class="ia-status-value"><i class="ia-dot {'ok' if api_ok else 'bad'}"></i>{'正常' if api_ok else '离线'}</span></div>
        <div class="ia-status-row"><span>数据连接</span><span class="ia-status-value"><i class="ia-dot {'ok' if db_ok else 'bad'}"></i>{'正常' if db_ok else '异常'}</span></div>
        <div class="ia-status-row"><span>模型访问</span><span class="ia-status-value"><i class="ia-dot {'ok' if key_ok else 'bad'}"></i>{'就绪' if key_ok else '缺失'}</span></div>
        <div class="ia-status-row"><span>当前模型</span><span class="ia-status-value">{html.escape(str(health.get('model', '未知')))}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

status_text = "服务在线" if is_online else "服务异常"
status_class = "ok" if is_online else "bad"
st.markdown(
    f"""
    <div class="ia-header"><div><div class="ia-eyebrow">自主分析</div>
    <div class="ia-title">业务数据分析</div>
    <div class="ia-subtitle">从问题到 SQL、证据与结论</div></div>
    <div class="ia-live"><i class="ia-dot {status_class}"></i>{status_text}</div></div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="ia-prompt-label">快捷问题</div>', unsafe_allow_html=True)
quick_select = st.pills(
    "快捷问题", options=list(EXAMPLES), selection_mode="single",
    label_visibility="collapsed", key="quick_select",
)
if quick_select and quick_select != st.session_state.get("applied_quick_select"):
    st.session_state["question_input"] = EXAMPLES[quick_select]
    st.session_state["applied_quick_select"] = quick_select

with st.form("analysis_form", clear_on_submit=False, border=True):
    question = st.text_area(
        "业务问题", key="question_input", height=96,
        placeholder="输入需要分析的业务问题", label_visibility="collapsed",
    )
    submitted = st.form_submit_button(
        "开始分析", type="primary", icon=":material/play_arrow:",
        width="stretch", disabled=not is_online,
    )

if submitted:
    cleaned_question = question.strip()
    if len(cleaned_question) < 5:
        st.warning("业务问题至少需要 5 个字符。", icon=":material/warning:")
    else:
        with st.status("正在执行分析工作流", expanded=True) as status:
            st.write("正在生成查询并核验证据…")
            try:
                new_result = run_analysis(cleaned_question)
                remember_result(new_result)
                status.update(label="分析完成", state="complete", expanded=False)
            except (requests.RequestException, RuntimeError) as exc:
                status.update(label="分析失败", state="error", expanded=True)
                st.error(str(exc), icon=":material/error:")

result = st.session_state.get("last_result")
if not result:
    st.markdown(
        """
        <div class="ia-empty"><div class="ia-empty-title">暂无分析结果</div>
        <div class="ia-empty-meta">选择快捷问题或输入新的业务问题</div></div>
        """,
        unsafe_allow_html=True,
    )
else:
    review = result.get("review", {})
    approved = review.get("approved", False)
    confidence = float(review.get("confidence", 0) or 0)
    rows = result.get("rows", [])
    request_id = result.get("request_id", "")
    st.markdown(
        f'<div class="ia-result-head"><div class="ia-result-title">分析结果</div>'
        f'<div class="ia-request-id">{html.escape(request_id)}</div></div>',
        unsafe_allow_html=True,
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("SQL 尝试", result.get("attempts", 0))
    metric_columns[1].metric("证据行数", len(rows))
    metric_columns[2].metric("质量复核", "通过" if approved else "需复核")
    metric_columns[3].metric("置信度", f"{confidence:.0%}")

    report_tab, evidence_tab, trace_tab, review_tab = st.tabs(
        ["分析报告", "数据证据", "执行过程", "质量审查"]
    )
    with report_tab:
        report_column, finding_column = st.columns([1.7, 1], gap="large")
        with report_column:
            st.markdown('<div class="ia-section-title">分析结论</div>', unsafe_allow_html=True)
            st.markdown(result.get("report", "暂无报告。"))
        with finding_column:
            analysis = result.get("analysis", {})
            st.markdown('<div class="ia-section-title">关键发现</div>', unsafe_allow_html=True)
            render_findings(analysis.get("findings", []))
            caveats = analysis.get("caveats", [])
            if caveats:
                st.markdown('<div class="ia-section-title" style="margin-top:1rem">限制条件</div>', unsafe_allow_html=True)
                render_findings(caveats)
        render_chart(rows, result.get("analysis", {}).get("chart"))

    with evidence_tab:
        evidence_head, evidence_action = st.columns([1, 0.32], vertical_alignment="center")
        with evidence_head:
            st.markdown('<div class="ia-section-title">查询证据</div>', unsafe_allow_html=True)
        with evidence_action:
            if rows:
                csv_data = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "导出 CSV", data=csv_data, file_name="insight-agent-evidence.csv",
                    mime="text/csv", icon=":material/download:", width="stretch",
                )
        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        else:
            st.info("本次分析没有返回证据行。")
        with st.expander("查看生成的 SQL", icon=":material/code:"):
            st.code(result.get("sql") or "-- 未生成 SQL", language="sql")
            if result.get("sql_explanation"):
                st.caption(result["sql_explanation"])

    with trace_tab:
        plan = result.get("plan", {})
        plan_column, timeline_column = st.columns([0.9, 1.4], gap="large")
        with plan_column:
            st.markdown('<div class="ia-section-title">分析计划</div>', unsafe_allow_html=True)
            st.markdown(f"**目标**  {plan.get('objective', '未提供')}")
            for index, step in enumerate(plan.get("steps", []), start=1):
                st.markdown(f"{index}. {step}")
            metrics = plan.get("required_metrics", [])
            if metrics:
                st.markdown("**所需指标**")
                st.caption(" · ".join(metrics))
        with timeline_column:
            st.markdown('<div class="ia-section-title">执行轨迹</div>', unsafe_allow_html=True)
            render_trace(result.get("trace", []))

    with review_tab:
        banner_class = "" if approved else " rejected"
        banner_title = "质量审查通过" if approved else "需要人工复核"
        st.markdown(
            f'<div class="ia-review-banner{banner_class}"><div class="ia-review-main">{banner_title}</div>'
            f'<div class="ia-review-score">{confidence:.0%}</div></div>',
            unsafe_allow_html=True,
        )
        st.progress(confidence, text="Reviewer 置信度")
        issues = review.get("issues", [])
        if issues:
            st.markdown('<div class="ia-section-title">发现的问题</div>', unsafe_allow_html=True)
            render_findings(issues)
        else:
            st.success("未发现关键证据问题。", icon=":material/verified:")
        if review.get("retry_instruction"):
            st.markdown('<div class="ia-section-title">修复建议</div>', unsafe_allow_html=True)
            st.write(review["retry_instruction"])
        with st.expander("查看结构化审查数据", icon=":material/data_object:"):
            st.code(json.dumps(review, ensure_ascii=False, indent=2), language="json")
