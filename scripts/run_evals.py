import json
import os
import statistics
import time
from pathlib import Path

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
QUESTIONS_PATH = Path(__file__).parents[1] / "evals" / "questions.json"


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
        results.append(
            {
                "id": case["id"],
                "status_code": status_code,
                "latency_seconds": round(latency, 2),
                "review_approved": payload.get("review", {}).get("approved", False),
                "expected_term_recall": len(terms_found) / len(case["expected_terms"]),
                "attempts": payload.get("attempts"),
                "error": request_error,
            }
        )
        print(json.dumps(results[-1], ensure_ascii=False))

    output_dir = Path(__file__).parents[1] / "artifacts"
    output_dir.mkdir(exist_ok=True)
    successful = [result for result in results if result["status_code"] == 200]
    latencies = [result["latency_seconds"] for result in results]
    summary = {
        "total_cases": len(results),
        "http_success_rate": len(successful) / len(results),
        "review_approval_rate": sum(result["review_approved"] for result in results) / len(results),
        "mean_expected_term_recall": statistics.fmean(
            result["expected_term_recall"] for result in results
        ),
        "median_latency_seconds": round(statistics.median(latencies), 2),
        "max_latency_seconds": round(max(latencies), 2),
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

