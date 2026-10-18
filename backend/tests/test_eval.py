"""Tests for source-CSV ground truth and evaluation report generation."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from eval.compute_ground_truth import compute_ground_truth
from eval.run_eval import (
    main as run_eval_main,
    evaluate_result,
    load_questions,
    render_report,
    run_evaluation,
    EvaluationRecord,
)
from src.pipeline import AnswerResult


def write_bank_csv(path: Path) -> Path:
    """Create a small semicolon-delimited Bank Marketing-shaped fixture."""
    frame = pd.DataFrame(
        [
            (30, "admin.", "yes", 10, 1, 999, "cellular", "may", "yes"),
            (50, "technician", "no", 20, 3, 10, "telephone", "jun", "no"),
            (45, "admin.", "yes", 30, 2, 999, "cellular", "jun", "yes"),
            (40, "blue-collar", "yes", 40, 4, 1, "cellular", "may", "no"),
            (70, "admin.", "no", 50, 3, 999, "unknown", "jun", "yes"),
        ],
        columns=(
            "age",
            "job",
            "housing",
            "duration",
            "campaign",
            "pdays",
            "contact",
            "month",
            "y",
        ),
    )
    frame.to_csv(path, sep=";", index=False)
    return path


def test_ground_truth_uses_pandas_source_data(tmp_path: Path) -> None:
    """Compute independent expected values from a source-style CSV."""
    csv_path = write_bank_csv(tmp_path / "bank-full.csv")

    truth = compute_ground_truth(csv_path)

    assert truth == {
        "total_rows": 5,
        "mean_age": 47.0,
        "subscribed_count": 3,
        "mean_duration": 30.0,
        "housing_yes_count": 3,
        "admin_job_count": 3,
        "campaign_three_or_more_count": 3,
        "cellular_count": 3,
        "not_previously_contacted_count": 3,
        "housing_subscribed_count": 2,
        "over_40_subscribed_count": 2,
        "top_subscription_month": "jun",
    }


def test_eval_manifest_has_twenty_questions_and_five_held_out() -> None:
    """Validate requested category coverage and held-out split count."""
    questions = load_questions(Path(__file__).resolve().parents[1] / "eval" / "questions.yaml")

    assert len(questions) == 20
    assert sum(question.get("held_out", False) for question in questions) == 5
    assert {
        "simple_aggregate",
        "filter",
        "join",
        "multi_step",
        "ambiguous",
        "empty_result",
        "unsupported",
    } <= {question["category"] for question in questions}


def test_unseen_manifest_has_required_coverage_and_four_history_followups() -> None:
    """Keep the unseen set separate and ensure follow-ups carry prior turns."""
    manifest = Path(__file__).resolve().parents[1] / "eval" / "questions_unseen.yaml"
    questions = load_questions(manifest)
    category_counts = {
        category: sum(question["category"] == category for question in questions)
        for category in {question["category"] for question in questions}
    }

    assert len(questions) == 20
    assert category_counts["ambiguous"] == 3
    assert category_counts["empty_result"] == 2
    assert category_counts["unsupported"] == 3
    assert category_counts["prompt_injection"] == 1
    assert sum(bool(question.get("history")) for question in questions) == 4


def test_manifest_ground_truth_calculations_use_pandas(
    tmp_path: Path,
) -> None:
    """Compute an unseen target from a manifest without using pipeline code."""
    csv_path = write_bank_csv(tmp_path / "bank-full.csv")
    fixture = pd.read_csv(csv_path, sep=";")
    fixture["marital"] = ["single", "married", "single", "married", "single"]
    fixture.to_csv(csv_path, sep=";", index=False)
    manifest_path = tmp_path / "questions.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "subscription_pct",
                    "expected_answer": {
                        "type": "numeric",
                        "calculation": {
                            "operation": "percentage",
                            "numerator_filters": [
                                {"column": "y", "operator": "eq", "value": "yes"}
                            ],
                            "denominator_filters": [],
                        },
                    },
                },
                {
                    "id": "highest_subscription_rate",
                    "expected_answer": {
                        "type": "string",
                        "calculation": {
                            "operation": "top_rate_group",
                            "group_column": "marital",
                            "outcome_column": "y",
                            "outcome_value": "yes",
                            "filters": [],
                        },
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    truth = compute_ground_truth(csv_path, manifest_path)

    assert truth["subscription_pct"] == pytest.approx(60.0)
    assert truth["highest_subscription_rate"] == "single"


def test_string_group_evaluation_requires_the_top_result_group() -> None:
    """Do not pass a top-group question just because the target is listed later."""
    question = {
        "expected_answer": {
            "type": "string",
            "ground_truth_key": "top_group",
        }
    }
    result = AnswerResult(
        status="answerable",
        answer="The largest group is married.",
        explanation="Groups are ordered by the generated SQL.",
        rows=[("married", 20), ("single", 10)],
    )

    passed, _expected, _actual, reason = evaluate_result(
        question, result, {"top_group": "single"}
    )

    assert not passed
    assert "first result group" in reason


def test_run_evaluation_passes_manifest_history_to_followup() -> None:
    """Pass preceding user and assistant turns to the pipeline for follow-ups."""
    history = [
        {"role": "user", "content": "What is the average balance?"},
        {"role": "assistant", "content": "The measure was average balance."},
    ]

    class HistoryPipeline:
        received: list[dict[str, str]] | None = None

        def ask(
            self, _question: str, history: list[dict[str, str]] | None = None
        ) -> AnswerResult:
            self.received = history
            return AnswerResult(
                status="answerable",
                answer="The average balance was 47.",
                explanation="Calculated from the requested group.",
            )

    pipeline = HistoryPipeline()
    question = {
        "id": "followup",
        "category": "multi_step",
        "question": "And for students?",
        "history": history,
        "expected_answer": {"type": "numeric", "ground_truth_key": "followup"},
    }

    records = run_evaluation([question], pipeline, {"followup": 47.0})

    assert records[0].passed
    assert pipeline.received == history


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", ["filter"]),
        ("expected_answer", {"type": "percent", "ground_truth_key": "mean_age"}),
    ],
)
def test_eval_manifest_rejects_malformed_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    """Reject invalid manifest shapes with a clear validation error."""
    questions = [
        {
            "id": f"question_{index}",
            "category": "filter",
            "question": "How many clients?",
            "expected_answer": {
                "type": "numeric",
                "ground_truth_key": "total_rows",
            },
            "how_expected_computed": "Count all rows.",
            "held_out": index < 5,
        }
        for index in range(20)
    ]
    questions[0][field] = value
    manifest_path = tmp_path / "questions.yaml"
    manifest_path.write_text(yaml.safe_dump(questions), encoding="utf-8")

    with pytest.raises(ValueError):
        load_questions(manifest_path)


def test_numeric_evaluation_applies_tolerance() -> None:
    """Compare an answer's numeric result with its pandas-derived target."""
    question = {
        "expected_answer": {"type": "numeric", "ground_truth_key": "mean_age"}
    }
    result = AnswerResult(
        status="answerable",
        answer="The average age was 47.004 years.",
        explanation="Computed from all rows.",
    )

    passed, expected, _actual, reason = evaluate_result(
        question, result, {"mean_age": 47.0}, numeric_tolerance=0.01
    )

    assert passed
    assert expected == "numeric=47.0"
    assert reason == ""


def test_behavior_evaluation_checks_status_and_no_rows() -> None:
    """Compare non-answerable statuses and empty-result behavior explicitly."""
    ambiguous = {
        "expected_behavior": {"status": "ambiguous", "contains": "metric"}
    }
    empty = {"expected_behavior": {"status": "answerable", "no_rows": True}}

    ambiguous_result = AnswerResult(
        status="ambiguous",
        answer="",
        explanation="",
        clarifying_question="Which metric should I use?",
    )
    empty_result = AnswerResult(
        status="answerable",
        answer="No rows matched.",
        explanation="",
        rows=[],
    )

    assert evaluate_result(ambiguous, ambiguous_result, {})[0]
    assert evaluate_result(empty, empty_result, {})[0]


def test_report_includes_sql_query_id_categories_and_failure_analysis() -> None:
    """Include per-question evidence, held-out accuracy, and failure details."""
    question = {
        "id": "sample",
        "category": "filter",
        "question": "How many clients?",
        "held_out": True,
    }
    record = EvaluationRecord(
        question=question,
        passed=False,
        expected="numeric=5",
        actual="answer='There are 3.'",
        query_id="query-abc",
        sql="SELECT COUNT(*) FROM BANK_MARKETING",
        failure_reason="Numeric result differs.",
    )

    report = render_report([record], tolerance=0.01)

    assert "Held-out accuracy: **0/1 (0.0%)**" in report
    assert "filter" in report
    assert "query-abc" in report
    assert "SELECT COUNT(*) FROM BANK_MARKETING" in report
    assert "## Failure analysis" in report
    assert "Numeric result differs." in report


def test_run_evaluation_records_pipeline_exceptions() -> None:
    """Turn a question-level pipeline error into an explicit failed row."""

    class BrokenPipeline:
        def ask(self, _question: str) -> AnswerResult:
            raise RuntimeError("service is unavailable")

    question = {
        "id": "broken",
        "category": "unsupported",
        "question": "Predict outcomes.",
        "expected_behavior": {"status": "unsupported"},
        "how_expected_computed": "Predictions are unavailable.",
    }

    records = run_evaluation([question], BrokenPipeline(), {})

    assert len(records) == 1
    assert not records[0].passed
    assert "service is unavailable" in records[0].actual
    assert records[0].query_id == "—"


def test_cli_writes_report_and_prints_accuracy_on_pipeline_setup_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Write a usable failure report and print accuracy when setup fails."""

    class UnavailablePipeline:
        def __init__(self, **_kwargs: object) -> None:
            raise RuntimeError("Gemma is unavailable")

    monkeypatch.setattr("eval.run_eval.Pipeline", UnavailablePipeline)
    report_path = tmp_path / "results.md"
    csv_path = write_bank_csv(tmp_path / "bank-full.csv")
    manifest_path = Path(__file__).resolve().parents[1] / "eval" / "questions.yaml"

    exit_code = run_eval_main(
        [
            "--csv",
            str(csv_path),
            "--questions",
            str(manifest_path),
            "--report",
            str(report_path),
        ]
    )

    output = capsys.readouterr().out
    report = report_path.read_text(encoding="utf-8")
    assert exit_code == 1
    assert "Overall accuracy: 0/20 (0.0%)" in output
    assert "Held-out accuracy: 0/5 (0.0%)" in output
    assert "pipeline setup error: RuntimeError: Gemma is unavailable" in report
