"""Tests for semicolon-delimited CSV loading and persisted row-count checks."""

from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

import scripts.load_data as load_data


def configure_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    uploaded_rows: int = 2,
    persisted_rows: int = 2,
) -> tuple[Path, Mock, Mock, Mock]:
    """Install a local CSV and fake Snowflake upload connection."""
    settings = {
        "SNOWFLAKE_ACCOUNT": "account",
        "SNOWFLAKE_USER": "user",
        "SNOWFLAKE_PASSWORD": "password",
        "SNOWFLAKE_WAREHOUSE": "DATAMIND_WH",
        "SNOWFLAKE_DATABASE": "DATAMIND_DB",
        "SNOWFLAKE_SCHEMA": "PUBLIC_DATA",
        "SNOWFLAKE_LOAD_ROLE": "DATAMIND_LOADER",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(load_data, "load_dotenv", Mock())

    csv_path = tmp_path / "bank.csv"
    csv_path.write_text("age;job\n30;admin.\n40;technician\n", encoding="utf-8")
    cursor = Mock()
    cursor.fetchone.return_value = (persisted_rows,)
    connection = Mock()
    connection.cursor.return_value = cursor
    connect = Mock(return_value=connection)
    write_pandas = Mock(return_value=(True, 1, uploaded_rows, []))
    monkeypatch.setattr(load_data.snowflake.connector, "connect", connect)
    monkeypatch.setattr(load_data, "write_pandas", write_pandas)
    return csv_path, connect, write_pandas, cursor


def test_load_csv_uses_semicolon_and_verifies_uploaded_row_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load every CSV row with the loader role and verify persisted table count."""
    csv_path, connect, write_pandas, cursor = configure_loader(
        monkeypatch, tmp_path
    )
    original_read_csv = pd.read_csv
    observed_delimiters: list[str] = []

    def read_csv(path: Path, **kwargs: object) -> pd.DataFrame:
        observed_delimiters.append(str(kwargs["sep"]))
        return original_read_csv(path, **kwargs)

    monkeypatch.setattr(load_data.pd, "read_csv", read_csv)

    assert load_data.load_csv(csv_path, "BANK_MARKETING") == 2

    assert observed_delimiters == [";"]
    assert connect.call_args.kwargs["role"] == "DATAMIND_LOADER"
    write_pandas.assert_called_once()
    assert write_pandas.call_args.args[1].shape == (2, 2)
    cursor.execute.assert_called_once_with(
        "SELECT COUNT(*) FROM BANK_MARKETING"
    )


def test_load_csv_rejects_mismatched_persisted_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not report a successful load when Snowflake persisted fewer rows."""
    csv_path, _, _, _ = configure_loader(
        monkeypatch,
        tmp_path,
        persisted_rows=1,
    )

    with pytest.raises(RuntimeError, match="Snowflake contains 1 rows"):
        load_data.load_csv(csv_path, "BANK_MARKETING")


def test_load_csv_rejects_mismatched_upload_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not continue when the connector reports an incomplete upload."""
    csv_path, _, _, cursor = configure_loader(
        monkeypatch,
        tmp_path,
        uploaded_rows=1,
    )

    with pytest.raises(RuntimeError, match="CSV contains 2"):
        load_data.load_csv(csv_path, "BANK_MARKETING")

    cursor.execute.assert_not_called()
