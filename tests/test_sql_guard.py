"""Tests for safe SQL parsing, allowlisting, and result caps."""

import pytest
from sqlglot import parse_one

from src.sql_guard import (
    SQLValidationError,
    configured_max_limit,
    validate_read_only_sql,
)


ALLOWLIST = {"BANK_MARKETING"}


@pytest.mark.parametrize(
    "sql",
    (
        "SELECT 1",
        "SELECT age FROM BANK_MARKETING",
        "WITH campaign_data AS (SELECT age FROM BANK_MARKETING) "
        "SELECT age FROM campaign_data",
        "SELECT 1;",
        "SELECT * FROM BANK_MARKETING LIMIT 20",
    ),
)
def test_accepts_one_select(sql: str) -> None:
    """Allow one SELECT, including a CTE and trailing semicolon."""
    validate_read_only_sql(sql, ALLOWLIST)


@pytest.mark.parametrize(
    "sql",
    (
        "",
        "DROP TABLE BANK_MARKETING",
        "INSERT INTO BANK_MARKETING (age) VALUES (1)",
        "UPDATE BANK_MARKETING SET age = 1",
        "DELETE FROM BANK_MARKETING",
        "CREATE TABLE harmless (value INT)",
        "SELECT 1; DELETE FROM BANK_MARKETING",
        "SELECT 1; -- hidden statement follows\nDELETE FROM BANK_MARKETING",
        "SELECT age FROM OTHER_TABLE",
        "WITH campaign_data AS (SELECT age FROM OTHER_TABLE) "
        "SELECT age FROM campaign_data",
        "SELECT * INTO OTHER_TABLE FROM BANK_MARKETING",
    ),
)
def test_rejects_writes_multiple_statements_and_unknown_tables(sql: str) -> None:
    """Reject DDL/DML, hidden second statements, and out-of-scope tables."""
    with pytest.raises(SQLValidationError):
        validate_read_only_sql(sql, ALLOWLIST)


def test_adds_default_limit_when_missing() -> None:
    """Enforce a row cap even when generated SELECT omitted LIMIT."""
    validated = validate_read_only_sql(
        "SELECT age FROM BANK_MARKETING", ALLOWLIST, max_limit=125
    )

    assert parse_one(validated, read="snowflake").args["limit"].expression.this == "125"


def test_caps_limit_and_preserves_smaller_limit() -> None:
    """Reduce excessive and parameterized limits while preserving a smaller cap."""
    capped = validate_read_only_sql(
        "SELECT age FROM BANK_MARKETING LIMIT 1000", ALLOWLIST, max_limit=100
    )
    preserved = validate_read_only_sql(
        "SELECT age FROM BANK_MARKETING LIMIT 10", ALLOWLIST, max_limit=100
    )

    assert parse_one(capped, read="snowflake").args["limit"].expression.this == "100"
    assert parse_one(preserved, read="snowflake").args["limit"].expression.this == "10"


def test_configured_max_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read and validate the environment-configured row cap."""
    monkeypatch.setenv("SQL_GUARD_MAX_LIMIT", "42")
    assert configured_max_limit() == 42

    monkeypatch.setenv("SQL_GUARD_MAX_LIMIT", "0")
    with pytest.raises(ValueError, match="positive integer"):
        configured_max_limit()
