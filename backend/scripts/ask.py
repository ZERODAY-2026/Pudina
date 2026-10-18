"""Answer one question or run five example questions through the pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from src.llm import GemmaClientError
from src.pipeline import AnswerResult, Pipeline
from src.snowflake_client import SnowflakeClientError


_DEMO_QUESTIONS = (
    "How many clients are in the dataset?",
    "How many clients subscribed to a term deposit?",
    "How many clients have a housing loan?",
    "What is the average age of clients?",
    "How many clients were contacted by cellular phone?",
)


def _print_result(question: str, result: AnswerResult) -> None:
    """Print an answer and the execution details required for verification."""
    print(f"\nQuestion: {question}")
    print(f"Status: {result.status}")
    print(f"Answer: {result.answer}")
    if result.clarifying_question:
        print(f"Clarifying question: {result.clarifying_question}")
    if result.sql:
        print(f"SQL: {result.sql}")
    print(f"Rows: {result.rows}")
    print(f"Query ID: {result.query_id}")
    print(f"Explanation: {result.explanation}")
    print(f"Assumptions: {result.assumptions}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one natural-language question or the five-question demo."""
    parser = argparse.ArgumentParser(
        description="Ask a question about the configured Snowflake dataset."
    )
    parser.add_argument("question", nargs="?", help="Question to answer.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/dataset_a.yaml"),
        help="Dataset YAML path (default: config/dataset_a.yaml).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run five example questions for the configured dataset.",
    )
    args = parser.parse_args(argv)
    if args.demo and args.question:
        parser.error("question cannot be supplied together with --demo")
    if not args.demo and not args.question:
        parser.error("provide a question or use --demo")

    try:
        pipeline = Pipeline(config_path=args.config)
        questions = _DEMO_QUESTIONS if args.demo else (args.question,)
        history: list[dict[str, str]] = []
        failed = False
        for question in questions:
            result = pipeline.ask(question, history=history)
            _print_result(question, result)
            failed = failed or result.status == "error"
            history.append({"question": question, "answer": result.answer})
        return 1 if failed else 0
    except (OSError, ValueError, GemmaClientError, SnowflakeClientError) as exc:
        print(f"Error answering question: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
