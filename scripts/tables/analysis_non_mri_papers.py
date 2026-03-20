"""
Analysis: Non-MRI Papers Flagging (Checklist #13)

Identify papers where Application_Norm == "Non-MRI" and recommend exclusion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import numpy as np
import pandas as pd
from mapper import load_data, get_project_root

np.random.seed(42)


def analyze_non_mri_papers():
    df = load_data()

    # Filter non-MRI papers
    non_mri = df[df["Application_Norm"] == "Non-MRI"].copy()

    # Build output
    result = non_mri[["Paper_ID", "Title", "Year", "MRI_Application_Area",
                       "Application_Norm", "Architecture_Norm"]].copy()
    result["Recommendation"] = "Exclude – not MRI modality"

    # Save
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_dir / "analysis_non_mri_papers.csv", index=False)

    # Print summary
    print("\n=== Non-MRI Papers Analysis ===\n")
    print(f"  Total papers: {len(df)}")
    print(f"  Non-MRI papers identified: {len(non_mri)}")
    print()

    if len(non_mri) > 0:
        print(f"  {'Paper_ID':<12} {'Year':>6}  Title")
        print(f"  {'-'*70}")
        for _, row in result.iterrows():
            title = row["Title"][:55] + "..." if len(str(row["Title"])) > 55 else row["Title"]
            print(f"  {row['Paper_ID']:<12} {int(row['Year']):>6}  {title}")

        print(f"\n  Original application labels:")
        for _, row in result.iterrows():
            print(f"    {row['Paper_ID']}: {row['MRI_Application_Area']}")

        print(f"\n  Recommendation: Exclude {len(non_mri)} non-MRI papers from main analysis.")
    else:
        print("  No non-MRI papers found.")

    print(f"\n  Saved: {out_dir / 'analysis_non_mri_papers.csv'}")
    return result


if __name__ == "__main__":
    analyze_non_mri_papers()
