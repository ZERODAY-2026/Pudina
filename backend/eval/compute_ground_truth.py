"""Compute evaluation targets directly from the local Bank Marketing CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml


def default_csv_path() -> Path:
    """Find the conventional UCI bank-full.csv location under data/."""
    data_root = Path(__file__).resolve().parents[1] / "data"
    candidates = sorted(data_root.glob("**/bank-full.csv"))
    if candidates:
        return candidates[0]
    return data_root / "bank-marketing" / "bank+marketing" / "bank-full.csv"


def compute_ground_truth(
    csv_path: str | Path,
    manifest_path: str | Path | None = None,
) -> dict[str, int | float | str | list[str]]:
    """Read the source CSV and compute all scalar targets with pandas."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Source CSV not found at '{path}'. Download bank-full.csv; "
            "see the README dataset instructions."
        )

    frame = pd.read_csv(path, sep=";")
    required_columns = {
        "age",
        "job",
        "housing",
        "duration",
        "campaign",
        "pdays",
        "contact",
        "month",
        "y",
    }
    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        raise ValueError(
            "The source CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    target = frame["y"].astype("string").str.casefold()
    housing = frame["housing"].astype("string").str.casefold()
    jobs = frame["job"].astype("string").str.casefold()
    contact = frame["contact"].astype("string").str.casefold()
    numeric_age = pd.to_numeric(frame["age"], errors="coerce")
    numeric_duration = pd.to_numeric(frame["duration"], errors="coerce")
    numeric_campaign = pd.to_numeric(frame["campaign"], errors="coerce")
    numeric_pdays = pd.to_numeric(frame["pdays"], errors="coerce")
    subscribed = target.eq("yes")

    monthly_subscriptions = (
        frame.loc[subscribed, "month"]
        .astype("string")
        .value_counts()
        .sort_index()
    )
    if monthly_subscriptions.empty:
        raise ValueError("No subscribed rows found; cannot compute top_subscription_month.")
    highest_month_count = monthly_subscriptions.max()
    top_month = str(
        sorted(monthly_subscriptions[monthly_subscriptions == highest_month_count].index)[0]
    )

    truth: dict[str, int | float | str | list[str]] = {
        "total_rows": int(len(frame)),
        "mean_age": float(numeric_age.mean()),
        "subscribed_count": int(subscribed.sum()),
        "mean_duration": float(numeric_duration.mean()),
        "housing_yes_count": int(housing.eq("yes").sum()),
        "admin_job_count": int(jobs.eq("admin.").sum()),
        "campaign_three_or_more_count": int(numeric_campaign.ge(3).sum()),
        "cellular_count": int(contact.eq("cellular").sum()),
        "not_previously_contacted_count": int(numeric_pdays.eq(999).sum()),
        "housing_subscribed_count": int((housing.eq("yes") & subscribed).sum()),
        "over_40_subscribed_count": int((numeric_age.gt(40) & subscribed).sum()),
        "top_subscription_month": top_month,
    }
    if manifest_path is not None:
        manifest = Path(manifest_path)
        try:
            with manifest.open(encoding="utf-8") as file:
                questions = yaml.safe_load(file)
        except (OSError, yaml.YAMLError) as exc:
            raise ValueError(f"Could not load evaluation manifest '{manifest}': {exc}") from exc
        if not isinstance(questions, list):
            raise ValueError("The evaluation manifest must contain a list of questions.")
        for question in questions:
            if not isinstance(question, dict) or "expected_answer" not in question:
                continue
            target_spec = question["expected_answer"]
            calculation = target_spec.get("calculation") if isinstance(target_spec, dict) else None
            if calculation is not None:
                if not isinstance(question.get("id"), str) or not isinstance(calculation, dict):
                    raise ValueError("Manifest calculation needs a question id and a mapping.")
                truth[question["id"]] = _compute_manifest_target(frame, calculation)
    return truth


def _compute_manifest_target(
    frame: pd.DataFrame, calculation: dict[str, Any]
) -> int | float | str | list[str]:
    """Evaluate a small, declarative pandas calculation from a manifest."""
    operation = calculation.get("operation")
    if operation in {"count", "mean", "percentage", "ratio"}:
        filters = calculation.get("filters", [])
        if not isinstance(filters, list):
            raise ValueError("Manifest calculation filters must be a list.")
        base_mask = _filter_mask(frame, filters)
        if operation == "count":
            return int(base_mask.sum())
        if operation == "mean":
            column = _manifest_column(frame, calculation.get("column"))
            values = pd.to_numeric(frame.loc[base_mask, column], errors="coerce")
            return float(values.mean())
        numerator_mask = base_mask & _filter_mask(
            frame, calculation.get("numerator_filters", [])
        )
        denominator_mask = base_mask & _filter_mask(
            frame, calculation.get("denominator_filters", [])
        )
        numerator = int(numerator_mask.sum())
        denominator = int(denominator_mask.sum())
        if denominator == 0:
            raise ValueError("Manifest percentage/ratio denominator is zero.")
        if operation == "ratio":
            return numerator / denominator
        return numerator / denominator * 100
    if operation == "top_groups":
        column = _manifest_column(frame, calculation.get("column"))
        limit = calculation.get("limit")
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("Manifest top_groups requires a positive integer limit.")
        mask = _filter_mask(frame, calculation.get("filters", []))
        counts = frame.loc[mask, column].astype("string").value_counts()
        ranked = sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
        return [str(value) for value, _count in ranked[:limit]]
    if operation == "top_rate_group":
        group_column = _manifest_column(frame, calculation.get("group_column"))
        outcome_column = _manifest_column(frame, calculation.get("outcome_column"))
        outcome_value = calculation.get("outcome_value")
        mask = _filter_mask(frame, calculation.get("filters", []))
        subset = frame.loc[mask, [group_column, outcome_column]].copy()
        subset[outcome_column] = (
            subset[outcome_column].astype("string").str.casefold()
        )
        rates = subset.assign(
            _success=subset[outcome_column].eq(str(outcome_value).casefold())
        ).groupby(group_column, dropna=False)["_success"].mean()
        if rates.empty:
            raise ValueError("Manifest top_rate_group has no groups to rank.")
        highest_rate = rates.max()
        return str(sorted(str(group) for group in rates[rates == highest_rate].index)[0])
    raise ValueError(f"Unsupported manifest calculation operation: {operation!r}")


def _manifest_column(frame: pd.DataFrame, column: object) -> str:
    """Validate a manifest column against the input data frame."""
    if not isinstance(column, str) or column not in frame.columns:
        raise ValueError(f"Manifest calculation references unknown column: {column!r}")
    return column


def _filter_mask(frame: pd.DataFrame, filters: object) -> pd.Series:
    """Build a conjunction of validated scalar comparisons using pandas."""
    if not isinstance(filters, list):
        raise ValueError("Manifest filter specification must be a list.")
    mask = pd.Series(True, index=frame.index)
    operators = {
        "eq": lambda series, value: series.eq(value),
        "ne": lambda series, value: series.ne(value),
        "gt": lambda series, value: pd.to_numeric(series, errors="coerce").gt(value),
        "ge": lambda series, value: pd.to_numeric(series, errors="coerce").ge(value),
        "lt": lambda series, value: pd.to_numeric(series, errors="coerce").lt(value),
        "le": lambda series, value: pd.to_numeric(series, errors="coerce").le(value),
    }
    for item in filters:
        if not isinstance(item, dict):
            raise ValueError("Every manifest filter must be a mapping.")
        column = _manifest_column(frame, item.get("column"))
        operator = item.get("operator")
        if operator not in operators:
            raise ValueError(f"Unsupported manifest filter operator: {operator!r}")
        mask &= operators[operator](frame[column], item.get("value"))
    return mask


def main(argv: Sequence[str] | None = None) -> int:
    """Print computed targets for a source CSV."""
    parser = argparse.ArgumentParser(
        description="Compute independent pandas ground truth for the eval dataset."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=default_csv_path(),
        help="Path to UCI bank-full.csv.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional evaluation manifest with declarative per-question calculations.",
    )
    args = parser.parse_args(argv)
    ground_truth = compute_ground_truth(args.csv, args.manifest)
    for key, value in ground_truth.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
