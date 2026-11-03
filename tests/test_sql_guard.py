import pytest

from app.services.sql_guard import SqlValidationError, validate_and_rewrite_sql


def test_adds_limit_to_safe_select() -> None:
    sql = validate_and_rewrite_sql("SELECT id, region FROM customers", max_rows=50)
    assert "LIMIT 50" in sql


def test_clamps_large_limit() -> None:
    sql = validate_and_rewrite_sql("SELECT id FROM orders LIMIT 5000", max_rows=100)
    assert "LIMIT 100" in sql


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE customers SET region = 'East'",
        "DROP TABLE products",
        "SELECT * FROM customers; SELECT * FROM orders",
        "SELECT * FROM pg_catalog.pg_tables",
    ],
)
def test_rejects_unsafe_sql(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        validate_and_rewrite_sql(sql)


def test_allows_cte_select() -> None:
    sql = validate_and_rewrite_sql(
        "WITH totals AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) "
        "SELECT customer_id, n FROM totals",
        max_rows=25,
    )
    assert "LIMIT 25" in sql

