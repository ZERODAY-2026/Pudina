"""Demonstrate a reversible data change on a disposable Snowflake table copy."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable, Sequence

import snowflake.connector
import yaml
from dotenv import load_dotenv
from snowflake.connector import SnowflakeConnection
from snowflake.connector.errors import Error as SnowflakeError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import DatasetConfig, load_dataset_config
from src.pipeline import AnswerResult, Pipeline
from src.snowflake_client import SnowflakeClient


_CONFIG_PATH = PROJECT_ROOT / "config" / "dataset_a.yaml"
_SOURCE_TABLE = "BANK_MARKETING"
_DEMO_TABLE = "BANK_MARKETING_DEMO_CHANGE"
_DEMO_TAG = "__DATAMIND_B4_DEMO__"
_QUESTION = "How many clients have the student occupation?"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")

_SYNTHETIC_ROW: dict[str, str | int] = {
    "age": 42,
    "job": "student",
    "marital": _DEMO_TAG,
    "education": "tertiary",
    "default": "no",
    "balance": 0,
    "housing": "no",
    "loan": "no",
    "contact": "cellular",
    "day": 1,
    "month": "may",
    "duration": 1,
    "campaign": 1,
    "pdays": -1,
    "previous": 0,
    "poutcome": "unknown",
    "y": "no",
}


class DemoFailure(RuntimeError):
    """Raised when the controlled data-change demonstration cannot be verified."""


def _required_setting(name: str) -> str:
    """Return a non-empty environment value or fail with its setting name."""
    value = os.getenv(name, "").strip()
    if not value:
        raise DemoFailure(f"Missing required environment setting: {name}.")
    return value


def _load_settings() -> tuple[dict[str, str], int]:
    """Validate the reader and loader roles without displaying credentials."""
    settings = {
        "account": _required_setting("SNOWFLAKE_ACCOUNT"),
        "user": _required_setting("SNOWFLAKE_USER"),
        "password": _required_setting("SNOWFLAKE_PASSWORD"),
        "warehouse": _required_setting("SNOWFLAKE_WAREHOUSE"),
        "database": _required_setting("SNOWFLAKE_DATABASE"),
        "schema": _required_setting("SNOWFLAKE_SCHEMA"),
    }
    reader_role = _required_setting("SNOWFLAKE_ROLE").upper()
    loader_role = _required_setting("SNOWFLAKE_LOAD_ROLE").upper()
    if reader_role != "DATAMIND_READER":
        raise DemoFailure("SNOWFLAKE_ROLE must be DATAMIND_READER.")
    if loader_role != "DATAMIND_LOADER":
        raise DemoFailure("SNOWFLAKE_LOAD_ROLE must be DATAMIND_LOADER.")
    try:
        timeout = int(os.getenv("SNOWFLAKE_TIMEOUT_SECONDS", "15"))
    except ValueError as exc:
        raise DemoFailure("SNOWFLAKE_TIMEOUT_SECONDS must be a positive integer.") from exc
    if timeout < 1:
        raise DemoFailure("SNOWFLAKE_TIMEOUT_SECONDS must be a positive integer.")
    return settings, timeout


def _quote_identifier(identifier: str) -> str:
    """Quote a simple configured Snowflake identifier."""
    if not _IDENTIFIER.fullmatch(identifier):
        raise DemoFailure(f"Unsupported Snowflake identifier in configuration: {identifier!r}")
    return f'"{identifier}"'


def _qualified_table(database: str, schema: str, table: str) -> str:
    """Return a safely quoted three-part Snowflake table name."""
    return ".".join(
        _quote_identifier(identifier.upper()) for identifier in (database, schema, table)
    )


def _connect_loader(
    settings: dict[str, str],
    timeout: int,
) -> SnowflakeConnection:
    """Open a direct Snowflake session using only DATAMIND_LOADER."""
    connection = snowflake.connector.connect(
        role="DATAMIND_LOADER",
        login_timeout=timeout,
        network_timeout=timeout,
        socket_timeout=timeout,
        **settings,
    )
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("USE SECONDARY ROLES NONE")
        finally:
            cursor.close()
    except SnowflakeError:
        connection.close()
        raise
    return connection


def _read_count(sql: str) -> tuple[int, str]:
    """Run a direct verification query through the reader-only client."""
    with SnowflakeClient() as client:
        result = client.run_query(sql)
    if not result["rows"] or not result["query_id"]:
        raise DemoFailure("Snowflake returned no count or query ID for a direct check.")
    try:
        count = int(result["rows"][0][0])
    except (TypeError, ValueError) as exc:
        raise DemoFailure("Snowflake returned a non-integer count for a direct check.") from exc
    return count, result["query_id"]


def _student_count_sql(table: str) -> str:
    """Create the direct SQL check for the chosen aggregate."""
    return f'SELECT COUNT(*) AS STUDENT_COUNT FROM {table} WHERE "job" = \'student\''


def _tag_count_sql(table: str) -> str:
    """Create a direct SQL check for tagged demonstration rows."""
    escaped_tag = _DEMO_TAG.replace("'", "''")
    return f'SELECT COUNT(*) AS TAGGED_COUNT FROM {table} WHERE "marital" = \'{escaped_tag}\''


def _answer_number(answer: str) -> int:
    """Extract the numeric count from Gemma's short answer."""
    match = _NUMBER.search(answer)
    if match is None:
        raise DemoFailure("The pipeline answer did not contain a numeric count.")
    try:
        return int(match.group().replace(",", ""))
    except ValueError as exc:
        raise DemoFailure("The pipeline answer did not contain an integer count.") from exc


def _observe(
    label: str,
    pipeline: Pipeline,
    table: str,
) -> tuple[int, str]:
    """Ask the same aggregate and cross-check result rows and answer with SQL."""
    result: AnswerResult = pipeline.ask(_QUESTION)
    if (
        result.status != "answerable"
        or result.query_id is None
        or result.sql is None
        or not result.rows
    ):
        details = "; ".join(result.warnings)
        raise DemoFailure(
            f"{label} pipeline result was not answerable with query evidence."
            + (f" Details: {details}" if details else "")
        )
    direct_count, direct_query_id = _read_count(_student_count_sql(table))
    try:
        pipeline_count = int(result.rows[0][0])
    except (TypeError, ValueError, IndexError) as exc:
        raise DemoFailure(f"{label} pipeline returned no integer count row.") from exc
    answer_count = _answer_number(result.answer)
    if pipeline_count != direct_count or answer_count != direct_count:
        raise DemoFailure(
            f"{label} did not match direct SQL: answer={answer_count}, "
            f"pipeline_row={pipeline_count}, direct_count={direct_count}."
        )
    print(f"{label}: {result.answer}")
    print(f"  Pipeline query ID: {result.query_id}")
    print(
        f"  Direct SQL count: {direct_count} "
        f"(query ID {direct_query_id})"
    )
    return direct_count, result.query_id


def _temporary_demo_config(
    source_config: Path,
    destination: Path,
) -> DatasetConfig:
    """Create an isolated in-process config that points at the Snowflake clone."""
    try:
        raw_config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DemoFailure(f"Could not read the Bank Marketing config: {exc}") from exc
    if (
        not isinstance(raw_config, dict)
        or not isinstance(raw_config.get("tables"), list)
        or len(raw_config["tables"]) != 1
        or raw_config["tables"][0].get("name") != _SOURCE_TABLE
    ):
        raise DemoFailure(
            "The demo expects config/dataset_a.yaml to define only BANK_MARKETING."
        )
    raw_config["tables"][0]["name"] = _DEMO_TABLE
    raw_config["dataset_name"] = "UCI Bank Marketing Demo Copy"
    raw_config["notes"] = [
        note.replace(_SOURCE_TABLE, _DEMO_TABLE)
        if isinstance(note, str)
        else note
        for note in raw_config.get("notes", [])
    ]
    try:
        destination.write_text(
            yaml.safe_dump(raw_config, sort_keys=False),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DemoFailure(f"Could not create temporary demo config: {exc}") from exc
    return load_dataset_config(destination)


def _synthetic_values(config: DatasetConfig) -> tuple[list[str], tuple[str | int, ...]]:
    """Map the controlled synthetic record to every configured table column."""
    columns = [column.name for column in config.tables[0].columns]
    missing = set(columns) - _SYNTHETIC_ROW.keys()
    if missing:
        raise DemoFailure(
            "The synthetic row does not cover configured columns: "
            + ", ".join(sorted(missing))
        )
    return columns, tuple(_SYNTHETIC_ROW[column] for column in columns)


def _execute_loader(connection: SnowflakeConnection, sql: str, params: tuple | None = None) -> None:
    """Execute one controlled loader-role statement and surface failures."""
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params) if params is not None else cursor.execute(sql)
        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()


def _clone_table(
    connection: SnowflakeConnection,
    source_table: str,
    demo_table: str,
) -> None:
    """Create or refresh the reserved demo table as a zero-copy Snowflake clone."""
    _execute_loader(
        connection,
        f"CREATE OR REPLACE TABLE {demo_table} CLONE {source_table}",
    )


def _insert_synthetic(
    connection: SnowflakeConnection,
    table: str,
    config: DatasetConfig,
) -> None:
    """Insert exactly one tagged synthetic client into the cloned table."""
    columns, values = _synthetic_values(config)
    column_sql = ", ".join(_quote_identifier(column) for column in columns)
    placeholders = ", ".join("%s" for _ in values)
    _execute_loader(
        connection,
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
        values,
    )


def _delete_tagged_rows(connection: SnowflakeConnection, table: str) -> None:
    """Remove only rows bearing this demo's unique tag from the demo clone."""
    _execute_loader(
        connection,
        f'DELETE FROM {table} WHERE "marital" = %s',
        (_DEMO_TAG,),
    )


def _drop_demo_table(connection: SnowflakeConnection, table: str) -> None:
    """Remove the reserved demo copy after its reverted value is verified."""
    _execute_loader(connection, f"DROP TABLE IF EXISTS {table}")


def _confirm(input_fn: Callable[[str], str]) -> bool:
    """Require an explicit phrase before replacing or changing the demo copy."""
    response = input_fn(
        "This will replace the reserved demo copy, insert one tagged synthetic "
        "row, delete it, then drop the copy. Type DEMO to continue: "
    )
    return response.strip() == "DEMO"


def run_demo(
    dry_run: bool = False,
    input_fn: Callable[[str], str] | None = None,
) -> int:
    """Run the checked before/after/reverted sequence, or a read-only preview."""
    load_dotenv(PROJECT_ROOT / ".env")
    confirm_input = input if input_fn is None else input_fn
    settings, timeout = _load_settings()
    source_config = load_dataset_config(_CONFIG_PATH)
    source_table = source_config.tables[0].name
    source_fqn = _qualified_table(settings["database"], settings["schema"], source_table)
    demo_fqn = _qualified_table(settings["database"], settings["schema"], _DEMO_TABLE)

    if dry_run:
        print("DRY RUN: no Snowflake writes, clone creation, or cleanup will occur.")
        pipeline = Pipeline(config_path=_CONFIG_PATH)
        _observe("CURRENT SOURCE VALUE", pipeline, source_table)
        print(
            f"Would clone {source_fqn}, insert one tagged student row into "
            f"{demo_fqn}, verify the increment, remove the row, verify the "
            "original count, and drop the clone."
        )
        return 0

    if not _confirm(confirm_input):
        print("Cancelled; no Snowflake writes were performed.")
        return 1

    connection = _connect_loader(settings, timeout)
    try:
        try:
            _clone_table(connection, source_fqn, demo_fqn)
            with tempfile.TemporaryDirectory(prefix="datamind-demo-") as temp_dir:
                demo_config_path = Path(temp_dir) / "dataset_demo.yaml"
                demo_config = _temporary_demo_config(_CONFIG_PATH, demo_config_path)
                tagged_count, _ = _read_count(_tag_count_sql(demo_fqn))
                if tagged_count:
                    raise DemoFailure(
                        "The source copy already contains the reserved demo tag; "
                        "the demo stopped before inserting anything."
                    )
                pipeline = Pipeline(config_path=demo_config_path)
                before, before_query_id = _observe(
                    "BEFORE", pipeline, demo_fqn
                )
                try:
                    _insert_synthetic(connection, demo_fqn, demo_config)
                    after, after_query_id = _observe("AFTER", pipeline, demo_fqn)
                    if after != before + 1:
                        raise DemoFailure(
                            f"Expected one added student row: before={before}, "
                            f"after={after}."
                        )
                    if after_query_id == before_query_id:
                        raise DemoFailure(
                            "Snowflake reused the query ID for the after question."
                        )
                finally:
                    _delete_tagged_rows(connection, demo_fqn)

                remaining_tags, _ = _read_count(_tag_count_sql(demo_fqn))
                if remaining_tags != 0:
                    raise DemoFailure(
                        f"Revert left {remaining_tags} tagged row(s) in the demo copy."
                    )
                reverted, reverted_query_id = _observe(
                    "REVERTED", pipeline, demo_fqn
                )
                if reverted != before:
                    raise DemoFailure(
                        f"Reverted value {reverted} does not match before value {before}."
                    )
                if reverted_query_id in {before_query_id, after_query_id}:
                    raise DemoFailure(
                        "The reverted question did not produce a new query ID."
                    )
                print(
                    "PASS: before, after, and reverted values match their direct "
                    "SQL checks; each pipeline question has a distinct query ID."
                )
        finally:
            _drop_demo_table(connection, demo_fqn)
    finally:
        connection.close()
    print("PASS: the demo clone was dropped; BANK_MARKETING was never modified.")
    return 0


def _redact_secrets(message: str) -> str:
    """Remove configured credentials from any connector error shown to the user."""
    for name in ("SNOWFLAKE_PASSWORD", "GEMMA_API_KEY"):
        secret = os.getenv(name, "")
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the dry-run option and report controlled failures without secrets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the reader question and direct SQL check without any writes.",
    )
    args = parser.parse_args(argv)
    try:
        return run_demo(dry_run=args.dry_run)
    except Exception as exc:
        print(
            f"Demo failed ({type(exc).__name__}): "
            f"{_redact_secrets(str(exc))}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
