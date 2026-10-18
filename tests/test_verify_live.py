"""Unit tests for live verification configuration and result contracts."""

import pytest

from scripts.verify_live import (
    _check_environment,
    _connect_reader,
    _require_pipeline_result,
    _safe_exception_message,
)
from src.pipeline import AnswerResult


@pytest.fixture
def live_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure the non-secret values needed for verifier environment checks."""
    settings = {
        "SNOWFLAKE_ACCOUNT": "account",
        "SNOWFLAKE_USER": "user",
        "SNOWFLAKE_PASSWORD": "test-password",
        "SNOWFLAKE_ROLE": "DATAMIND_READER",
        "SNOWFLAKE_WAREHOUSE": "DATAMIND_WH",
        "SNOWFLAKE_DATABASE": "DATAMIND_DB",
        "SNOWFLAKE_SCHEMA": "PUBLIC_DATA",
        "SNOWFLAKE_LOAD_ROLE": "DATAMIND_LOADER",
        "GEMMA_BACKEND": "ollama",
        "GEMMA_MODEL": "gemma3:4b",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)


def test_check_environment_accepts_required_reader_and_loader_roles(
    live_environment: None,
) -> None:
    """Accept the documented Snowflake roles without returning their values."""
    assert _check_environment() == [
        "Required Snowflake roles and Gemma settings are configured."
    ]


def test_check_environment_requires_api_settings_without_printing_values(
    live_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report missing API setting names without exposing configured secrets."""
    monkeypatch.setenv("GEMMA_BACKEND", "api")
    monkeypatch.setenv("GEMMA_API_KEY", "sensitive-api-key")
    monkeypatch.delenv("GEMMA_API_BASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="GEMMA_API_BASE_URL") as exc_info:
        _check_environment()

    assert "sensitive-api-key" not in str(exc_info.value)


def test_exception_output_redacts_configured_secret_values(
    live_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redact passwords and API keys from backend exception text."""
    monkeypatch.setenv("GEMMA_API_KEY", "sensitive-api-key")
    error = RuntimeError("failed with test-password and sensitive-api-key")

    output = _safe_exception_message(error)

    assert "test-password" not in output
    assert "sensitive-api-key" not in output
    assert output.count("[REDACTED]") == 2


def test_read_only_probe_disables_secondary_roles(
    live_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Probe the primary reader role without inherited user secondary roles."""
    from unittest.mock import Mock

    from scripts import verify_live

    cursor = Mock()
    connection = Mock()
    connection.cursor.return_value = cursor
    connect = Mock(return_value=connection)
    monkeypatch.setattr(verify_live.snowflake.connector, "connect", connect)

    assert _connect_reader() is connection

    assert connect.call_args.kwargs["role"] == "DATAMIND_READER"
    cursor.execute.assert_called_once_with("USE SECONDARY ROLES NONE")
    cursor.close.assert_called_once()


def test_pipeline_result_contract_detects_unexpected_empty_rows() -> None:
    """Require the impossible-age edge case to return no rows."""
    result = AnswerResult(
        status="answerable",
        answer="Some clients match.",
        explanation="The query returned rows.",
        sql="SELECT AGE FROM BANK_MARKETING",
        rows=[(30,)],
        query_id="query-id",
    )

    with pytest.raises(RuntimeError, match="instead of an empty result"):
        _require_pipeline_result(
            result,
            "Show rows where age > 200.",
            expected_status="answerable",
            require_empty_rows=True,
        )


def test_pipeline_failure_includes_sql_and_diagnostics() -> None:
    """Show generated SQL and warning details when live behavior is unexpected."""
    result = AnswerResult(
        status="error",
        answer="Could not query.",
        explanation="Only SELECT queries can run.",
        warnings=["SQL compilation error: invalid identifier"],
    )

    with pytest.raises(RuntimeError, match="invalid identifier"):
        _require_pipeline_result(
            result,
            "Show rows where age > 200.",
            expected_status="answerable",
        )
