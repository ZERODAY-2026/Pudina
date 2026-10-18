"""Orchestrate question classification, guarded SQL, Snowflake, and responses."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlglot import exp, parse_one

from src.config_loader import (
    DatasetConfig,
    build_schema_prompt,
    load_dataset_config,
)
from src.llm import GemmaClient
from src.prompts import (
    build_answer_prompt,
    build_classification_prompt,
    build_sql_prompt,
)
from src.sql_guard import SQLValidationError, configured_max_limit, validate_read_only_sql
from src.snowflake_client import (
    QueryResult,
    SnowflakeClient,
    SnowflakeClientError,
)


class ClassificationResult(BaseModel):
    """Structured model classification of a user question."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["answerable", "ambiguous", "unsupported"]
    reason: str = Field(min_length=1)
    clarifying_question: str | None = None

    @model_validator(mode="after")
    def require_clarification(self) -> ClassificationResult:
        """Require a clarifying question when classification is ambiguous."""
        if self.status == "ambiguous" and not self.clarifying_question:
            raise ValueError("Ambiguous questions require a clarifying_question.")
        return self


class GeneratedAnswer(BaseModel):
    """Structured answer text generated from query result rows."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)


class AnswerResult(BaseModel):
    """Complete response, including status and Snowflake execution metadata."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["answerable", "ambiguous", "unsupported", "error"]
    answer: str
    explanation: str
    assumptions: list[str] = Field(default_factory=list)
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[tuple[object, ...]] = Field(default_factory=list)
    query_id: str | None = None
    clarifying_question: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Pipeline:
    """Answer data questions using a config-scoped, read-only Snowflake path."""

    def __init__(
        self,
        config_path: str | Path = Path("config/dataset_a.yaml"),
        llm: GemmaClient | None = None,
        max_limit: int | None = None,
    ) -> None:
        """Load dataset metadata and prepare the schema prompt."""
        self.config_path = Path(config_path)
        self.config: DatasetConfig = load_dataset_config(self.config_path)
        self.schema_prompt = build_schema_prompt(self.config_path)
        self.llm = llm or GemmaClient()
        self.max_limit = configured_max_limit() if max_limit is None else max_limit
        if self.max_limit < 1:
            raise ValueError("max_limit must be a positive integer.")
        self.allowed_tables = [table.name for table in self.config.tables]

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> AnswerResult:
        """Classify a question and return a data-backed answer or next step."""
        if not question.strip():
            raise ValueError("question must not be empty.")
        recent_history = list(history or [])[-6:]
        if _is_write_request(question):
            return self._unsupported_result(
                "I can't write, change, or delete data. "
                "I can answer read-only questions about the configured dataset."
            )
        if _needs_metric_clarification(question):
            return AnswerResult(
                status="ambiguous",
                answer="“Best” or “top” needs a metric to rank by.",
                explanation=(
                    "The dataset contains multiple fields that could define a "
                    "ranking, so no metric was assumed."
                ),
                clarifying_question=(
                    "Which metric should I use to rank the results, such as "
                    "subscription rate, balance, or age?"
                ),
            )

        classification = self.llm.generate_json(
            build_classification_prompt(question, recent_history),
            ClassificationResult,
        )

        if classification.status == "ambiguous":
            clarifying_question = classification.clarifying_question
            if clarifying_question is None:
                raise RuntimeError("Ambiguous classification omitted its question.")
            return AnswerResult(
                status="ambiguous",
                answer=classification.reason,
                explanation=classification.reason,
                clarifying_question=clarifying_question,
            )
        if classification.status == "unsupported":
            return self._unsupported_result(classification.reason)

        sql: str | None = None
        last_error: str | None = None
        result: QueryResult | None = None
        for attempt in range(2):
            raw_sql = self.llm.generate(
                build_sql_prompt(
                    self.schema_prompt,
                    self.config,
                    question,
                    recent_history,
                    previous_sql=sql if attempt else None,
                    error=last_error if attempt else None,
                ),
                system="Return one Snowflake SELECT query only.",
                temperature=0.0,
                max_tokens=512,
            )
            sql = _strip_sql_fence(raw_sql)
            try:
                sql = validate_read_only_sql(
                    sql,
                    table_allowlist=self.allowed_tables,
                    max_limit=self.max_limit,
                )
                with SnowflakeClient() as client:
                    result = client.run_query(sql)
                break
            except (SQLValidationError, SnowflakeClientError) as exc:
                last_error = str(exc)
                if attempt == 1:
                    return AnswerResult(
                        status="error",
                        answer=(
                            "I couldn't safely run a read-only query for this "
                            "request."
                        ),
                        explanation=(
                            "Only SELECT queries against the configured dataset "
                            "tables can run. Please rephrase as a question about "
                            "the available data."
                        ),
                        warnings=[f"Query blocked: {last_error}"],
                    )

        if result is None or sql is None:
            raise RuntimeError("Pipeline completed without a query result.")

        if not result["rows"]:
            table_names, filters = _query_context(sql)
            table_text = ", ".join(table_names) if table_names else "the configured dataset"
            filter_text = f" Filters: {filters}." if filters else " No filters were applied."
            return AnswerResult(
                status="answerable",
                answer="No rows matched the requested criteria.",
                explanation=(
                    f"The query returned no rows from {table_text}.{filter_text}"
                ),
                assumptions=["No matching rows were returned by Snowflake."],
                sql=sql,
                columns=result["columns"],
                rows=[],
                query_id=result["query_id"],
            )

        generated = self.llm.generate_json(
            build_answer_prompt(question, sql, result["columns"], result["rows"]),
            GeneratedAnswer,
        )
        warnings = _check_generated_numbers(
            generated.answer,
            generated.explanation,
            generated.assumptions,
            result["rows"],
        )
        explanation = generated.explanation
        if warnings:
            explanation += " Numeric consistency warning: " + " ".join(warnings)
        return AnswerResult(
            status="answerable",
            answer=generated.answer,
            explanation=explanation,
            assumptions=generated.assumptions,
            sql=sql,
            columns=result["columns"],
            rows=result["rows"],
            query_id=result["query_id"],
            warnings=warnings,
        )

    def _unsupported_result(self, reason: str) -> AnswerResult:
        """Return a polite refusal with examples of supported data questions."""
        table_names = ", ".join(table.name for table in self.config.tables)
        column_names = ", ".join(
            column.name for table in self.config.tables for column in table.columns
        )
        supported_scope = (
            f"I can answer read-only questions about {self.config.dataset_name}, "
            f"including data in {table_names} and fields such as {column_names}."
        )
        return AnswerResult(
            status="unsupported",
            answer=f"I can't help with that request. {supported_scope}",
            explanation=reason,
        )


def _strip_sql_fence(sql: str) -> str:
    """Remove optional SQL Markdown fences around generated SQL."""
    match = re.fullmatch(
        r"\s*```(?:sql)?\s*(.*?)\s*```\s*",
        sql,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else sql.strip()


_WRITE_REQUEST = re.compile(
    r"\b(?:delete|drop|insert|update|alter|truncate|create|write|modify|"
    r"remove|erase|change)\b",
    re.IGNORECASE,
)
_RANK_WORD = re.compile(r"\b(?:best|top)\b", re.IGNORECASE)
_RANK_METRIC = re.compile(
    r"\b(?:age|balance|duration|campaign|pdays|previous|count|number|"
    r"amount|rate|percentage|percent|subscription|subscribed|conversion|"
    r"salary)\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?%?")


def _is_write_request(question: str) -> bool:
    """Identify explicit user requests to mutate, remove, or define data."""
    return _WRITE_REQUEST.search(question) is not None


def _needs_metric_clarification(question: str) -> bool:
    """Detect unqualified best/top requests before asking the classifier."""
    return _RANK_WORD.search(question) is not None and _RANK_METRIC.search(question) is None


def _query_context(sql: str) -> tuple[list[str], str | None]:
    """Extract table names and an optional filter expression for empty-result text."""
    query = parse_one(sql, read="snowflake")
    tables = list(dict.fromkeys(table.name for table in query.find_all(exp.Table)))
    where = query.find(exp.Where)
    filters = where.this.sql(dialect="snowflake") if where else None
    return tables, filters


def _check_generated_numbers(
    answer: str,
    explanation: str,
    assumptions: list[str],
    rows: list[tuple[object, ...]],
) -> list[str]:
    """Flag numeric claims in generated text absent from all returned row values."""
    returned_numbers: set[str] = set()
    for row in rows:
        for value in row:
            returned_numbers.update(_numeric_tokens(str(value)))
    claimed_numbers = _numeric_tokens(
        "\n".join((answer, explanation, *assumptions))
    )
    unsupported_numbers = sorted(claimed_numbers - returned_numbers)
    if not unsupported_numbers:
        return []
    values = ", ".join(unsupported_numbers)
    return [
        f"Generated text contains numeric value(s) {values} that do not appear "
        "in the returned rows; verify the answer before relying on those values."
    ]


def _numeric_tokens(text: str) -> set[str]:
    """Normalize numeric tokens for exact row-to-text consistency checks."""
    tokens: set[str] = set()
    for match in _NUMBER.finditer(text):
        raw_value = match.group().replace(",", "").removesuffix("%")
        try:
            normalized = format(Decimal(raw_value).normalize(), "f")
            if "." in normalized:
                normalized = normalized.rstrip("0").rstrip(".")
            tokens.add(normalized)
        except InvalidOperation:
            continue
    return tokens


def ask(
    question: str,
    history: list[dict[str, str]] | None = None,
    config_path: str | Path = Path("config/dataset_a.yaml"),
) -> AnswerResult:
    """Run a question through a newly configured pipeline instance."""
    return Pipeline(config_path=config_path).ask(question, history=history)
