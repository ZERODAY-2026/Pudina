"""Load the UCI Bank Marketing CSV into a Snowflake table."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas


_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def _required_setting(name: str) -> str:
    """Return a non-empty environment setting or raise a clear error."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment setting: {name}.")
    return value


def load_csv(csv_path: Path, table_name: str, delimiter: str = ";") -> int:
    """Load a delimited CSV into the configured Snowflake database and schema."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")
    if len(delimiter) != 1:
        raise ValueError("Delimiter must be exactly one character.")
    if not _TABLE_NAME.fullmatch(table_name):
        raise ValueError("Table name must be a simple Snowflake identifier.")
    if not csv_path.stat().st_size:
        raise ValueError(f"CSV file is empty: {csv_path}")

    load_dotenv()
    frame = pd.read_csv(csv_path, sep=delimiter)
    if frame.empty or len(frame.columns) == 0:
        raise ValueError(f"CSV file contains no data rows: {csv_path}")

    settings = {
        "account": _required_setting("SNOWFLAKE_ACCOUNT"),
        "user": _required_setting("SNOWFLAKE_USER"),
        "password": _required_setting("SNOWFLAKE_PASSWORD"),
        "warehouse": _required_setting("SNOWFLAKE_WAREHOUSE"),
        "database": _required_setting("SNOWFLAKE_DATABASE"),
        "schema": _required_setting("SNOWFLAKE_SCHEMA"),
        "role": _required_setting("SNOWFLAKE_LOAD_ROLE"),
    }
    connection = snowflake.connector.connect(**settings)
    try:
        success, _chunks, row_count, _output = write_pandas(
            connection,
            frame,
            table_name.upper(),
            database=settings["database"],
            schema=settings["schema"],
            auto_create_table=True,
            overwrite=True,
        )
        if not success:
            raise RuntimeError("Snowflake reported that the CSV load did not succeed.")
        return row_count
    finally:
        connection.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments and load the selected CSV."""
    parser = argparse.ArgumentParser(
        description="Load a CSV file into a Snowflake table."
    )
    parser.add_argument("csv_path", type=Path, help="Path to the CSV file.")
    parser.add_argument("table_name", help="Destination Snowflake table name.")
    parser.add_argument(
        "--delimiter",
        default=";",
        help="Single-character CSV delimiter (default: ';' for UCI Bank Marketing).",
    )
    args = parser.parse_args(argv)

    try:
        row_count = load_csv(args.csv_path, args.table_name, args.delimiter)
    except (
        OSError,
        ValueError,
        RuntimeError,
        snowflake.connector.Error,
        pd.errors.ParserError,
    ) as exc:
        print(f"Error loading CSV: {exc}", file=sys.stderr)
        return 1

    print(
        f"Loaded {row_count} rows into "
        f"{os.getenv('SNOWFLAKE_DATABASE', 'DATAMIND_DB')}."
        f"{os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC_DATA')}."
        f"{args.table_name.upper()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
