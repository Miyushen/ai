from scripts.run_evals import collect_node_durations, evaluate_golden_result


def test_collect_node_durations_sums_retries_and_ignores_invalid_events() -> None:
    trace = [
        {"node": "sql_generator", "duration_ms": 120.25},
        {"node": "sql_guard", "duration_ms": 1.5},
        {"node": "sql_generator", "duration_ms": 80.25},
        {"node": "reviewer"},
        {"duration_ms": 5},
    ]

    assert collect_node_durations(trace) == {
        "sql_generator": 200.5,
        "sql_guard": 1.5,
    }


def test_evaluate_golden_result_checks_entities_and_numeric_evidence() -> None:
    oracle = {
        "row_indices": [0, -1],
        "entity_column": "channel",
        "numeric_columns": ["revenue"],
    }
    oracle_rows = [
        {"channel": "Organic", "revenue": 982405.53},
        {"channel": "Marketplace", "revenue": 803951.35},
        {"channel": "Direct", "revenue": 647382.82},
    ]
    payload = {
        "report": "Organic 贡献最高，Direct 最低。",
        "rows": [
            {"source": "Organic", "net_revenue": 982405.53},
            {"source": "Direct", "net_revenue": 647382.82},
        ],
    }

    result = evaluate_golden_result(oracle, oracle_rows, payload)

    assert result["gold_result_score"] == 1.0
    assert result["gold_entity_recall"] == 1.0
    assert result["gold_numeric_recall"] == 1.0


def test_evaluate_golden_result_detects_unsupported_numbers() -> None:
    oracle = {
        "row_indices": [0],
        "entity_column": "region",
        "numeric_columns": ["current_revenue"],
    }
    oracle_rows = [{"region": "North", "current_revenue": 100.0}]
    payload = {"report": "North 下降最明显。", "rows": [{"current_revenue": 80.0}]}

    result = evaluate_golden_result(oracle, oracle_rows, payload)

    assert result["gold_entity_recall"] == 1.0
    assert result["gold_numeric_recall"] == 0.0
    assert result["gold_result_score"] == 0.5
