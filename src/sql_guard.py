"""Validate model-generated SQL against read-only and dataset-scope rules."""

from __future__ import annotations

import os
from collections.abc import Iterable

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class SQLValidationError(ValueError):
    """Raised when SQL is invalid, unsafe, or outside the dataset scope."""


def validate_read_only_sql(
    sql: str,
    table_allowlist: Iterable[str] | None = None,
    max_limit: int | None = 500,
) -> str:
    """Validate exactly one SELECT, enforce table scope, and cap result rows."""
    if not sql.strip():
        raise SQLValidationError("SQL query must not be empty.")
    if max_limit is not None and max_limit < 1:
        raise ValueError("max_limit must be a positive integer or None.")

    try:
        statements = [
            statement
            for statement in parse(sql, read="snowflake")
            if statement is not None
        ]
    except ParseError as exc:
        raise SQLValidationError(f"Invalid Snowflake SQL: {exc}") from exc

    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed.")
    statement = statements[0]
    if not isinstance(statement, exp.Query) or not statement.find(exp.Select):
        raise SQLValidationError("Only a SELECT or WITH...SELECT query is allowed.")
    if statement.find(exp.Into):
        raise SQLValidationError("SELECT INTO is not allowed.")

    if table_allowlist is not None:
        _validate_tables(statement, table_allowlist)

    if max_limit is not None:
        _apply_limit(statement, max_limit)
    return statement.sql(dialect="snowflake")


def configured_max_limit() -> int:
    """Read the positive SQL row cap from SQL_GUARD_MAX_LIMIT (default 500)."""
    raw_limit = os.getenv("SQL_GUARD_MAX_LIMIT", "500").strip()
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ValueError("SQL_GUARD_MAX_LIMIT must be a positive integer.") from exc
    if limit < 1:
        raise ValueError("SQL_GUARD_MAX_LIMIT must be a positive integer.")
    return limit


def _validate_tables(statement: exp.Query, table_allowlist: Iterable[str]) -> None:
    """Reject table references not explicitly present in the allowlist."""
    allowed = {_normalize_identifier(name) for name in table_allowlist}
    if not allowed:
        raise SQLValidationError("The configured table allowlist is empty.")

    cte_names = {
        cte.alias_or_name.casefold()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }
    for table in statement.find_all(exp.Table):
        if not any((table.catalog, table.db)) and table.name.casefold() in cte_names:
            continue
        qualified_name = ".".join(
            part.casefold()
            for part in (table.catalog, table.db, table.name)
            if part
        )
        if qualified_name not in allowed:
            raise SQLValidationError(
                f"Table '{qualified_name}' is not in the configured dataset allowlist."
            )


def _normalize_identifier(identifier: str) -> str:
    """Normalize a Snowflake identifier for case-insensitive allowlist matching."""
    return ".".join(
        part.strip().strip('"').casefold() for part in identifier.split(".")
    )


def _apply_limit(statement: exp.Query, max_limit: int) -> None:
    """Add LIMIT or reduce a larger/non-literal LIMIT to the configured cap."""
    limit_node = statement.args.get("limit")
    if limit_node is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
        return

    limit_value = limit_node.args.get("expression")
    if not isinstance(limit_value, exp.Literal) or not limit_value.is_int:
        limit_node.set("expression", exp.Literal.number(max_limit))
        return

    if int(limit_value.this) > max_limit:
        limit_node.set("expression", exp.Literal.number(max_limit))
