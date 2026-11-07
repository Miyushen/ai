from scripts.run_evals import collect_node_durations


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
