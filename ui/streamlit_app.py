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
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #858a90; font-size: 0.68rem; margin: -0.42rem 0 0.42rem 2rem;
    }
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
        display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: end;
        margin: 1.65rem 0 0.85rem; padding: 0 0 0.9rem;
        border-bottom: 1px solid var(--line);
    }
    .ia-result-kicker { color: var(--green); font-size: 0.72rem; font-weight: 760; margin-bottom: 0.25rem; }
    .ia-result-title { font-size: 1.15rem; line-height: 1.45; font-weight: 740; max-width: 920px; }
    .ia-result-meta { color: #7b8085; font-size: 0.72rem; margin-top: 0.35rem; }
    .ia-request-id { color: #858a90; font-family: monospace; font-size: 0.7rem; white-space: nowrap; }
    .ia-followup {
        margin: 0.8rem 0 0.55rem; padding: 0.8rem 0.95rem;
        border-left: 3px solid var(--green); background: var(--green-soft);
        color: #315b50; font-size: 0.8rem;
    }
    .ia-stage-label { margin: 1rem 0 0.5rem; color: #62676c; font-size: 0.74rem; font-weight: 720; }
    .ia-stage-strip {
        display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 0.35rem;
        margin-bottom: 0.9rem;
    }
    .ia-stage {
        min-width: 0; padding: 0.55rem 0.52rem; border: 1px solid var(--line);
        border-radius: 4px; background: var(--panel);
    }
    .ia-stage.ok { border-color: #b9d8cc; background: #f4faf7; }
    .ia-stage.retry { border-color: #e5c58f; background: #fff9ef; }
    .ia-stage.failed { border-color: #e4b8b2; background: var(--red-soft); }
    .ia-stage-top { display: flex; align-items: center; gap: 0.35rem; min-width: 0; }
    .ia-stage-index {
        width: 18px; height: 18px; flex: 0 0 18px; display: grid; place-items: center;
        border-radius: 50%; background: #a5aaae; color: #fff; font-size: 0.62rem; font-weight: 760;
    }
    .ia-stage.ok .ia-stage-index { background: var(--green); }
    .ia-stage.retry .ia-stage-index { background: var(--amber); }
    .ia-stage.failed .ia-stage-index { background: var(--red); }
    .ia-stage-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.72rem; font-weight: 720; }
    .ia-stage-time { margin: 0.28rem 0 0 1.45rem; color: #858a90; font-size: 0.64rem; }
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
    .ia-trace-node {
        display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
        color: var(--ink); font-size: 0.82rem; font-weight: 720;
    }
    .ia-trace-duration {
        color: #777c82; background: #eceeef; border-radius: 4px;
        padding: 0.12rem 0.32rem; font-family: monospace; font-size: 0.68rem; font-weight: 650;
    }
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
        margin-top: 1.25rem; padding: 2.2rem 1rem 1.4rem; text-align: center;
        border-top: 1px solid var(--line); color: var(--muted);
    }
    .ia-empty-title { color: #474b50; font-weight: 700; font-size: 0.92rem; }
    .ia-empty-meta { margin-top: 0.35rem; font-size: 0.78rem; }
    .ia-empty-flow {
        max-width: 760px; margin: 1.45rem auto 0; display: grid;
        grid-template-columns: repeat(4, 1fr); gap: 0.5rem;
    }
    .ia-empty-step { padding: 0.65rem 0.5rem; border-top: 2px solid #cdd2d5; text-align: left; }
    .ia-empty-step strong { display: block; color: #44494e; font-size: 0.78rem; }
    .ia-empty-step span { display: block; color: #858a90; font-size: 0.68rem; margin-top: 0.2rem; }

    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
    [data-testid="stCode"] { border-radius: 6px; }
    [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 6px; background: var(--panel); }
    [data-testid="stPlotlyChart"] { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }

    @media (max-width: 800px) {
        .block-container { padding: 1rem 0.85rem 2rem; }
        .ia-header { grid-template-columns: 1fr; align-items: start; }
        .ia-title { font-size: 1.35rem; }
        .ia-result-head { grid-template-columns: 1fr; align-items: start; }
        .ia-stage-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .ia-empty-flow { grid-template-columns: repeat(2, 1fr); }
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


def format_duration(duration_ms: float) -> str:
    if duration_ms < 1000:
        return f"{duration_ms:.0f} ms"
    return f"{duration_ms / 1000:.1f} s"


def render_trace(trace: list[dict[str, Any]]) -> None:
    if not trace:
        st.info("本次运行没有执行轨迹。")
        return
    rows = []
    for event in trace:
        status = event.get("status", "ok")
        css_status = status if status in {"retry", "failed"} else "ok"
        node = NODE_LABELS.get(event.get("node", ""), event.get("node", "未知节点"))
        duration = format_duration(float(event.get("duration_ms", 0) or 0))
        rows.append(
            f'<div class="ia-trace-row {css_status}">'
            f'<div class="ia-trace-node"><span>{html.escape(node)}</span>'
            f'<span class="ia-trace-duration">{duration}</span></div>'
            f'<div class="ia-trace-detail">{html.escape(event.get("detail", ""))}</div></div>'
        )
    st.markdown(f'<div class="ia-timeline">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_stage_overview(trace: list[dict[str, Any]]) -> None:
    events_by_node: dict[str, list[dict[str, Any]]] = {}
    for event in trace:
        events_by_node.setdefault(event.get("node", ""), []).append(event)

    stages = []
    for index, node in enumerate(NODE_LABELS, start=1):
        if node == "failure":
            continue
        events = events_by_node.get(node, [])
        statuses = {event.get("status", "ok") for event in events}
        if "failed" in statuses:
            css_status = "failed"
        elif "retry" in statuses or len(events) > 1:
            css_status = "retry"
        elif events:
            css_status = "ok"
        else:
            css_status = "pending"
        duration_ms = sum(float(event.get("duration_ms", 0) or 0) for event in events)
        duration = format_duration(duration_ms) if events else "等待"
        stages.append(
            f'<div class="ia-stage {css_status}" title="{html.escape(NODE_LABELS[node])}">'
            f'<div class="ia-stage-top"><span class="ia-stage-index">{index}</span>'
            f'<span class="ia-stage-name">{html.escape(NODE_LABELS[node])}</span></div>'
            f'<div class="ia-stage-time">{html.escape(duration)}</div></div>'
        )
    st.markdown(
        '<div class="ia-stage-label">工作流阶段</div>'
        f'<div class="ia-stage-strip">{"".join(stages)}</div>',
        unsafe_allow_html=True,
    )


def render_findings(items: list[str]) -> None:
    if items:
        content = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        st.markdown(f'<ul class="ia-findings">{content}</ul>', unsafe_allow_html=True)


def run_analysis_with_context(
    question: str,
    parent_request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"question": question}
    if parent_request_id:
        payload["parent_request_id"] = parent_request_id
    response = requests.post(
        f"{API_BASE_URL}/api/v1/analyze", json=payload, timeout=600
    )
    if not response.ok:
        try:
            detail = response.json().get("detail", "分析服务返回错误。")
        except ValueError:
            detail = "分析服务返回错误。"
        raise RuntimeError(detail)
    return response.json()


@st.cache_data(ttl=5, show_spinner=False)
def get_run_history() -> list[dict[str, Any]]:
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/runs", params={"limit": 20}, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def get_run_result(request_id: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}/api/v1/runs/{request_id}", timeout=10)
    response.raise_for_status()
    return response.json()


def format_run_time(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        return ""


def build_markdown_report(result: dict[str, Any]) -> str:
    sql = result.get("sql") or "-- 未生成 SQL"
    return (
        f"# InsightAgent 分析报告\n\n"
        f"**问题：** {result.get('question', '')}\n\n"
        f"**请求 ID：** `{result.get('request_id', '')}`\n\n"
        f"{result.get('report', '')}\n\n"
        f"## 查询 SQL\n\n```sql\n{sql}\n```\n"
    )


def remember_result(result: dict[str, Any]) -> None:
    st.session_state["last_result"] = result
    get_run_history.clear()


if "question_input" not in st.session_state:
    st.session_state["question_input"] = EXAMPLES["地区趋势"]
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

    all_history = get_run_history()
    st.markdown(
        f'<div class="ia-section-label">最近任务 · {len(all_history)}</div>',
        unsafe_allow_html=True,
    )
    history_query = st.text_input(
        "搜索历史任务", placeholder="搜索问题", label_visibility="collapsed",
        key="history_query",
    )
    history_filter = st.segmented_control(
        "任务状态", options=["全部", "通过", "需复核"], default="全部",
        label_visibility="collapsed", key="history_filter",
    )
    history = all_history
    if history_query.strip():
        query = history_query.strip().lower()
        history = [item for item in history if query in item.get("question", "").lower()]
    if history_filter == "通过":
        history = [item for item in history if item.get("approved") is True]
    elif history_filter == "需复核":
        history = [item for item in history if item.get("approved") is not True]

    if history:
        for index, item in enumerate(history[:8]):
            label = item["question"] if len(item["question"]) <= 24 else f'{item["question"][:23]}…'
            status = item.get("status")
            if status == "completed":
                time_label = format_run_time(item.get("created_at"))
                duration_label = format_duration(float(item.get("total_duration_ms") or 0))
                approved_label = "已通过" if item.get("approved") else "需复核"
                item_icon = ":material/check_circle:" if item.get("approved") else ":material/warning:"
                if st.button(
                    label, key=f'history_{item["request_id"]}_{index}', icon=item_icon,
                    help=f"{time_label} · {item['question']}", width="stretch",
                ):
                    try:
                        st.session_state["last_result"] = get_run_result(item["request_id"])
                        st.rerun()
                    except requests.RequestException:
                        st.error("历史任务读取失败。")
                st.caption(f"{time_label} · {duration_label} · {approved_label}")
            else:
                state_label = "执行中" if status == "running" else "失败"
                st.caption(f"{state_label} · {label}")
    else:
        st.caption("没有匹配的历史任务")

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
                new_result = run_analysis_with_context(cleaned_question)
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
        <div class="ia-empty-meta">选择快捷问题或输入新的业务问题</div>
        <div class="ia-empty-flow">
        <div class="ia-empty-step"><strong>1 · 规划</strong><span>拆解业务问题</span></div>
        <div class="ia-empty-step"><strong>2 · 查询</strong><span>生成并校验 SQL</span></div>
        <div class="ia-empty-step"><strong>3 · 分析</strong><span>从证据提取结论</span></div>
        <div class="ia-empty-step"><strong>4 · 复核</strong><span>Reviewer 独立检查</span></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )
else:
    review = result.get("review", {})
    approved = review.get("approved", False)
    confidence = float(review.get("confidence", 0) or 0)
    rows = result.get("rows", [])
    request_id = result.get("request_id", "")
    run_summary = next(
        (item for item in all_history if item.get("request_id") == request_id),
        {},
    )
    created_at = format_run_time(run_summary.get("created_at"))
    model_name = run_summary.get("model") or health.get("model", "未知模型")
    meta_parts = [part for part in [created_at, str(model_name), f"ID {request_id[:8]}"] if part]
    st.markdown(
        '<div class="ia-result-head"><div>'
        '<div class="ia-result-kicker">分析结果</div>'
        f'<div class="ia-result-title">{html.escape(result.get("question", "未命名分析"))}</div>'
        f'<div class="ia-result-meta">{html.escape(" · ".join(meta_parts))}</div></div>'
        f'<div class="ia-request-id" title="{html.escape(request_id)}">{html.escape(request_id[:8])}</div></div>',
        unsafe_allow_html=True,
    )
    metric_columns = st.columns(5)
    metric_columns[0].metric("SQL 尝试", result.get("attempts", 0))
    metric_columns[1].metric("证据行数", len(rows))
    metric_columns[2].metric("质量复核", "通过" if approved else "需复核")
    metric_columns[3].metric("置信度", f"{confidence:.0%}")
    metric_columns[4].metric(
        "端到端耗时", format_duration(float(result.get("total_duration_ms", 0) or 0))
    )
    render_stage_overview(result.get("trace", []))

    if result.get("parent_request_id"):
        lineage_info, lineage_action = st.columns([1, 0.2], vertical_alignment="center")
        with lineage_info:
            st.markdown(
                '<div class="ia-followup">本次分析基于上一轮结果继续追问，'
                'Planner 和 SQL Generator 已获得受控历史上下文。</div>',
                unsafe_allow_html=True,
            )
        with lineage_action:
            if st.button(
                "上一轮", icon=":material/arrow_back:", width="stretch",
                key=f"open_parent_{request_id}", help="打开本次追问的父任务",
            ):
                try:
                    st.session_state["last_result"] = get_run_result(result["parent_request_id"])
                    st.rerun()
                except requests.RequestException:
                    st.error("上一轮任务读取失败。")

    with st.expander("基于本次结果继续追问", icon=":material/forum:"):
        with st.form(f"follow_up_form_{request_id}", border=False):
            follow_up_question = st.text_area(
                "追问内容",
                placeholder="例如：进一步拆分贡献最高渠道的地区表现",
                key=f"follow_up_question_{request_id}",
            )
            follow_up_submitted = st.form_submit_button(
                "继续分析", type="primary", icon=":material/arrow_forward:", width="stretch"
            )
        if follow_up_submitted:
            cleaned_follow_up = follow_up_question.strip()
            if len(cleaned_follow_up) < 5:
                st.warning("追问内容至少需要 5 个字符。")
            else:
                with st.status("正在结合上一轮证据继续分析", expanded=True) as status:
                    try:
                        follow_up_result = run_analysis_with_context(
                            cleaned_follow_up,
                            parent_request_id=request_id,
                        )
                        remember_result(follow_up_result)
                        status.update(label="追问分析完成", state="complete", expanded=False)
                        st.rerun()
                    except (requests.RequestException, RuntimeError) as exc:
                        status.update(label="追问分析失败", state="error", expanded=True)
                        st.error(str(exc), icon=":material/error:")

    report_tab, evidence_tab, trace_tab, review_tab = st.tabs(
        ["分析报告", "数据证据", "执行过程", "质量审查"]
    )
    with report_tab:
        report_column, finding_column = st.columns([1.7, 1], gap="large")
        with report_column:
            report_title, report_action = st.columns([1, 0.42], vertical_alignment="center")
            with report_title:
                st.markdown('<div class="ia-section-title">分析结论</div>', unsafe_allow_html=True)
            with report_action:
                st.download_button(
                    "导出报告",
                    data=build_markdown_report(result).encode("utf-8"),
                    file_name=f"insight-agent-{request_id[:8]}.md",
                    mime="text/markdown",
                    icon=":material/download:",
                    width="stretch",
                )
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
            trace = result.get("trace", [])
            render_trace(trace)
            timed_events = [event for event in trace if event.get("duration_ms") is not None]
            if timed_events:
                slowest = max(timed_events, key=lambda event: float(event.get("duration_ms", 0)))
                slowest_label = NODE_LABELS.get(slowest.get("node", ""), slowest.get("node", "未知节点"))
                st.caption(
                    f"最耗时节点：{slowest_label} · "
                    f"{format_duration(float(slowest.get('duration_ms', 0) or 0))}"
                )

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
