"""Mocked safety and lifecycle tests for the reversible Snowflake demo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import scripts.demo_data_change as demo
from src.pipeline import AnswerResult


@pytest.fixture
def demo_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace Snowflake and pipeline operations with observable fake state."""
    state: dict[str, Any] = {
        "baseline": 12,
        "rows": [],
        "clone_exists": False,
        "loader_sql": [],
        "pipeline_queries": 0,
        "fail_pipeline_call": None,
    }
    for name, value in {
        "SNOWFLAKE_ACCOUNT": "account",
        "SNOWFLAKE_USER": "user",
        "SNOWFLAKE_PASSWORD": "password",
        "SNOWFLAKE_ROLE": "DATAMIND_READER",
        "SNOWFLAKE_LOAD_ROLE": "DATAMIND_LOADER",
        "SNOWFLAKE_WAREHOUSE": "DATAMIND_WH",
        "SNOWFLAKE_DATABASE": "DATAMIND_DB",
        "SNOWFLAKE_SCHEMA": "PUBLIC_DATA",
        "SNOWFLAKE_TIMEOUT_SECONDS": "15",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(demo, "load_dotenv", lambda *_args, **_kwargs: None)

    class FakeCursor:
        def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
            if sql == "USE SECONDARY ROLES NONE":
                return
            state["loader_sql"].append(sql)
            if sql.startswith("CREATE OR REPLACE TABLE"):
                state["clone_exists"] = True
                state["rows"].clear()
            elif sql.startswith("INSERT INTO"):
                assert params is not None
                state["rows"].append(params)
            elif sql.startswith("DELETE FROM"):
                state["rows"].clear()
            elif sql.startswith("DROP TABLE"):
                state["clone_exists"] = False
                state["rows"].clear()

        def close(self) -> None:
            pass

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            pass

        def close(self) -> None:
            state["connection_closed"] = True

    class FakeReader:
        def __enter__(self) -> FakeReader:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def run_query(self, sql: str) -> dict[str, Any]:
            if "TAGGED_COUNT" in sql:
                count = sum(
                    1 for row in state["rows"] if demo._DEMO_TAG in row
                )
            else:
                is_demo_table = demo._DEMO_TABLE in sql
                count = state["baseline"] + (
                    len(state["rows"]) if is_demo_table else 0
                )
            state["direct_queries"] = state.get("direct_queries", 0) + 1
            return {
                "rows": [(count,)],
                "query_id": f"direct-{state['direct_queries']}",
            }

    class FakePipeline:
        def __init__(self, config_path: str | Path) -> None:
            self.is_demo = demo._DEMO_TABLE in Path(config_path).read_text(
                encoding="utf-8"
            )

        def ask(self, _question: str) -> AnswerResult:
            state["pipeline_queries"] += 1
            if state["pipeline_queries"] == state["fail_pipeline_call"]:
                raise RuntimeError("mock pipeline failure")
            count = state["baseline"] + (
                len(state["rows"]) if self.is_demo else 0
            )
            return AnswerResult(
                status="answerable",
                answer=f"There are {count} students.",
                explanation="Count from the dataset.",
                sql='SELECT COUNT(*) FROM BANK_MARKETING WHERE "job" = \'student\'',
                rows=[(count,)],
                query_id=f"pipeline-{state['pipeline_queries']}",
            )

    def connect(**kwargs: Any) -> FakeConnection:
        state["loader_connect_kwargs"] = kwargs
        return FakeConnection()

    monkeypatch.setattr(demo.snowflake.connector, "connect", connect)
    monkeypatch.setattr(demo, "SnowflakeClient", FakeReader)
    monkeypatch.setattr(demo, "Pipeline", FakePipeline)
    return state


def test_dry_run_queries_source_without_loader_or_writes(
    demo_mocks: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dry run may read the original table but must never open loader access."""
    assert demo.main(["--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "DRY RUN" in output
    assert "CURRENT SOURCE VALUE" in output
    assert demo_mocks["loader_sql"] == []
    assert "loader_connect_kwargs" not in demo_mocks
    assert demo_mocks["clone_exists"] is False


def test_confirmation_cancellation_precedes_any_snowflake_write(
    demo_mocks: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Rejecting the confirmation prompt must leave Snowflake untouched."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "no")

    assert demo.main([]) == 1

    assert "Cancelled" in capsys.readouterr().out
    assert demo_mocks["loader_sql"] == []
    assert "loader_connect_kwargs" not in demo_mocks


def test_success_uses_loader_and_restores_the_copy(
    demo_mocks: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Clone, insert, delete, and drop via loader; verify three reader answers."""
    assert demo.run_demo(input_fn=lambda _prompt: "DEMO") == 0

    output = capsys.readouterr().out
    assert "BEFORE: There are 12 students." in output
    assert "AFTER: There are 13 students." in output
    assert "REVERTED: There are 12 students." in output
    assert "distinct query ID" in output
    assert demo_mocks["loader_connect_kwargs"]["role"] == "DATAMIND_LOADER"
    assert [sql.split(" ", 1)[0] for sql in demo_mocks["loader_sql"]] == [
        "CREATE",
        "INSERT",
        "DELETE",
        "DROP",
    ]
    assert '"age"' in demo_mocks["loader_sql"][1]
    assert '"default"' in demo_mocks["loader_sql"][1]
    assert demo_mocks["clone_exists"] is False
    assert demo_mocks["rows"] == []


def test_pipeline_failure_still_deletes_tag_and_drops_clone(
    demo_mocks: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A post-insert pipeline failure must be surfaced and leave no clone."""
    demo_mocks["fail_pipeline_call"] = 2
    monkeypatch.setattr("builtins.input", lambda _prompt: "DEMO")

    assert demo.main([]) == 1

    assert "mock pipeline failure" in capsys.readouterr().err
    assert any(sql.startswith("DELETE FROM") for sql in demo_mocks["loader_sql"])
    assert demo_mocks["loader_sql"][-1].startswith("DROP TABLE")
    assert demo_mocks["clone_exists"] is False
    assert demo_mocks["rows"] == []
