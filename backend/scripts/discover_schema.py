"""Discover Snowflake table and column metadata into an editable YAML draft."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Sequence

import yaml
from dotenv import load_dotenv

from src.snowflake_client import SnowflakeClient, SnowflakeClientError


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_TODO = "TODO: add a plain-English description."


def _validate_identifier(value: str, setting_name: str) -> str:
    """Validate a database or schema identifier before interpolating it in SQL."""
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{setting_name} must be a simple Snowflake identifier.")
    return value


def discover_schema(database: str, schema: str) -> dict[str, object]:
    """Read INFORMATION_SCHEMA metadata using the configured read-only client."""
    database = _validate_identifier(database, "database")
    schema = _validate_identifier(schema, "schema")
    schema_literal = schema.replace("'", "''")
    table_sql = (
        "SELECT TABLE_NAME, TABLE_COMMENT "
        f'FROM "{database}".INFORMATION_SCHEMA.TABLES '
        f"WHERE TABLE_SCHEMA = '{schema_literal}' "
        "AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
    )
    columns_sql = (
        "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT "
        f'FROM "{database}".INFORMATION_SCHEMA.COLUMNS '
        f"WHERE TABLE_SCHEMA = '{schema_literal}' "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )

    with SnowflakeClient() as client:
        tables_result = client.run_query(table_sql)
        columns_result = client.run_query(columns_sql)

    columns_by_table: dict[str, list[dict[str, object]]] = {}
    for table_name, column_name, data_type, is_nullable, comment in columns_result[
        "rows"
    ]:
        columns_by_table.setdefault(table_name, []).append(
            {
                "name": column_name,
                "type": data_type,
                "description": comment or _TODO,
                "sample_values": [],
                "nullable": is_nullable == "YES",
            }
        )

    tables = []
    for table_name, comment in tables_result["rows"]:
        tables.append(
            {
                "name": table_name,
                "description": comment or _TODO,
                "columns": columns_by_table.get(table_name, []),
            }
        )
    if not tables:
        raise ValueError(
            f"No base tables found in Snowflake schema {database}.{schema}."
        )
    return {
        "dataset_name": f"{database}.{schema}",
        "description": _TODO,
        "tables": tables,
        "joins": [],
        "notes": ["Add dataset-specific quirks, units, and missing-value notes."],
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Discover configured Snowflake schema metadata and write an editable YAML."""
    parser = argparse.ArgumentParser(
        description="Discover Snowflake INFORMATION_SCHEMA metadata as YAML."
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Destination YAML path for the draft config.",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    database = os.getenv("SNOWFLAKE_DATABASE", "").strip()
    schema = os.getenv("SNOWFLAKE_SCHEMA", "").strip()
    if not database or not schema:
        print(
            "Error: SNOWFLAKE_DATABASE and SNOWFLAKE_SCHEMA must be configured.",
            file=sys.stderr,
        )
        return 1

    try:
        draft = discover_schema(database, schema)
        with args.output_path.open("w", encoding="utf-8", newline="\n") as output:
            yaml.safe_dump(draft, output, sort_keys=False, allow_unicode=True)
    except (OSError, ValueError, SnowflakeClientError, yaml.YAMLError) as exc:
        print(f"Error discovering schema: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote editable schema draft to {args.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
