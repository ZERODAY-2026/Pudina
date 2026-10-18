"""Run dataset questions through DataMind and report ground-truth accuracy."""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from eval.compute_ground_truth import compute_ground_truth, default_csv_path
from src.pipeline import AnswerResult, Pipeline


_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")
_VALID_CATEGORIES = {
    "simple_aggregate",
    "filter",
    "join",
    "multi_step",
    "ambiguous",
    "empty_result",
    "unsupported",
}


@dataclass
class EvaluationRecord:
    """Outcome of one manifest question."""

    question: dict[str, Any]
    passed: bool
    expected: str
    actual: str
    query_id: str
    sql: str
    failure_reason: str = ""


def load_questions(path: str | Path) -> list[dict[str, Any]]:
    """Load and structurally validate the YAML evaluation manifest."""
    manifest_path = Path(path)
    try:
        with manifest_path.open(encoding="utf-8") as manifest:
            questions = yaml.safe_load(manifest)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not load evaluation questions '{manifest_path}': {exc}") from exc

    if not isinstance(questions, list) or len(questions) != 20:
        raise ValueError("The evaluation manifest must contain exactly 20 questions.")
    identifiers: set[str] = set()
    held_out_count = 0
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Every evaluation question must be a mapping.")
        required = {"id", "category", "question", "how_expected_computed"}
        missing = required - question.keys()
        if missing:
            raise ValueError(f"Evaluation question is missing fields: {sorted(missing)}")
        if not isinstance(question["id"], str) or not question["id"].strip():
            raise ValueError("Every evaluation question id must be a non-empty string.")
        if (
            not isinstance(question["category"], str)
            or question["category"] not in _VALID_CATEGORIES
        ):
            raise ValueError(f"Unknown evaluation category: {question['category']}")
        if not all(
            isinstance(question[field], str) and question[field].strip()
            for field in ("question", "how_expected_computed")
        ):
            raise ValueError(
                f"{question['id']} must have a question and calculation explanation."
            )
        if ("expected_answer" in question) == ("expected_behavior" in question):
            raise ValueError(
                f"{question['id']} must define exactly one expected_answer or expected_behavior."
            )
        if question["id"] in identifiers:
            raise ValueError(f"Duplicate evaluation question id: {question['id']}")
        if "expected_answer" in question:
            expected_answer = question["expected_answer"]
            if (
                not isinstance(expected_answer, dict)
                or expected_answer.get("type") not in {"numeric", "string"}
                or not isinstance(expected_answer.get("ground_truth_key"), str)
            ):
                raise ValueError(
                    f"{question['id']} must define a numeric or string "
                    "ground_truth_key in expected_answer."
                )
        else:
            expected_behavior = question["expected_behavior"]
            if (
                not isinstance(expected_behavior, dict)
                or expected_behavior.get("status")
                not in {"answerable", "ambiguous", "unsupported"}
                or (
                    expected_behavior.get("no_rows") is not True
                    and not isinstance(expected_behavior.get("contains"), str)
                )
            ):
                raise ValueError(
                    f"{question['id']} must define an expected status and "
                    "either no_rows or a response phrase."
                )
        held_out = question.get("held_out", False)
        if not isinstance(held_out, bool):
            raise ValueError(f"{question['id']} held_out must be a boolean.")
        identifiers.add(question["id"])
        held_out_count += held_out
    if held_out_count != 5:
        raise ValueError("Exactly five evaluation questions must be held out.")
    return questions


def evaluate_result(
    question: dict[str, Any],
    result: AnswerResult,
    ground_truth: dict[str, int | float | str],
    numeric_tolerance: float = 0.01,
) -> tuple[bool, str, str, str]:
    """Compare one pipeline result against its CSV-derived target."""
    if "expected_behavior" in question:
        expected_behavior = question["expected_behavior"]
        expected_status = expected_behavior["status"]
        expected = f"status={expected_status}"
        if expected_behavior.get("no_rows"):
            expected += ", no rows"
            passed = result.status == expected_status and not result.rows
        else:
            phrase = str(expected_behavior.get("contains", "")).casefold()
            expected += f", response contains {phrase!r}"
            passed = (
                result.status == expected_status
                and phrase in result.answer.casefold()
            )
        actual = (
            f"status={result.status}, answer={result.answer!r}, "
            f"row_count={len(result.rows)}"
        )
        reason = "" if passed else "Expected behavior/status was not met."
        return passed, expected, actual, reason

    target_spec = question["expected_answer"]
    key = target_spec["ground_truth_key"]
    if key not in ground_truth:
        raise ValueError(f"No computed ground truth for key '{key}'.")
    expected_value = ground_truth[key]
    expected_type = target_spec["type"]
    expected = f"{expected_type}={expected_value}"
    if result.status != "answerable":
        actual = f"status={result.status}, answer={result.answer!r}"
        return False, expected, actual, "Expected an answerable result."

    if expected_type == "numeric":
        if not isinstance(expected_value, (int, float)):
            raise ValueError(f"Ground-truth value '{key}' is not numeric.")
        actual_numbers = _numbers_in(result.answer)
        passed = any(
            math.isclose(
                value,
                float(expected_value),
                rel_tol=numeric_tolerance,
                abs_tol=numeric_tolerance,
            )
            for value in actual_numbers
        )
        reason = (
            ""
            if passed
            else "Answer did not contain the CSV-derived numeric target "
            f"within tolerance {numeric_tolerance}."
        )
        actual = f"answer={result.answer!r}, rows={result.rows!r}"
        return passed, expected, actual, reason

    if expected_type == "string":
        if not isinstance(expected_value, str):
            raise ValueError(f"Ground-truth value '{key}' is not a string.")
        expected_string = expected_value.casefold()
        row_values = " ".join(str(value) for row in result.rows for value in row)
        passed = (
            expected_string in result.answer.casefold()
            or expected_string in row_values.casefold()
        )
        reason = "" if passed else "Answer and result rows omit the expected string."
        actual = f"answer={result.answer!r}, rows={result.rows!r}"
        return passed, expected, actual, reason

    raise ValueError(f"Unsupported expected answer type: {expected_type}")


def run_evaluation(
    questions: list[dict[str, Any]],
    pipeline: Pipeline,
    ground_truth: dict[str, int | float | str],
    numeric_tolerance: float = 0.01,
) -> list[EvaluationRecord]:
    """Run each question independently through the configured pipeline."""
    records: list[EvaluationRecord] = []
    for question in questions:
        try:
            result = pipeline.ask(question["question"])
            passed, expected, actual, reason = evaluate_result(
                question,
                result,
                ground_truth,
                numeric_tolerance,
            )
        except Exception as exc:
            result = None
            passed = False
            expected = _expected_summary(question, ground_truth)
            actual = f"evaluation error: {type(exc).__name__}: {exc}"
            reason = "Pipeline raised an exception."

        records.append(
            EvaluationRecord(
                question=question,
                passed=passed,
                expected=expected,
                actual=actual,
                query_id=result.query_id if result is not None and result.query_id else "—",
                sql=result.sql if result is not None and result.sql else "—",
                failure_reason=reason,
            )
        )
    return records


def _expected_summary(
    question: dict[str, Any],
    ground_truth: dict[str, int | float | str],
) -> str:
    """Format an expected result if evaluation fails before comparison."""
    if "expected_behavior" in question:
        return str(question["expected_behavior"])
    spec = question["expected_answer"]
    key = spec["ground_truth_key"]
    return f"{spec['type']}={ground_truth.get(key, 'missing')}"


def _numbers_in(text: str) -> list[float]:
    """Extract numeric tokens from a generated answer."""
    values = []
    for match in _NUMBER.finditer(text):
        try:
            values.append(float(match.group().replace(",", "")))
        except ValueError:
            continue
    return values


def _accuracy(records: list[EvaluationRecord]) -> tuple[int, int, float]:
    """Calculate passed count, total count, and percentage."""
    passed = sum(record.passed for record in records)
    total = len(records)
    return passed, total, (passed / total * 100) if total else 0.0


def render_report(records: list[EvaluationRecord], tolerance: float) -> str:
    """Render per-question outcomes, accuracy summaries, and failure analysis."""
    passed, total, overall = _accuracy(records)
    held_out = [
        record for record in records if record.question.get("held_out", False)
    ]
    held_passed, held_total, held_accuracy = _accuracy(held_out)
    lines = [
        "# DataMind Evaluation Results",
        "",
        f"- Overall accuracy: **{passed}/{total} ({overall:.1f}%)**",
        f"- Held-out accuracy: **{held_passed}/{held_total} ({held_accuracy:.1f}%)**",
        f"- Numeric tolerance: `{tolerance}` (relative and absolute)",
        "",
        "## Accuracy by category",
        "",
        "| Category | Passed | Total | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    categories = sorted({record.question["category"] for record in records})
    for category in categories:
        category_records = [
            record for record in records if record.question["category"] == category
        ]
        category_passed, category_total, category_accuracy = _accuracy(category_records)
        lines.append(
            f"| {category} | {category_passed} | {category_total} | "
            f"{category_accuracy:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Held-out accuracy by category",
            "",
            "| Category | Passed | Total | Accuracy |",
            "|---|---:|---:|---:|",
        ]
    )
    for category in sorted({record.question["category"] for record in held_out}):
        category_records = [
            record
            for record in held_out
            if record.question["category"] == category
        ]
        category_passed, category_total, category_accuracy = _accuracy(category_records)
        lines.append(
            f"| {category} | {category_passed} | {category_total} | "
            f"{category_accuracy:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Per-question results",
            "",
            "| Result | ID | Category | Split | Question | Expected | Actual | Query ID | SQL |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for record in records:
        question = record.question
        split = "held-out" if question.get("held_out", False) else "development"
        sql = record.sql.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {'PASS' if record.passed else 'FAIL'} | {question['id']} | "
            f"{question['category']} | {split} | "
            f"{_cell(question['question'])} | {_cell(record.expected)} | "
            f"{_cell(record.actual)} | {_cell(record.query_id)} | `{sql}` |"
        )

    failures = [record for record in records if not record.passed]
    lines.extend(["", "## Failure analysis", ""])
    if failures:
        for record in failures:
            lines.append(
                f"- **{record.question['id']} ({record.question['category']})**: "
                f"{record.failure_reason} Expected {record.expected}; "
                f"observed {record.actual}."
            )
    else:
        lines.append("No failures.")
    return "\n".join(lines) + "\n"


def _cell(value: object) -> str:
    """Escape Markdown table-cell control characters."""
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", "")


def main(argv: Sequence[str] | None = None) -> int:
    """Compute CSV ground truth, run all questions, and write the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=default_csv_path(),
        help="Path to UCI bank-full.csv.",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=REPOSITORY_ROOT / "eval" / "questions.yaml",
        help="Evaluation manifest path.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "config" / "dataset_a.yaml",
        help="Dataset configuration path used by the pipeline.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPOSITORY_ROOT / "eval" / "results.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Relative and absolute tolerance for numeric answers (default: 0.01).",
    )
    args = parser.parse_args(argv)
    if args.tolerance < 0:
        parser.error("--tolerance must not be negative")

    try:
        questions = load_questions(args.questions)
        ground_truth = compute_ground_truth(args.csv)
    except (OSError, ValueError) as exc:
        print(f"Evaluation setup failed: {exc}", file=sys.stderr)
        return 2

    try:
        pipeline = Pipeline(config_path=args.config)
    except Exception as exc:
        records = [
            EvaluationRecord(
                question=question,
                passed=False,
                expected=_expected_summary(question, ground_truth),
                actual=f"pipeline setup error: {type(exc).__name__}: {exc}",
                query_id="—",
                sql="—",
                failure_reason="Pipeline could not be initialized.",
            )
            for question in questions
        ]
    else:
        records = run_evaluation(questions, pipeline, ground_truth, args.tolerance)

    report = render_report(records, args.tolerance)
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    except OSError as exc:
        print(f"Could not write evaluation report '{args.report}': {exc}", file=sys.stderr)
        return 2

    passed, total, accuracy = _accuracy(records)
    held_out = [
        record for record in records if record.question.get("held_out", False)
    ]
    held_passed, held_total, held_accuracy = _accuracy(held_out)
    print(f"Overall accuracy: {passed}/{total} ({accuracy:.1f}%)")
    print(
        f"Held-out accuracy: {held_passed}/{held_total} "
        f"({held_accuracy:.1f}%)"
    )
    print(f"Report written to {args.report}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
