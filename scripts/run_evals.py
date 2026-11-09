import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.sql_executor import execute_read_only
from app.services.sql_guard import validate_and_rewrite_sql

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
QUESTIONS_PATH = PROJECT_ROOT / "evals" / "questions.json"


def collect_node_durations(trace: list[dict]) -> dict[str, float]:
    """Sum repeated node attempts so repair loops remain visible in evaluation output."""
    durations: dict[str, float] = {}
    for event in trace:
        node = event.get("node")
        duration_ms = event.get("duration_ms")
        if not isinstance(node, str) or not isinstance(duration_ms, (int, float)):
            continue
        durations[node] = round(durations.get(node, 0) + float(duration_ms), 2)
    return durations


def _selected_rows(rows: list[dict[str, Any]], indices: list[int]) -> list[dict[str, Any]]:
    selected = []
    for index in indices:
        resolved = index if index >= 0 else len(rows) + index
        if 0 <= resolved < len(rows):
            selected.append(rows[resolved])
    return selected


def _numeric_values(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return [float(value)]
    if isinstance(value, dict):
        return [number for item in value.values() for number in _numeric_values(item)]
    if isinstance(value, list):
        return [number for item in value for number in _numeric_values(item)]
    return []


def _number_present(expected: float, candidates: list[float]) -> bool:
    tolerance = max(0.02, abs(expected) * 1e-7)
    return any(abs(candidate - expected) <= tolerance for candidate in candidates)


def evaluate_golden_result(
    oracle: dict[str, Any],
    oracle_rows: list[dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    selected = _selected_rows(oracle_rows, oracle.get("row_indices", []))
    searchable = json.dumps(
        {
            "report": payload.get("report", ""),
            "analysis": payload.get("analysis", {}),
            "rows": payload.get("rows", []),
        },
        ensure_ascii=False,
        default=str,
    ).lower()

    entity_column = oracle.get("entity_column")
    expected_entities = [
        str(row[entity_column])
        for row in selected
        if entity_column and row.get(entity_column) is not None
    ]
    entity_recall = (
        sum(entity.lower() in searchable for entity in expected_entities) / len(expected_entities)
        if expected_entities
        else None
    )

    numeric_columns = oracle.get("numeric_columns", [])
    expected_numbers = [
        float(row[column])
        for row in selected
        for column in numeric_columns
        if isinstance(row.get(column), (int, float))
    ]
    candidate_numbers = _numeric_values(payload.get("rows", []))
    numeric_recall = (
        sum(_number_present(number, candidate_numbers) for number in expected_numbers)
        / len(expected_numbers)
        if expected_numbers
        else None
    )

    components = [score for score in (entity_recall, numeric_recall) if score is not None]
    return {
        "gold_result_score": statistics.fmean(components) if components else 0.0,
        "gold_entity_recall": entity_recall,
        "gold_numeric_recall": numeric_recall,
        "gold_expected_entities": expected_entities,
        "gold_expected_numeric_count": len(expected_numbers),
    }


def run_oracle(case: dict[str, Any]) -> list[dict[str, Any]]:
    oracle = case["oracle"]
    safe_sql = validate_and_rewrite_sql(oracle["sql"])
    _, rows = execute_read_only(safe_sql)
    return rows


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    results = []
    for case in questions:
        started = time.perf_counter()
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/analyze",
                json={"question": case["question"]},
                timeout=300,
            )
            status_code = response.status_code
            payload = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            request_error = None
        except requests.RequestException as exc:
            status_code = 0
            payload = {}
            request_error = type(exc).__name__
        latency = time.perf_counter() - started
        report = payload.get("report", "")
        terms_found = [term for term in case["expected_terms"] if term.lower() in report.lower()]
        golden = evaluate_golden_result(case["oracle"], run_oracle(case), payload)
        results.append(
            {
                "id": case["id"],
                "status_code": status_code,
                "latency_seconds": round(latency, 2),
                "review_approved": payload.get("review", {}).get("approved", False),
                "expected_term_recall": len(terms_found) / len(case["expected_terms"]),
                "attempts": payload.get("attempts"),
                "agent_duration_seconds": round(payload.get("total_duration_ms", 0) / 1000, 2),
                "node_duration_ms": collect_node_durations(payload.get("trace", [])),
                **golden,
                "error": request_error,
            }
        )
        print(json.dumps(results[-1], ensure_ascii=False))

    output_dir = PROJECT_ROOT / "artifacts"
    output_dir.mkdir(exist_ok=True)
    successful = [result for result in results if result["status_code"] == 200]
    latencies = [result["latency_seconds"] for result in results]
    node_samples: dict[str, list[float]] = {}
    for result in successful:
        for node, duration_ms in result["node_duration_ms"].items():
            node_samples.setdefault(node, []).append(duration_ms)
    summary = {
        "total_cases": len(results),
        "http_success_rate": len(successful) / len(results),
        "review_approval_rate": sum(result["review_approved"] for result in results) / len(results),
        "mean_expected_term_recall": statistics.fmean(
            result["expected_term_recall"] for result in results
        ),
        "mean_gold_result_score": statistics.fmean(
            result["gold_result_score"] for result in results
        ),
        "mean_gold_entity_recall": statistics.fmean(
            result["gold_entity_recall"]
            for result in results
            if result["gold_entity_recall"] is not None
        ),
        "mean_gold_numeric_recall": statistics.fmean(
            result["gold_numeric_recall"]
            for result in results
            if result["gold_numeric_recall"] is not None
        ),
        "median_latency_seconds": round(statistics.median(latencies), 2),
        "max_latency_seconds": round(max(latencies), 2),
        "mean_node_duration_ms": {
            node: round(statistics.fmean(samples), 2)
            for node, samples in sorted(node_samples.items())
        },
    }
    output_path = output_dir / "eval-results.json"
    output_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"summary": summary}, ensure_ascii=False))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

