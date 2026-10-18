"""Print the row count and Snowflake query ID for a loaded table."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Sequence

from src.snowflake_client import SnowflakeClient, SnowflakeClientError


_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def main(argv: Sequence[str] | None = None) -> int:
    """Count rows in one table using the read-only Snowflake client."""
    parser = argparse.ArgumentParser(
        description="Count rows in a table using DATAMIND_READER."
    )
    parser.add_argument("table_name", help="Table name in the configured schema.")
    args = parser.parse_args(argv)
    if not _TABLE_NAME.fullmatch(args.table_name):
        parser.error("table_name must be a simple Snowflake identifier")

    try:
        with SnowflakeClient() as client:
            result = client.run_query(
                f"SELECT COUNT(*) AS ROW_COUNT FROM {args.table_name.upper()}"
            )
        print(f"Row count: {result['rows'][0][0]}")
        print(f"Query ID: {result['query_id']}")
    except (SnowflakeClientError, ValueError) as exc:
        print(f"Error counting table rows: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
