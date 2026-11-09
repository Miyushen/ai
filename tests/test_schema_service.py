from datetime import date
from unittest.mock import MagicMock, patch

from app.services.schema_service import get_business_schema


def test_schema_includes_database_date_coverage() -> None:
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["orders", "metric_definitions"]
    inspector.get_columns.return_value = [
        {"name": "order_date", "type": "DATE", "nullable": False}
    ]
    inspector.get_foreign_keys.return_value = []

    connection = MagicMock()
    coverage_result = MagicMock()
    coverage_result.one.return_value = (date(2026, 5, 5), date(2026, 10, 31))
    metric_result = MagicMock()
    metric_result.mappings.return_value = [
        {
            "metric_name": "revenue",
            "formula": "SUM(item_revenue)",
            "description": "Gross revenue.",
        }
    ]
    connection.execute.side_effect = [coverage_result, metric_result]
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection

    with (
        patch("app.services.schema_service.inspect", return_value=inspector),
        patch("app.services.schema_service.engine.connect", return_value=connection_context),
    ):
        schema = get_business_schema()

    assert schema["orders"]["data_coverage"] == {
        "date_column": "order_date",
        "min_date": "2026-05-05",
        "max_date": "2026-10-31",
    }
    assert schema["metric_definitions"]["business_metrics"][0]["metric_name"] == "revenue"
