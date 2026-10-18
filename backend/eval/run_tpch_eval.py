"""Evaluate TPC-H questions through the real FastAPI ask endpoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from fastapi.testclient import TestClient

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from eval.compute_tpch_ground_truth import (
    TPCH_GROUND_TRUTH_SQL,
    compute_tpch_ground_truth,
)
from eval.run_eval import (
    EvaluationRecord,
    evaluate_result,
    load_questions,
    render_report,
)
from src.api import AskResponse, create_app
from src.pipeline import AnswerResult


_DATASET_ID = "tpc-h-sf1"
_MANIFEST = REPOSITORY_ROOT / "eval" / "questions_tpch.yaml"
_REPORT = REPOSITORY_ROOT / "eval" / "results_tpch.md"


def _answer_result(response: AskResponse) -> AnswerResult:
    """Adapt the public API status and evidence to the shared evaluator."""
    status_map = {
        "answered": "answerable",
        "empty": "answerable",
        "clarify": "ambiguous",
        "unsupported": "unsupported",
        "error": "error",
    }
    return AnswerResult(
        status=status_map[response.status],
        answer=response.answer or "",
        explanation=response.explanation or "",
        assumptions=response.assumptions,
        sql=response.sql,
        columns=response.columns,
        rows=[tuple(row) for row in response.rows],
        query_id=response.query_id,
        clarifying_question=response.clarifying_question,
    )


def _report_ground_truth_queries(
    evidence: list[dict[str, Any]],
) -> str:
    """Append the independent SQL targets and their Snowflake evidence."""
    lines = [
        "",
        "## Independent SQL ground truth",
        "",
        "These expected values were queried directly through the reader client, "
        "not through the NL pipeline.",
        "",
        "| ID | Expected rows | Query ID | Hand-written SQL |",
        "|---|---|---|---|",
    ]
    for item in evidence:
        sql = str(item["sql"]).replace("|", "\\|").replace("\n", " ")
        rows = str(item["rows"]).replace("|", "\\|")
        lines.append(
            f"| {item['id']} | {rows} | {item['query_id']} | `{sql}` |"
        )
    return "\n".join(lines) + "\n"


def _setup_failure_report(error: BaseException) -> str:
    """Explain that independent targets were unavailable without leaking details."""
    lines = [
        "# TPC-H SF1 Evaluation Results",
        "",
        "- Overall accuracy: **0/0 (N/A)**",
        "- Evaluation status: **not run**",
        "",
        "Independent SQL ground truth could not be collected, so no expected "
        "values or pipeline accuracy are claimed. Check reader-role Snowflake "
        "connectivity and SELECT access to `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1`.",
        "",
        f"Failure type: `{type(error).__name__}`",
        "",
        "Hand-written expected-answer SQL is defined in "
        "`eval/compute_tpch_ground_truth.py`.",
        "",
    ]
    return "\n".join(lines)


def run_tpch_evaluation(
    questions_path: Path = _MANIFEST,
    report_path: Path = _REPORT,
) -> tuple[list[EvaluationRecord], list[dict[str, Any]]]:
    """Collect direct SQL targets, then grade actual POST /api/ask responses."""
    questions = load_questions(questions_path)
    ground_truth, evidence = compute_tpch_ground_truth()
    records: list[EvaluationRecord] = []
    with TestClient(create_app()) as client:
        for question in questions:
            result: AnswerResult | None = None
            try:
                response = client.post(
                    "/api/ask",
                    json={
                        "question": question["question"],
                        "dataset": _DATASET_ID,
                        "history": question.get("history", []),
                    },
                )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"/api/ask returned HTTP {response.status_code}: "
                        f"{response.json()}"
                    )
                result = _answer_result(AskResponse.model_validate(response.json()))
                passed, expected, actual, reason = evaluate_result(
                    question,
                    result,
                    ground_truth,
                )
            except Exception as exc:
                passed = False
                expected_spec = question.get("expected_answer", {})
                key = expected_spec.get("ground_truth_key", question["id"])
                expected = (
                    f"{expected_spec.get('type', 'behavior')}="
                    f"{ground_truth.get(key, question.get('expected_behavior', 'unknown'))}"
                )
                actual = f"evaluation error: {type(exc).__name__}: {exc}"
                reason = "The API request or response could not be evaluated."

            records.append(
                EvaluationRecord(
                    question=question,
                    passed=passed,
                    expected=expected,
                    actual=actual,
                    query_id=(
                        result.query_id
                        if result is not None and result.query_id
                        else "—"
                    ),
                    sql=result.sql if result is not None and result.sql else "—",
                    failure_reason=reason,
                )
            )

    report = render_report(records, tolerance=0.01)
    report += _report_ground_truth_queries(evidence)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return records, evidence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the live TPC-H evaluation and write its evidence report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=_MANIFEST)
    parser.add_argument("--report", type=Path, default=_REPORT)
    args = parser.parse_args(argv)
    try:
        records, _evidence = run_tpch_evaluation(args.manifest, args.report)
    except Exception as exc:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(_setup_failure_report(exc), encoding="utf-8")
        except OSError as report_error:
            print(
                f"Could not write TPC-H report ({type(report_error).__name__}).",
                file=sys.stderr,
            )
        print(
            "TPC-H evaluation could not run. Verify Snowflake reader access to "
            "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1 and the configured Gemma backend.",
            file=sys.stderr,
        )
        return 2

    passed = sum(record.passed for record in records)
    print(f"TPC-H evaluation: {passed}/{len(records)} questions passed.")
    print(f"Report written to {args.report}")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
