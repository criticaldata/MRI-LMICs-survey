"""
Analysis: Temporal Trends (Checklist #36)

Year-by-year breakdown of LMIC scores, % low-field, % code available,
and % clinical validation per year.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root

np.random.seed(42)


def analyze_temporal_trends():
    df = load_data()

    # Group by year
    years = sorted(df["Year"].dropna().unique())
    rows = []

    for year in years:
        subset = df[df["Year"] == year]
        n = len(subset)
        scored = subset.dropna(subset=["LMIC_Score"])

        row = {
            "Year": int(year),
            "N_Papers": n,
            "LMIC_Score_Mean": scored["LMIC_Score"].mean() if len(scored) > 0 else np.nan,
            "LMIC_Score_Median": scored["LMIC_Score"].median() if len(scored) > 0 else np.nan,
            "Pct_Low_Field": (subset["Low_Field_Norm"] == "Yes").sum() / n * 100 if n > 0 else 0,
            "Pct_Code_Available": (subset["Code_Available_Norm"] == "Yes").sum() / n * 100 if n > 0 else 0,
            "Pct_Clinical_Validation": (subset["Clinical_Validation_Norm"] != "None").sum() / n * 100 if n > 0 else 0,
        }
        rows.append(row)

    result = pd.DataFrame(rows)

    # Save
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_dir / "analysis_temporal_trends.csv", index=False)

    # Print summary
    print("\n=== Temporal Trends Analysis ===\n")
    print(f"  Year range: {int(years[0])}–{int(years[-1])}")
    print(f"  Total papers: {len(df)}")
    print()
    print(f"  {'Year':<8} {'N':>4} {'LMIC Mean':>10} {'LMIC Med':>10} {'%LowField':>10} {'%Code':>8} {'%ClinVal':>10}")
    print(f"  {'-'*62}")
    for _, row in result.iterrows():
        print(
            f"  {int(row['Year']):<8} {int(row['N_Papers']):>4} "
            f"{row['LMIC_Score_Mean']:>10.2f} {row['LMIC_Score_Median']:>10.1f} "
            f"{row['Pct_Low_Field']:>10.1f} {row['Pct_Code_Available']:>8.1f} "
            f"{row['Pct_Clinical_Validation']:>10.1f}"
        )

    print(f"\n  Saved: {out_dir / 'analysis_temporal_trends.csv'}")
    return result


if __name__ == "__main__":
    analyze_temporal_trends()
