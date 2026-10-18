"""Tests for the independent SQL targets and compact TPC-H manifest."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from eval.compute_tpch_ground_truth import (
    TPCH_GROUND_TRUTH_SQL,
    compute_tpch_ground_truth,
)
from eval.run_eval import load_questions
from src.snowflake_client import QueryResult, SnowflakeClient


class FakeDirectClient(SnowflakeClient):
    """Context-managed direct SQL client that never calls the question pipeline."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def __enter__(self) -> FakeDirectClient:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def run_query(self, sql: str) -> QueryResult:
        self.queries.append(sql)
        if "N.N_NAME" in sql:
            rows: list[tuple[object, ...]] = [
                ("CANADA", 100),
                ("UNITED STATES", 90),
                ("BRAZIL", 80),
            ]
        elif "R.R_NAME" in sql:
            rows = [("AFRICA", 5), ("AMERICA", 5)]
        elif "COUNT(*)" in sql:
            rows = [(Decimal("150000"),)]
        else:
            rows = [(Decimal("123.45"),)]
        return {
            "columns": ["VALUE"],
            "rows": rows,
            "query_id": f"direct-{len(self.queries)}",
            "row_count": len(rows),
            "elapsed_ms": 1,
        }


def test_tpch_manifest_has_requested_types_and_categories() -> None:
    """Provide 8–10 evaluation questions including join and refusal cases."""
    manifest = Path(__file__).resolve().parents[1] / "eval" / "questions_tpch.yaml"
    questions = load_questions(manifest)

    assert 8 <= len(questions) <= 10
    assert sum(question["category"] == "join" for question in questions) >= 2
    assert sum(question["category"] == "ambiguous" for question in questions) == 1
    assert sum(question["category"] == "unsupported" for question in questions) == 1
    assert all(
        "bank" not in question["question"].casefold() for question in questions
    )


def test_tpch_expected_values_run_only_handwritten_direct_sql() -> None:
    """Get targets and query IDs by executing the dedicated SQL map directly."""
    fake_client = FakeDirectClient()

    ground_truth, evidence = compute_tpch_ground_truth(
        client_factory=lambda: fake_client
    )

    assert len(fake_client.queries) == len(TPCH_GROUND_TRUTH_SQL) == 8
    assert all(
        "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1." in sql
        for sql in fake_client.queries
    )
    assert ground_truth["tpch_customer_count"] == 150000.0
    assert ground_truth["tpch_top_order_nations"] == [
        "CANADA",
        "UNITED STATES",
        "BRAZIL",
    ]
    assert len(evidence) == len(TPCH_GROUND_TRUTH_SQL)
    assert evidence[0]["query_id"] == "direct-1"
