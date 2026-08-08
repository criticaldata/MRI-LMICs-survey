"""Write the quality assessment from the frozen source using shared logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))
sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root
from review_metrics import build_analysis

np.random.seed(42)


def analyze_quality_assessment():
    df = load_data()
    analysis = build_analysis(df)
    derived = analysis["derived"]
    scored = analysis["quality"]

    # Save per-paper scores
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_paper_cols = [
        "Paper_ID", "Title", "Year",
        "QA_PSNR", "QA_SSIM", "QA_OtherMetrics", "Reporting_Quality",
        "QA_ClinVal", "QA_MultiReader", "QA_ClinicalDataset", "Validation_Quality",
        "QA_Code", "QA_PublicData", "QA_ArchDescribed", "Reproducibility",
        "Quality_Total",
    ]
    scored[per_paper_cols].to_csv(out_dir / "analysis_quality_assessment.csv", index=False)

    summary = analysis["quality_summary"]
    summary.to_csv(out_dir / "analysis_quality_summary.csv", index=False)

    # Print summary
    print("\n=== Quality Assessment Analysis ===\n")
    print(f"  Total papers assessed: {len(derived)}")
    print()
    print(f"  {'Domain':<25} {'Max':>4} {'Mean':>6} {'Med':>5} {'Std':>6} {'Min':>4} {'Max':>4}")
    print(f"  {'-'*56}")
    for _, row in summary.iterrows():
        print(
            f"  {row['Domain']:<25} {int(row['Max_Possible']):>4} "
            f"{row['Mean']:>6.2f} {row['Median']:>5.1f} {row['Std']:>6.2f} "
            f"{int(row['Min']):>4} {int(row['Max']):>4}"
        )

    print(f"\n  Total Quality Score distribution:")
    for score in range(10):
        n = (scored["Quality_Total"] == score).sum()
        if n > 0:
            print(f"    Score {score}: {n} papers ({n/len(derived)*100:.1f}%)")

    print(f"\n  Saved: {out_dir / 'analysis_quality_assessment.csv'}")
    print(f"  Saved: {out_dir / 'analysis_quality_summary.csv'}")
    return scored[per_paper_cols]


if __name__ == "__main__":
    analyze_quality_assessment()
