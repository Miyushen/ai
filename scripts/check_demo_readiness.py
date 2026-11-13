import json
import os
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).parents[1]
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
UI_URL = os.getenv("UI_URL", "http://localhost:8501")


def check_http_json(url: str, timeout: int = 10) -> tuple[bool, Any]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return True, response.json()
    except (requests.RequestException, ValueError) as exc:
        return False, type(exc).__name__


def build_report() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    health_ok, health = check_http_json(f"{API_BASE_URL}/api/v1/health")
    checks.append(
        {
            "name": "API 与数据库",
            "passed": health_ok
            and health.get("status") == "ok"
            and health.get("database") == "ok",
            "detail": health,
        }
    )
    checks.append(
        {
            "name": "模型密钥",
            "passed": health_ok and bool(health.get("openai_key_configured")),
            "detail": health.get("model") if health_ok else health,
        }
    )

    try:
        ui_response = requests.get(UI_URL, timeout=10)
        ui_passed = ui_response.status_code == 200
        ui_detail: Any = ui_response.status_code
    except requests.RequestException as exc:
        ui_passed = False
        ui_detail = type(exc).__name__
    checks.append({"name": "Streamlit 前端", "passed": ui_passed, "detail": ui_detail})

    runs_ok, runs = check_http_json(f"{API_BASE_URL}/api/v1/runs?limit=100")
    approved_runs = (
        [run for run in runs if run.get("status") == "completed" and run.get("approved")]
        if runs_ok and isinstance(runs, list)
        else []
    )
    checks.append(
        {
            "name": "历史结果回放",
            "passed": bool(approved_runs),
            "detail": f"{len(approved_runs)} 个已通过任务",
        }
    )

    eval_path = PROJECT_ROOT / "artifacts" / "eval-results.json"
    eval_summary = {}
    if eval_path.exists():
        try:
            eval_summary = json.loads(eval_path.read_text(encoding="utf-8")).get("summary", {})
        except (ValueError, OSError):
            pass
    checks.append(
        {
            "name": "15 题黄金评测",
            "passed": eval_summary.get("total_cases") == 15
            and eval_summary.get("http_success_rate") == 1.0
            and eval_summary.get("review_approval_rate") == 1.0,
            "detail": eval_summary,
        }
    )

    required_files = [
        PROJECT_ROOT / "docs" / "screenshots" / "insight-agent-demo.png",
        PROJECT_ROOT / "docs" / "screenshots" / "insight-agent-trace.png",
        PROJECT_ROOT / "docs" / "screenshots" / "insight-agent-mobile.png",
        PROJECT_ROOT / "presentation" / "InsightAgent-项目演示与答辩.pptx",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required_files if not path.exists()]
    checks.append(
        {
            "name": "离线演示材料",
            "passed": not missing,
            "detail": "完整" if not missing else {"missing": missing},
        }
    )

    return {
        "ready": all(check["passed"] for check in checks),
        "checks": checks,
        "fallback_ready": bool(approved_runs) and not missing,
    }


def main() -> None:
    report = build_report()
    output_path = PROJECT_ROOT / "artifacts" / "demo-readiness.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for check in report["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        print(f"[{marker}] {check['name']}: {check['detail']}")
    print(f"Fallback demo ready: {report['fallback_ready']}")
    print(f"Wrote {output_path}")
    raise SystemExit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
