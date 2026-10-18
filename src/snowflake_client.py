"""Read-only Snowflake client."""

from __future__ import annotations

import os
from time import perf_counter
from types import TracebackType
from typing import TypedDict

import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector import SnowflakeConnection
from snowflake.connector.errors import Error as SnowflakeError

from src.sql_guard import validate_read_only_sql


class QueryResult(TypedDict):
    """Result returned by a successful Snowflake query."""

    columns: list[str]
    rows: list[tuple[object, ...]]
    query_id: str
    row_count: int
    elapsed_ms: int


class SnowflakeClientError(RuntimeError):
    """Error raised when Snowflake configuration or operations fail."""


class SnowflakeClient:
    """Run SELECT queries through the configured read-only Snowflake role."""

    def __init__(self) -> None:
        """Load connection settings from .env and open the Snowflake session."""
        load_dotenv()
        settings = {
            "account": self._required_setting("SNOWFLAKE_ACCOUNT"),
            "user": self._required_setting("SNOWFLAKE_USER"),
            "password": self._required_setting("SNOWFLAKE_PASSWORD"),
            "warehouse": self._required_setting("SNOWFLAKE_WAREHOUSE"),
            "database": self._required_setting("SNOWFLAKE_DATABASE"),
            "schema": self._required_setting("SNOWFLAKE_SCHEMA"),
        }
        configured_role = self._required_setting("SNOWFLAKE_ROLE").upper()
        if configured_role != "DATAMIND_READER":
            raise SnowflakeClientError(
                "SNOWFLAKE_ROLE must be DATAMIND_READER for read-only queries."
            )

        try:
            self._connection: SnowflakeConnection | None = (
                snowflake.connector.connect(role="DATAMIND_READER", **settings)
            )
        except SnowflakeError as exc:
            raise SnowflakeClientError(f"Could not connect to Snowflake: {exc}") from exc

    @staticmethod
    def _required_setting(name: str) -> str:
        """Return a non-empty environment setting or raise a clear error."""
        value = os.getenv(name, "").strip()
        if not value:
            raise SnowflakeClientError(f"Missing required environment setting: {name}.")
        return value

    def run_query(self, sql: str) -> QueryResult:
        """Execute one SELECT query and return its rows and Snowflake metadata."""
        validate_read_only_sql(sql)
        connection = self._connection
        if connection is None:
            raise SnowflakeClientError("Snowflake client is closed.")

        started_at = perf_counter()
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute(sql)
            columns = [description[0] for description in cursor.description or ()]
            rows = cursor.fetchall()
            query_id = cursor.sfqid
            if not query_id:
                raise SnowflakeClientError(
                    "Snowflake completed the query without returning a query ID."
                )
        except SnowflakeError as exc:
            raise SnowflakeClientError(f"Snowflake query failed: {exc}") from exc
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except SnowflakeError as exc:
                    raise SnowflakeClientError(
                        f"Could not close query cursor: {exc}"
                    ) from exc

        return {
            "columns": columns,
            "rows": rows,
            "query_id": query_id,
            "row_count": len(rows),
            "elapsed_ms": int((perf_counter() - started_at) * 1000),
        }

    def close(self) -> None:
        """Close the Snowflake connection; repeated calls are harmless."""
        connection = self._connection
        self._connection = None
        if connection is None:
            return
        try:
            connection.close()
        except SnowflakeError as exc:
            raise SnowflakeClientError(f"Could not close Snowflake connection: {exc}") from exc

    def __enter__(self) -> SnowflakeClient:
        """Return this client for use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the Snowflake connection when leaving a context."""
        self.close()
