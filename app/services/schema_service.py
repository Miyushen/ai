from typing import Any

from sqlalchemy import inspect, text

from app.db.base import engine

ALLOWED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
    "refunds",
    "marketing_campaigns",
    "daily_traffic",
    "metric_definitions",
}

DATE_COLUMNS = {
    "daily_traffic": "event_date",
    "orders": "order_date",
    "refunds": "refund_date",
}


def get_business_schema() -> dict[str, Any]:
    inspector = inspect(engine)
    schema: dict[str, Any] = {}
    available = set(inspector.get_table_names())
    for table_name in sorted(ALLOWED_TABLES & available):
        columns = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column.get("nullable", True),
            }
            for column in inspector.get_columns(table_name)
        ]
        foreign_keys = [
            {
                "columns": key.get("constrained_columns", []),
                "references": {
                    "table": key.get("referred_table"),
                    "columns": key.get("referred_columns", []),
                },
            }
            for key in inspector.get_foreign_keys(table_name)
        ]
        schema[table_name] = {"columns": columns, "foreign_keys": foreign_keys}

    dated_tables = sorted(set(DATE_COLUMNS) & available)
    if dated_tables:
        with engine.connect() as connection:
            for table_name in dated_tables:
                column_name = DATE_COLUMNS[table_name]
                start_date, end_date = connection.execute(
                    text(
                        f'SELECT MIN("{column_name}"), MAX("{column_name}") '
                        f'FROM "{table_name}"'
                    )
                ).one()
                schema[table_name]["data_coverage"] = {
                    "date_column": column_name,
                    "min_date": start_date.isoformat() if start_date else None,
                    "max_date": end_date.isoformat() if end_date else None,
                }
            if "metric_definitions" in available:
                metric_rows = connection.execute(
                    text(
                        "SELECT metric_name, formula, description "
                        "FROM metric_definitions ORDER BY metric_name"
                    )
                ).mappings()
                schema["metric_definitions"]["business_metrics"] = [dict(row) for row in metric_rows]
    return schema

