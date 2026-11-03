from typing import Any

from sqlalchemy import inspect

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
    return schema

