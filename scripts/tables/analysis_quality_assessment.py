"""
Analysis: Simplified Quality Assessment (Checklist #8)

Adapted from CLAIM checklist, scoring each paper on:
  - Reporting quality (0-3): PSNR reported, SSIM reported, other metrics reported
  - Validation quality (0-3): clinical validation, multi-reader/prospective, clinical/mixed dataset
  - Reproducibility (0-3): code available, public benchmark data, architecture specifics described
  - Total: 0-9
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root

np.random.seed(42)


def analyze_quality_assessment():
    df = load_data()

    # --- Reporting quality (0-3) ---
    df["QA_PSNR"] = df["PSNR_Numeric"].notna().astype(int)
    df["QA_SSIM"] = df["SSIM_Numeric"].notna().astype(int)
    df["QA_OtherMetrics"] = (
        df["Other_Metrics"].notna()
        & (df["Other_Metrics"].str.strip() != "")
        & (~df["Other_Metrics"].str.lower().isin(["n/a", "na", "not reported", "none"]))
    ).astype(int)
    df["Reporting_Quality"] = df["QA_PSNR"] + df["QA_SSIM"] + df["QA_OtherMetrics"]

    # --- Validation quality (0-3) ---
    df["QA_ClinVal"] = (df["Clinical_Validation_Norm"] != "None").astype(int)
    df["QA_MultiReader"] = df["Clinical_Validation_Norm"].isin(
        ["Multi-reader", "Prospective validation"]
    ).astype(int)
    df["QA_ClinicalDataset"] = df["Dataset_Type_Norm"].isin(
        ["Clinical", "Mixed"]
    ).astype(int)
    df["Validation_Quality"] = df["QA_ClinVal"] + df["QA_MultiReader"] + df["QA_ClinicalDataset"]

    # --- Reproducibility (0-3) ---
    df["QA_Code"] = (df["Code_Available_Norm"] == "Yes").astype(int)
    df["QA_PublicData"] = (df["Dataset_Type_Norm"] == "Public benchmark").astype(int)
    df["QA_ArchDescribed"] = (
        df["Architecture_Specifics"].notna()
        & (df["Architecture_Specifics"].str.strip() != "")
        & (~df["Architecture_Specifics"].str.lower().isin(["n/a", "na", "not reported", "none"]))
    ).astype(int)
    df["Reproducibility"] = df["QA_Code"] + df["QA_PublicData"] + df["QA_ArchDescribed"]

    # --- Total quality score (0-9) ---
    df["Quality_Total"] = df["Reporting_Quality"] + df["Validation_Quality"] + df["Reproducibility"]

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
    df[per_paper_cols].to_csv(out_dir / "analysis_quality_assessment.csv", index=False)

    # Save summary
    summary_rows = []
    for domain, col in [("Reporting Quality", "Reporting_Quality"),
                        ("Validation Quality", "Validation_Quality"),
                        ("Reproducibility", "Reproducibility"),
                        ("Total Quality", "Quality_Total")]:
        summary_rows.append({
            "Domain": domain,
            "Max_Possible": 3 if col != "Quality_Total" else 9,
            "Mean": df[col].mean(),
            "Median": df[col].median(),
            "Std": df[col].std(),
            "Min": df[col].min(),
            "Max": df[col].max(),
        })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out_dir / "analysis_quality_summary.csv", index=False)

    # Print summary
    print("\n=== Quality Assessment Analysis ===\n")
    print(f"  Total papers assessed: {len(df)}")
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
        n = (df["Quality_Total"] == score).sum()
        if n > 0:
            print(f"    Score {score}: {n} papers ({n/len(df)*100:.1f}%)")

    print(f"\n  Saved: {out_dir / 'analysis_quality_assessment.csv'}")
    print(f"  Saved: {out_dir / 'analysis_quality_summary.csv'}")
    return df[per_paper_cols]


if __name__ == "__main__":
    analyze_quality_assessment()
