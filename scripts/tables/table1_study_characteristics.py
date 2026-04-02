"""
Table 1: Study Characteristics Overview

Generates a summary table of all 48 included studies, covering year range,
MRI application areas, field strength types, AI architectures, and dataset types.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
from mapper import load_data, get_project_root


def create_table1():
    df = load_data()
    n = len(df)

    rows = []

    # Total papers
    rows.append(("Total papers included", str(n), ""))

    # Year range
    year_min, year_max = df["Year"].min(), df["Year"].max()
    rows.append(("Publication year range", f"{year_min}\u2013{year_max}", ""))

    # Year distribution
    year_counts = df["Year"].value_counts().sort_index()
    for year, count in year_counts.items():
        rows.append((f"  {year}", str(count), f"{count/n*100:.1f}%"))

    rows.append(("", "", ""))

    # MRI Application Areas
    rows.append(("MRI Application Area", "n", "%"))
    app_counts = df["Application_Norm"].value_counts()
    for app, count in app_counts.items():
        rows.append((f"  {app}", str(count), f"{count/n*100:.1f}%"))

    rows.append(("", "", ""))

    # Field Strength
    rows.append(("Field Strength", "n", "%"))
    fs_counts = df["Field_Strength_Norm"].value_counts()
    for fs, count in fs_counts.items():
        rows.append((f"  {fs}", str(count), f"{count/n*100:.1f}%"))

    rows.append(("", "", ""))

    # Primary Focus
    rows.append(("Primary Focus", "n", "%"))
    pf_counts = df["Primary_Focus_Norm"].value_counts()
    for pf, count in pf_counts.items():
        rows.append((f"  {pf}", str(count), f"{count/n*100:.1f}%"))

    rows.append(("", "", ""))

    # AI Architecture
    rows.append(("AI Architecture", "n", "%"))
    arch_counts = df["Architecture_Norm"].value_counts()
    for arch, count in arch_counts.items():
        rows.append((f"  {arch}", str(count), f"{count/n*100:.1f}%"))

    rows.append(("", "", ""))

    # Dataset Type
    rows.append(("Dataset Type", "n", "%"))
    dt_counts = df["Dataset_Type_Norm"].value_counts()
    for dt, count in dt_counts.items():
        rows.append((f"  {dt}", str(count), f"{count/n*100:.1f}%"))

    rows.append(("", "", ""))

    # Clinical Validation
    has_validation = (df["Clinical_Validation_Norm"] != "None").sum()
    rows.append(("Clinical validation reported", str(has_validation), f"{has_validation/n*100:.1f}%"))

    # Code Availability
    code_yes = (df["Code_Available_Norm"] == "Yes").sum()
    rows.append(("Code publicly available", str(code_yes), f"{code_yes/n*100:.1f}%"))

    # Low-field mentioned
    lf_yes = (df["Low_Field_Norm"] == "Yes").sum()
    rows.append(("Low-field MRI mentioned", str(lf_yes), f"{lf_yes/n*100:.1f}%"))

    # Resource constraints
    rc_yes = (df["Resource_Constraints_Norm"] == "Yes").sum()
    rows.append(("Resource constraints addressed", str(rc_yes), f"{rc_yes/n*100:.1f}%"))

    result = pd.DataFrame(rows, columns=["Characteristic", "n", "%"])

    # Save
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_dir / "table1_study_characteristics.csv", index=False)

    # Print
    print("\n=== Table 1: Study Characteristics Overview ===\n")
    for _, row in result.iterrows():
        if row["Characteristic"] == "":
            print()
        elif row["n"] == "n":
            print(f"  {row['Characteristic']:<45} {'n':>5} {'%':>8}")
            print(f"  {'-'*60}")
        else:
            print(f"  {row['Characteristic']:<45} {row['n']:>5} {row['%']:>8}")

    return result


if __name__ == "__main__":
    create_table1()
