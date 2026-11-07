from unittest.mock import patch

from app.agent.nodes import execute_sql_node


def test_empty_query_results_request_sql_repair() -> None:
    with patch("app.agent.nodes.execute_read_only", return_value=(["category"], [])):
        result = execute_sql_node({"sql": "SELECT category FROM products"})

    assert result["rows"] == []
    assert "no evidence rows" in result["error"]
    assert result["trace"][0]["status"] == "retry"
    assert result["trace"][0]["duration_ms"] >= 0


def test_non_empty_query_results_continue() -> None:
    rows = [{"category": "Electronics"}]
    with patch("app.agent.nodes.execute_read_only", return_value=(["category"], rows)):
        result = execute_sql_node({"sql": "SELECT category FROM products"})

    assert result["rows"] == rows
    assert result["error"] is None
    assert result["trace"][0]["status"] == "ok"
    assert result["trace"][0]["duration_ms"] >= 0
