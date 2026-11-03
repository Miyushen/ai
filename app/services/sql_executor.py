from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import engine


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def execute_read_only(sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    settings = get_settings()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text(f"SET LOCAL statement_timeout = {settings.sql_timeout_ms}"))
            result = connection.execute(text(sql))
            columns = list(result.keys())
            rows = [
                {key: _json_value(value) for key, value in row.items()}
                for row in result.mappings().fetchmany(settings.max_sql_rows)
            ]
        finally:
            transaction.rollback()
    return columns, rows

