"""Tests for the read-only Snowflake client."""

from unittest.mock import Mock, call

import pytest

from src.snowflake_client import SnowflakeClient, SnowflakeClientError


@pytest.fixture
def connection_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide complete Snowflake settings for client construction."""
    settings = {
        "SNOWFLAKE_ACCOUNT": "account",
        "SNOWFLAKE_USER": "user",
        "SNOWFLAKE_PASSWORD": "password",
        "SNOWFLAKE_ROLE": "DATAMIND_READER",
        "SNOWFLAKE_WAREHOUSE": "DATAMIND_WH",
        "SNOWFLAKE_DATABASE": "DATAMIND_DB",
        "SNOWFLAKE_SCHEMA": "PUBLIC_DATA",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)


def test_run_query_returns_rows_and_metadata(
    connection_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return query results and ensure the connection uses the read-only role."""
    cursor = Mock()
    cursor.description = [("ROW_COUNT",)]
    cursor.fetchall.return_value = [(42,)]
    cursor.sfqid = "query-123"
    connection = Mock()
    connection.cursor.return_value = cursor
    connect = Mock(return_value=connection)
    monkeypatch.setattr("src.snowflake_client.snowflake.connector.connect", connect)

    with SnowflakeClient() as client:
        result = client.run_query("SELECT COUNT(*) AS ROW_COUNT FROM BANK_MARKETING")

    assert result["columns"] == ["ROW_COUNT"]
    assert result["rows"] == [(42,)]
    assert result["query_id"] == "query-123"
    assert result["row_count"] == 1
    assert result["elapsed_ms"] >= 0
    assert connect.call_args.kwargs["role"] == "DATAMIND_READER"
    assert cursor.execute.call_args_list == [
        call("USE SECONDARY ROLES NONE"),
        call("SELECT COUNT(*) AS ROW_COUNT FROM BANK_MARKETING"),
    ]
    connection.close.assert_called_once()
    assert cursor.close.call_count == 2


def test_rejects_other_configured_role(
    connection_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not allow the client to connect with a role other than the reader."""
    monkeypatch.setenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    with pytest.raises(SnowflakeClientError, match="DATAMIND_READER"):
        SnowflakeClient()
