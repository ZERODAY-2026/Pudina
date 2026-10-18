"""Tests for the Streamlit chat rendering and session-history behavior."""

from __future__ import annotations

import sys
from contextlib import nullcontext
from types import ModuleType
from typing import Any

import pandas as pd
import pytest

from src.app import (
    available_configs,
    dataframe_for_result,
    main,
    render_assistant_message,
)
from src.pipeline import AnswerResult


class FakeStreamlit(ModuleType):
    """Small Streamlit test double for UI rendering and rerun state."""

    def __init__(self, question: str | None = None) -> None:
        super().__init__("streamlit")
        self.session_state: dict[str, Any] = {}
        self.sidebar = self
        self.question = question
        self.events: list[tuple[str, Any]] = []
        self.input_consumed = False

    def set_page_config(self, **kwargs: Any) -> None:
        self.events.append(("page_config", kwargs))

    def title(self, value: str) -> None:
        self.events.append(("title", value))

    def caption(self, value: str) -> None:
        self.events.append(("caption", value))

    def subheader(self, value: str) -> None:
        self.events.append(("subheader", value))

    def selectbox(self, _label: str, options: list[str], **_kwargs: Any) -> str:
        return options[0]

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        self.events.append(("button", _args[0] if _args else ""))
        return False

    def chat_input(self, _label: str) -> str | None:
        if self.input_consumed:
            return None
        self.input_consumed = True
        return self.question

    def chat_message(self, role: str) -> Any:
        self.events.append(("chat_message", role))
        return nullcontext()

    def spinner(self, message: str) -> Any:
        self.events.append(("spinner", message))
        return nullcontext()

    def expander(self, label: str) -> Any:
        self.events.append(("expander", label))
        return nullcontext()

    def markdown(self, value: str) -> None:
        self.events.append(("markdown", value))

    def write(self, value: str) -> None:
        self.events.append(("write", value))

    def info(self, value: str) -> None:
        self.events.append(("info", value))

    def warning(self, value: str) -> None:
        self.events.append(("warning", value))

    def error(self, value: str) -> None:
        self.events.append(("error", value))

    def code(self, value: str, language: str | None = None) -> None:
        self.events.append(("code", (value, language)))

    def dataframe(self, frame: pd.DataFrame, **_kwargs: Any) -> None:
        self.events.append(("dataframe", frame))


def test_available_configs_returns_yaml_files(tmp_path) -> None:
    """Only select YAML dataset config files from the config directory."""
    (tmp_path / "one.yaml").write_text("test: true", encoding="utf-8")
    (tmp_path / "two.yml").write_text("test: true", encoding="utf-8")
    (tmp_path / "readme.txt").write_text("not a config", encoding="utf-8")

    assert [path.name for path in available_configs(tmp_path)] == ["one.yaml"]


def test_dataframe_uses_result_columns_and_rows() -> None:
    """Build a labeled dataframe directly from verified result values."""
    result = AnswerResult(
        status="answerable",
        answer="One row.",
        explanation="The query returned one row.",
        columns=["AGE", "JOB"],
        rows=[(42, "admin.")],
    )

    frame = dataframe_for_result(result)

    assert list(frame.columns) == ["AGE", "JOB"]
    assert frame.to_dict(orient="records") == [{"AGE": 42, "JOB": "admin."}]


def test_render_assistant_message_shows_required_evidence_sections() -> None:
    """Render answer, assumptions, SQL, rows, and query ID in labeled sections."""
    fake_st = FakeStreamlit()
    result = AnswerResult(
        status="answerable",
        answer="Two clients matched.",
        explanation="BANK_MARKETING was filtered to y = 'yes'.",
        assumptions=["The returned row is the requested count."],
        sql="SELECT COUNT(*) AS COUNT FROM BANK_MARKETING",
        columns=["COUNT"],
        rows=[(2,)],
        query_id="query-123",
    )

    render_assistant_message(fake_st, result)

    section_labels = {
        event[1] for event in fake_st.events if event[0] == "expander"
    }
    assert section_labels == {
        "How I got this",
        "SQL executed",
        "Result rows",
        "Snowflake query ID",
    }
    assert ("markdown", result.answer) in fake_st.events
    assert ("code", (result.sql, "sql")) in fake_st.events
    assert any(
        event[0] == "dataframe"
        and event[1].to_dict(orient="records") == [{"COUNT": 2}]
        for event in fake_st.events
    )
    assert ("code", ("query-123", None)) in fake_st.events


def test_render_refusal_and_empty_result_with_friendly_status() -> None:
    """Make refusal and no-match states explicit without fabricating rows."""
    fake_st = FakeStreamlit()
    refusal = AnswerResult(
        status="unsupported",
        answer="I can't help with predictions. I can answer questions about the data.",
        explanation="Predictions are not supported.",
    )
    empty = AnswerResult(
        status="answerable",
        answer="No rows matched the requested criteria.",
        explanation="No matching records were returned.",
        sql="SELECT age FROM BANK_MARKETING WHERE age > 200 LIMIT 500",
        columns=["AGE"],
        query_id="empty-query",
    )

    render_assistant_message(fake_st, refusal)
    render_assistant_message(fake_st, empty)

    assert ("info", "Try asking a read-only question about the configured dataset.") in fake_st.events
    assert ("info", "No rows matched the requested criteria.") in fake_st.events
    assert ("write", "No SQL was executed.") in fake_st.events


def test_main_passes_follow_up_history_and_renders_clarification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass prior turns to the pipeline and display clarification normally."""
    fake_st = FakeStreamlit("Which month had the most subscriptions?")
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    calls: list[tuple[str, list[dict[str, str]]]] = []

    class StubPipeline:
        def __init__(self, config_path: object) -> None:
            assert config_path

        def ask(
            self,
            question: str,
            history: list[dict[str, str]],
        ) -> AnswerResult:
            calls.append((question, list(history)))
            if len(calls) == 1:
                return AnswerResult(
                    status="answerable",
                    answer="There were 12 subscriptions.",
                    explanation="The returned count was 12.",
                    sql="SELECT COUNT(*) FROM BANK_MARKETING WHERE y = 'yes'",
                    columns=["COUNT"],
                    rows=[(12,)],
                    query_id="first-query",
                )
            return AnswerResult(
                status="ambiguous",
                answer="The ranking needs a metric.",
                explanation="No ranking metric was assumed.",
                clarifying_question="Do you mean number of subscriptions or rate?",
            )

    monkeypatch.setattr("src.app.Pipeline", StubPipeline)
    main()

    assert calls == [
        ("Which month had the most subscriptions?", []),
    ]
    first_answer = fake_st.session_state["datamind_chat_messages"][-1]["content"]
    fake_st.question = "Compare with our previous result."
    fake_st.input_consumed = False
    main()

    assert calls[1] == (
        "Compare with our previous result.",
        [
            {
                "question": "Which month had the most subscriptions?",
                "answer": first_answer,
            }
        ],
    )
    assert fake_st.session_state["datamind_conversation_history"] == [
        {
            "question": "Which month had the most subscriptions?",
            "answer": first_answer,
        },
        {
            "question": "Compare with our previous result.",
            "answer": "The ranking needs a metric.",
        },
    ]
    assert (
        "info",
        "Do you mean number of subscriptions or rate?",
    ) in fake_st.events
    assert fake_st.session_state["datamind_chat_messages"][-1]["result"].status == "ambiguous"
    assert any(
        event == ("button", "How many clients are in the dataset?")
        for event in fake_st.events
    )


def test_main_displays_errors_and_preserves_renderable_chat_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Show a helpful service error and keep assistant history renderable."""
    fake_st = FakeStreamlit("How many clients?")
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    class BrokenPipeline:
        def __init__(self, config_path: object) -> None:
            pass

        def ask(
            self,
            _question: str,
            _history: list[dict[str, str]],
        ) -> AnswerResult:
            raise ConnectionError("Snowflake unavailable")

    monkeypatch.setattr("src.app.Pipeline", BrokenPipeline)
    main()

    assistant_message = fake_st.session_state["datamind_chat_messages"][-1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["result"].status == "error"
    assert "couldn't complete that request" in assistant_message["content"]
    assert any(event[0] == "warning" for event in fake_st.events)
