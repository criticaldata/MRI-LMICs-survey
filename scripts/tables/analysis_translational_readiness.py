"""
Analysis: Translational Readiness Score (Checklist #33, #39)

Composite 0-5 score per paper based on LMIC relevance, low-field mention,
code availability, clinical validation, and resource constraints.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root

np.random.seed(42)


def analyze_translational_readiness():
    df = load_data()

    # Compute component scores (each 0 or 1)
    df["TR_LMIC"] = (df["LMIC_Score"] >= 4).astype(int)
    df["TR_LowField"] = (df["Low_Field_Norm"] == "Yes").astype(int)
    df["TR_Code"] = (df["Code_Available_Norm"] == "Yes").astype(int)
    df["TR_ClinicalVal"] = (df["Clinical_Validation_Norm"] != "None").astype(int)
    df["TR_Resource"] = (df["Resource_Constraints_Norm"] == "Yes").astype(int)

    # Total Translational Readiness Score (0-5)
    tr_cols = ["TR_LMIC", "TR_LowField", "TR_Code", "TR_ClinicalVal", "TR_Resource"]
    df["TR_Score"] = df[tr_cols].sum(axis=1)

    # Save per-paper scores
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_paper = df[["Paper_ID", "Title", "Year", "Architecture_Norm", "Application_Norm"]
                   + tr_cols + ["TR_Score"]].copy()
    per_paper.to_csv(out_dir / "analysis_translational_readiness.csv", index=False)

    # Summary by architecture
    arch_summary = (
        df.groupby("Architecture_Norm")["TR_Score"]
        .agg(["count", "mean", "median", "min", "max"])
        .rename(columns={"count": "N"})
        .sort_values("mean", ascending=False)
    )

    # Summary by application
    app_summary = (
        df.groupby("Application_Norm")["TR_Score"]
        .agg(["count", "mean", "median", "min", "max"])
        .rename(columns={"count": "N"})
        .sort_values("mean", ascending=False)
    )

    # Combine and save
    combined = pd.concat(
        [arch_summary.assign(Group_Type="Architecture"),
         app_summary.assign(Group_Type="Application")],
    )
    combined.index.name = "Group"
    combined.to_csv(out_dir / "analysis_tr_by_architecture.csv")

    # Print summary
    print("\n=== Translational Readiness Score Analysis ===\n")
    print(f"  Total papers: {len(df)}")
    print(f"  TR Score distribution:")
    for score in range(6):
        n = (df["TR_Score"] == score).sum()
        print(f"    Score {score}: {n} papers ({n/len(df)*100:.1f}%)")

    print(f"\n  Mean TR Score: {df['TR_Score'].mean():.2f}")
    print(f"  Median TR Score: {df['TR_Score'].median():.1f}")

    print(f"\n  Component breakdown:")
    for col in tr_cols:
        n_yes = df[col].sum()
        print(f"    {col:<20}: {n_yes} ({n_yes/len(df)*100:.1f}%)")

    print(f"\n  By Architecture:")
    print(f"  {'Architecture':<20} {'N':>4} {'Mean':>6} {'Median':>8}")
    print(f"  {'-'*40}")
    for arch, row in arch_summary.iterrows():
        print(f"  {arch:<20} {int(row['N']):>4} {row['mean']:>6.2f} {row['median']:>8.1f}")

    print(f"\n  By Application:")
    print(f"  {'Application':<20} {'N':>4} {'Mean':>6} {'Median':>8}")
    print(f"  {'-'*40}")
    for app, row in app_summary.iterrows():
        print(f"  {app:<20} {int(row['N']):>4} {row['mean']:>6.2f} {row['median']:>8.1f}")

    print(f"\n  Saved: {out_dir / 'analysis_translational_readiness.csv'}")
    print(f"  Saved: {out_dir / 'analysis_tr_by_architecture.csv'}")
    return per_paper


if __name__ == "__main__":
    analyze_translational_readiness()
