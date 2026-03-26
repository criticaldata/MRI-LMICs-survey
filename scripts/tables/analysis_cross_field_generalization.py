"""
Analysis: Cross-Field Generalization

Identifies papers that evaluate SR models across different MRI field strengths,
specifically those targeting low-field to high-field translation, which is a key
strategy for improving diagnostic quality in LMIC settings.

Three categories:
  1. True cross-field (low <-> high/standard): Field_Strength_Norm == "Low-field"
     OR (Field_Strength_Norm == "Mixed" AND Low_Field_Norm == "Yes")
  2. Multi-scanner standard (1.5T + 3T combos): Standard-field papers whose
     Field_Strength_Type text contains "and", "vs", or "+"
  3. Single field strength: all remaining papers
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
from mapper import load_data, get_project_root


def classify_field_category(row):
    """Return one of: 'True cross-field', 'Multi-scanner standard', 'Single field strength'."""
    fs_norm = str(row.get("Field_Strength_Norm", "")).strip()
    lf_norm = str(row.get("Low_Field_Norm", "")).strip()
    fs_type = str(row.get("Field_Strength_Type", "")).strip().lower()

    # True cross-field: low-field-involved papers
    if fs_norm == "Low-field":
        return "True cross-field"
    if fs_norm == "Mixed" and lf_norm == "Yes":
        return "True cross-field"

    # Multi-scanner standard: standard-field with multiple strengths in raw text
    if fs_norm == "Standard-field":
        if any(kw in fs_type for kw in ["and", "vs", "+"]):
            return "Multi-scanner standard"

    return "Single field strength"


def analyze_cross_field_generalization():
    df = load_data()

    df["Field_Category"] = df.apply(classify_field_category, axis=1)

    true_cross = df[df["Field_Category"] == "True cross-field"].copy()
    multi_std = df[df["Field_Category"] == "Multi-scanner standard"].copy()
    single = df[df["Field_Category"] == "Single field strength"].copy()

    # -----------------------------------------------------------------------
    # Print summary
    # -----------------------------------------------------------------------
    print("\n=== Cross-Field Generalization Analysis ===\n")
    print(f"  Total papers:                          {len(df)}")
    print(f"  True cross-field (low<->high):         {len(true_cross)}")
    print(f"  Multi-scanner standard (1.5T+3T):      {len(multi_std)}")
    print(f"  Single field strength:                 {len(single)}")
    print()

    # -----------------------------------------------------------------------
    # Detailed table: true cross-field papers
    # -----------------------------------------------------------------------
    print("  --- True Cross-Field Papers ---\n")
    cols_display = [
        "Paper_ID", "Year", "Field_Strength_Type", "Field_Strength_Norm",
        "Low_Field_Norm", "Architecture_Norm", "LMIC_Score",
    ]
    print(
        f"  {'ID':>4}  {'Year':>4}  {'FS_Norm':<16}  {'LF':>4}  {'Architecture':<18}  "
        f"{'LMIC':>4}  {'Field_Strength_Type'}"
    )
    print(f"  {'-'*90}")
    for _, row in true_cross.sort_values("Paper_ID").iterrows():
        print(
            f"  {int(row['Paper_ID']):>4}  {int(row['Year']):>4}  "
            f"{str(row['Field_Strength_Norm']):<16}  "
            f"{str(row['Low_Field_Norm']):>4}  "
            f"{str(row['Architecture_Norm']):<18}  "
            f"{str(row['LMIC_Score']):>4}  "
            f"{str(row['Field_Strength_Type'])}"
        )

    print()
    print("  --- Multi-Scanner Standard Papers ---\n")
    print(
        f"  {'ID':>4}  {'Year':>4}  {'FS_Norm':<16}  {'Architecture':<18}  "
        f"{'LMIC':>4}  {'Field_Strength_Type'}"
    )
    print(f"  {'-'*80}")
    for _, row in multi_std.sort_values("Paper_ID").iterrows():
        print(
            f"  {int(row['Paper_ID']):>4}  {int(row['Year']):>4}  "
            f"{str(row['Field_Strength_Norm']):<16}  "
            f"{str(row['Architecture_Norm']):<18}  "
            f"{str(row['LMIC_Score']):>4}  "
            f"{str(row['Field_Strength_Type'])}"
        )

    # -----------------------------------------------------------------------
    # LMIC score comparison across categories
    # -----------------------------------------------------------------------
    print()
    print("  --- LMIC Score by Category ---\n")
    print(f"  {'Category':<32}  {'N':>4}  {'Mean LMIC':>10}  {'Median LMIC':>12}")
    print(f"  {'-'*62}")
    for label, subset in [
        ("True cross-field", true_cross),
        ("Multi-scanner standard", multi_std),
        ("Single field strength", single),
    ]:
        scored = subset.dropna(subset=["LMIC_Score"])
        mean_v = scored["LMIC_Score"].mean() if len(scored) else float("nan")
        med_v = scored["LMIC_Score"].median() if len(scored) else float("nan")
        print(
            f"  {label:<32}  {len(subset):>4}  {mean_v:>10.2f}  {med_v:>12.1f}"
        )

    # -----------------------------------------------------------------------
    # Save CSV
    # -----------------------------------------------------------------------
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_cols = [
        "Paper_ID", "Title", "Year",
        "Field_Strength_Type", "Field_Strength_Norm",
        "Architecture_Norm", "LMIC_Score",
        "Low_Field_Norm", "Resource_Constraints_Norm",
        "Clinical_Validation_Norm", "Main_Finding_1",
        "Field_Category",
    ]
    # Keep only columns that exist in the dataframe
    output_cols = [c for c in output_cols if c in df.columns]

    # Export all cross-field papers (true + multi-scanner standard)
    cross_all = pd.concat([true_cross, multi_std]).sort_values("Paper_ID")
    cross_all[output_cols].to_csv(
        out_dir / "analysis_cross_field_generalization.csv", index=False
    )

    out_path = out_dir / "analysis_cross_field_generalization.csv"
    print(f"\n  Saved: {out_path}")
    return true_cross, multi_std, single


if __name__ == "__main__":
    analyze_cross_field_generalization()
