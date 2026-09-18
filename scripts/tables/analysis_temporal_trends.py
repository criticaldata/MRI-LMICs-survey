"""Temporal trend analysis with 2020-2024 primary and 2025 preliminary scopes."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

from mapper import get_project_root, load_data  # noqa: E402


PRIMARY_YEAR_START = 2020
PRIMARY_YEAR_END = 2024
PRELIMINARY_YEAR = 2025


def _summarize_years(df: pd.DataFrame, status: str) -> pd.DataFrame:
    """Summarize a specific year scope without mixing incomplete years."""
    rows = []
    for year in sorted(df["Year"].dropna().unique()):
        subset = df.loc[df["Year"] == year]
        n = len(subset)
        scored = subset.dropna(subset=["LMIC_Score"])
        rows.append(
            {
                "Year": int(year),
                "N_Papers": n,
                "LMIC_Score_Mean": scored["LMIC_Score"].mean() if len(scored) else None,
                "LMIC_Score_Median": scored["LMIC_Score"].median() if len(scored) else None,
                "Pct_Low_Field": (subset["Low_Field_Norm"] == "Yes").sum() / n * 100 if n else 0,
                "Pct_Code_Available": (subset["Code_Available_Norm"] == "Yes").sum() / n * 100 if n else 0,
                "Pct_Clinical_Validation": (subset["Clinical_Validation_Norm"] != "None").sum() / n * 100 if n else 0,
                "Status": status,
            }
        )
    return pd.DataFrame(rows)


def build_temporal_trends(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return primary full-year results and the separately labelled 2025 snapshot."""
    primary = _summarize_years(
        df.loc[df["Year"].between(PRIMARY_YEAR_START, PRIMARY_YEAR_END)].copy(),
        "Primary full-year analysis",
    )
    preliminary = _summarize_years(
        df.loc[df["Year"] == PRELIMINARY_YEAR].copy(),
        "Preliminary and incomplete",
    )
    return primary, preliminary


def analyze_temporal_trends() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write the reviewer-safe temporal outputs without deleting 2025 evidence."""
    primary, preliminary = build_temporal_trends(load_data())
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    primary_path = out_dir / "analysis_temporal_trends.csv"
    preliminary_path = out_dir / "analysis_temporal_trends_2025_preliminary.csv"
    primary.to_csv(primary_path, index=False)
    preliminary.to_csv(preliminary_path, index=False)
    print("=== Temporal Trends Analysis ===")
    print(f"Primary full-year scope: {PRIMARY_YEAR_START}-{PRIMARY_YEAR_END}; papers={int(primary['N_Papers'].sum())}")
    print(f"Preliminary {PRELIMINARY_YEAR} scope: papers={int(preliminary['N_Papers'].sum())}")
    print(f"Saved primary: {primary_path}")
    print(f"Saved preliminary: {preliminary_path}")
    return primary, preliminary


if __name__ == "__main__":
    analyze_temporal_trends()
