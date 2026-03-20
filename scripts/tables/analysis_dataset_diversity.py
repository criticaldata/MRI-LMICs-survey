"""
Analysis: Dataset Diversity (Checklist #38)

Count of dataset types and cross-tabulations with architecture and application.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root

np.random.seed(42)


def analyze_dataset_diversity():
    df = load_data()

    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Overall dataset type counts ---
    dt_counts = df["Dataset_Type_Norm"].value_counts()

    # --- Cross-tab: Dataset_Type_Norm x Architecture_Norm ---
    ct_arch = pd.crosstab(df["Dataset_Type_Norm"], df["Architecture_Norm"], margins=True)

    # --- Cross-tab: Dataset_Type_Norm x Application_Norm ---
    ct_app = pd.crosstab(df["Dataset_Type_Norm"], df["Application_Norm"], margins=True)

    # Combine into one CSV with labeled sections
    rows = []

    # Section 1: Overall counts
    rows.append({"Section": "Dataset Type Counts", "Row": "", "Column": "", "Value": ""})
    for dt, count in dt_counts.items():
        rows.append({
            "Section": "Dataset Type Counts",
            "Row": dt,
            "Column": "Count",
            "Value": count,
        })
        rows.append({
            "Section": "Dataset Type Counts",
            "Row": dt,
            "Column": "Percentage",
            "Value": f"{count / len(df) * 100:.1f}%",
        })

    # Section 2: Dataset x Architecture
    rows.append({"Section": "Dataset x Architecture", "Row": "", "Column": "", "Value": ""})
    for dt in ct_arch.index:
        for arch in ct_arch.columns:
            rows.append({
                "Section": "Dataset x Architecture",
                "Row": dt,
                "Column": arch,
                "Value": ct_arch.loc[dt, arch],
            })

    # Section 3: Dataset x Application
    rows.append({"Section": "Dataset x Application", "Row": "", "Column": "", "Value": ""})
    for dt in ct_app.index:
        for app in ct_app.columns:
            rows.append({
                "Section": "Dataset x Application",
                "Row": dt,
                "Column": app,
                "Value": ct_app.loc[dt, app],
            })

    result = pd.DataFrame(rows)
    result.to_csv(out_dir / "analysis_dataset_diversity.csv", index=False)

    # Print summary
    print("\n=== Dataset Diversity Analysis ===\n")
    n = len(df)
    print(f"  Total papers: {n}\n")

    print("  Dataset Type Distribution:")
    print(f"  {'Type':<20} {'N':>5} {'%':>8}")
    print(f"  {'-'*35}")
    for dt, count in dt_counts.items():
        print(f"  {dt:<20} {count:>5} {count/n*100:>7.1f}%")

    print(f"\n  Cross-tab: Dataset Type x Architecture")
    print(ct_arch.to_string())

    print(f"\n  Cross-tab: Dataset Type x Application")
    print(ct_app.to_string())

    print(f"\n  Saved: {out_dir / 'analysis_dataset_diversity.csv'}")
    return result


if __name__ == "__main__":
    analyze_dataset_diversity()
