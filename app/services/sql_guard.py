from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from app.services.schema_service import ALLOWED_TABLES


@dataclass
class SqlValidationError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


BLOCKED_EXPRESSIONS = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Merge,
    exp.Transaction,
    exp.Update,
)


def validate_and_rewrite_sql(sql: str, max_rows: int = 200) -> str:
    if not sql or not sql.strip():
        raise SqlValidationError("The model returned an empty SQL query.")

    try:
        statements = parse(sql, read="postgres")
    except ParseError as exc:
        raise SqlValidationError(f"SQL parsing failed: {exc}") from exc

    if len(statements) != 1:
        raise SqlValidationError("Exactly one SQL statement is allowed.")

    expression = statements[0]
    if any(expression.find(node_type) for node_type in BLOCKED_EXPRESSIONS):
        raise SqlValidationError("Only read-only SELECT queries are allowed.")
    if not isinstance(expression, exp.Select) and expression.find(exp.Select) is None:
        raise SqlValidationError("The statement must contain a SELECT query.")

    referenced_tables = {table.name.lower() for table in expression.find_all(exp.Table)}
    cte_names = {
        cte.alias_or_name.lower()
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }
    physical_tables = referenced_tables - cte_names
    forbidden_tables = physical_tables - ALLOWED_TABLES
    if forbidden_tables:
        names = ", ".join(sorted(forbidden_tables))
        raise SqlValidationError(f"Query references non-allowlisted tables: {names}.")
    if not physical_tables:
        raise SqlValidationError("Query must reference at least one business table.")

    limit = expression.args.get("limit")
    if limit is None:
        expression = expression.limit(max_rows)
    else:
        limit_value = limit.expression
        if isinstance(limit_value, exp.Literal) and limit_value.is_int:
            if int(limit_value.this) > max_rows:
                expression.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
        else:
            expression.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return expression.sql(dialect="postgres", pretty=True)

