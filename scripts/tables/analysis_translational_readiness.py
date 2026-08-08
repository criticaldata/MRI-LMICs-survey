"""Write the corrected five-criterion Translational Readiness analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))
sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root
from review_metrics import build_analysis

np.random.seed(42)


def analyze_translational_readiness():
    df = load_data()
    analysis = build_analysis(df)
    corrected = analysis["derived"]
    per_paper = analysis["tr"]

    # Save per-paper scores
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_paper.to_csv(out_dir / "analysis_translational_readiness.csv", index=False)

    # Summary by architecture
    arch_summary = (
        corrected.groupby("Architecture_Norm_Corrected")["TR_Score"]
        .agg(["count", "mean", "median", "min", "max"])
        .rename(columns={"count": "N"})
        .sort_values("mean", ascending=False)
    )

    # Summary by application
    app_summary = (
        corrected.groupby("Application_Norm")["TR_Score"]
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
    print(f"  Total papers: {len(corrected)}")
    print(f"  TR Score distribution:")
    for score in range(6):
        n = (corrected["TR_Score"] == score).sum()
        print(f"    Score {score}: {n} papers ({n/len(corrected)*100:.1f}%)")

    print(f"\n  Mean TR Score: {corrected['TR_Score'].mean():.2f}")
    print(f"  Median TR Score: {corrected['TR_Score'].median():.1f}")

    print(f"\n  Component breakdown:")
    tr_cols = ["TR_LowFieldDomain", "TR_OpenScience", "TR_ClinicalEvaluation", "TR_HardwareAwareness", "TR_DataDiversity"]
    for col in tr_cols:
        n_yes = corrected[col].sum()
        print(f"    {col:<24}: {n_yes} ({n_yes/len(corrected)*100:.1f}%)")

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
