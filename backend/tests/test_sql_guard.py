"""Tests for safe SQL parsing, allowlisting, and result caps."""

import pytest
from sqlglot import parse_one

from src.sql_guard import (
    SQLValidationError,
    configured_max_limit,
    repair_unconfigured_columns,
    repair_unconfigured_join_paths,
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


def test_accepts_quoted_keyword_like_column_identifiers() -> None:
    """Preserve quoted keyword-like Snowflake columns through SQL validation."""
    validated = validate_read_only_sql(
        'SELECT "DEFAULT", "DAY", "MONTH" FROM BANK_MARKETING',
        ALLOWLIST,
    )

    assert '"DEFAULT"' in validated
    assert '"DAY"' in validated
    assert '"MONTH"' in validated


@pytest.mark.parametrize(
    "sql",
    (
        "SELECT COUNT(*) FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
        'SELECT COUNT(*) FROM "SNOWFLAKE_SAMPLE_DATA"."TPCH_SF1"."CUSTOMER"',
        (
            "SELECT COUNT(*) FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS AS O "
            "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C "
            "ON O.O_CUSTKEY = C.C_CUSTKEY"
        ),
    ),
)
def test_accepts_fully_qualified_configured_tables(sql: str) -> None:
    """Allow exact configured database.schema.table names and joined references."""
    allowlist = {
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS",
    }

    validate_read_only_sql(sql, allowlist)


def test_accepts_only_configured_join_key_pairs() -> None:
    """Allow configured joins in either orientation and reject inferred shortcuts."""
    tables = {
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION",
    }
    joins = [
        (
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
            "C_NATIONKEY",
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION",
            "N_NATIONKEY",
        )
    ]

    validate_read_only_sql(
        "SELECT N.N_NAME FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C "
        "ON N.N_NATIONKEY = C.C_NATIONKEY",
        tables,
        join_allowlist=joins,
    )

    with pytest.raises(SQLValidationError, match="not a configured relationship"):
        validate_read_only_sql(
            "SELECT N.N_NAME FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N "
            "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C "
            "ON N.N_NATIONKEY = C.C_CUSTKEY",
            tables,
            join_allowlist=joins,
        )


def test_repairs_guessed_join_with_configured_shortest_path() -> None:
    """Insert configured intermediate tables for an invalid direct join."""
    joins = [
        (
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION",
            "N_NATIONKEY",
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
            "C_NATIONKEY",
        ),
        (
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS",
            "O_CUSTKEY",
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
            "C_CUSTKEY",
        ),
    ]
    sql = (
        "SELECT N.N_NAME, COUNT(O.O_ORDERKEY) FROM "
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS AS O "
        "ON N.N_NATIONKEY = O.O_CUSTKEY GROUP BY N.N_NAME"
    )

    repaired = repair_unconfigured_join_paths(sql, joins)

    assert "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS _DM_JOIN_1" in repaired
    assert "n.n_nationkey = _dm_join_1.c_nationkey" in repaired.casefold()
    assert "_dm_join_1.c_custkey = o.o_custkey" in repaired.casefold()
    assert "n.n_nationkey = o.o_custkey" not in repaired.casefold()


def test_repairs_unique_column_name_suffix_from_schema() -> None:
    """Map a malformed display-column name to its unique configured suffix."""
    sql = (
        "SELECT R.R_REGIONNAME FROM "
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.REGION AS R "
        "GROUP BY R.R_REGIONNAME"
    )
    columns = {
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.REGION": [
            "R_REGIONKEY",
            "R_NAME",
            "R_COMMENT",
        ]
    }

    repaired = repair_unconfigured_columns(sql, columns)

    assert repaired.count("R.R_NAME") == 2
    assert "R_REGIONNAME" not in repaired


def test_rejects_fully_qualified_table_outside_configured_schema() -> None:
    """Do not permit a same-named table in another database or schema."""
    with pytest.raises(SQLValidationError, match="not in the configured"):
        validate_read_only_sql(
            "SELECT COUNT(*) FROM OTHER_SAMPLE_DATA.TPCH_SF1.CUSTOMER",
            {"SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER"},
        )


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


def test_scalar_aggregate_does_not_get_a_misleading_row_limit() -> None:
    """Keep result caps from implying that aggregate input rows were capped."""
    validated = validate_read_only_sql(
        "SELECT AVG(balance) FROM BANK_MARKETING LIMIT 500",
        ALLOWLIST,
        max_limit=500,
    )

    assert parse_one(validated, read="snowflake").args.get("limit") is None


def test_grouped_aggregate_keeps_result_row_limit() -> None:
    """Retain the result cap when an aggregate can return multiple groups."""
    validated = validate_read_only_sql(
        "SELECT job, COUNT(*) FROM BANK_MARKETING GROUP BY job",
        ALLOWLIST,
        max_limit=125,
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
