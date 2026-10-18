"""Compute evaluation targets directly from the local Bank Marketing CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import pandas as pd


def default_csv_path() -> Path:
    """Find the conventional UCI bank-full.csv location under data/."""
    data_root = Path(__file__).resolve().parents[1] / "data"
    candidates = sorted(data_root.glob("**/bank-full.csv"))
    if candidates:
        return candidates[0]
    return data_root / "bank-marketing" / "bank+marketing" / "bank-full.csv"


def compute_ground_truth(csv_path: str | Path) -> dict[str, int | float | str]:
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

    return {
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
    args = parser.parse_args(argv)
    ground_truth = compute_ground_truth(args.csv)
    for key, value in ground_truth.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
