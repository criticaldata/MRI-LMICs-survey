"""
Table 4: LMIC Applicability Assessment

Generates a summary of LMIC relevance scores (1-5), cross-tabulated with
low-field mention, resource constraints, code availability, and clinical validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
from mapper import load_data, get_project_root

SCORE_LABELS = {
    1: "Score 1 (Minimal relevance)",
    2: "Score 2 (Low relevance)",
    3: "Score 3 (Moderate relevance)",
    4: "Score 4 (High relevance)",
    5: "Score 5 (Direct LMIC application)",
}


def create_table4():
    df = load_data()
    n = len(df)

    # --- Panel A: LMIC Score Distribution ---
    panel_a_rows = []
    for score in [5, 4, 3, 2, 1]:
        subset = df[df["LMIC_Score"] == score]
        count = len(subset)
        pct = count / n * 100

        # Within this score group, count key characteristics
        low_field = (subset["Low_Field_Norm"] == "Yes").sum()
        resource = (subset["Resource_Constraints_Norm"] == "Yes").sum()
        code = (subset["Code_Available_Norm"] == "Yes").sum()
        validated = (subset["Clinical_Validation_Norm"] != "None").sum()

        panel_a_rows.append({
            "LMIC Score": SCORE_LABELS[score],
            "n Papers": count,
            "% of Total": f"{pct:.1f}%",
            "Low-Field": low_field,
            "Resource Addressed": resource,
            "Code Available": code,
            "Clinically Validated": validated,
        })

    # Papers with missing LMIC score
    missing = df["LMIC_Score"].isna().sum()
    if missing > 0:
        panel_a_rows.append({
            "LMIC Score": "Not scored",
            "n Papers": missing,
            "% of Total": f"{missing/n*100:.1f}%",
            "Low-Field": "",
            "Resource Addressed": "",
            "Code Available": "",
            "Clinically Validated": "",
        })

    df_a = pd.DataFrame(panel_a_rows)

    # --- Panel B: Key LMIC indicators ---
    panel_b_rows = []

    # Low-field focus
    lf = df[df["Low_Field_Norm"] == "Yes"]
    panel_b_rows.append({
        "Indicator": "Low-field MRI mentioned",
        "n": len(lf),
        "%": f"{len(lf)/n*100:.1f}%",
        "Median LMIC Score": f"{lf['LMIC_Score'].median():.0f}" if len(lf) > 0 else "N/A",
    })

    # Resource constraints
    rc = df[df["Resource_Constraints_Norm"] == "Yes"]
    panel_b_rows.append({
        "Indicator": "Resource constraints addressed",
        "n": len(rc),
        "%": f"{len(rc)/n*100:.1f}%",
        "Median LMIC Score": f"{rc['LMIC_Score'].median():.0f}" if len(rc) > 0 else "N/A",
    })

    # Code available
    ca = df[df["Code_Available_Norm"] == "Yes"]
    panel_b_rows.append({
        "Indicator": "Code publicly available",
        "n": len(ca),
        "%": f"{len(ca)/n*100:.1f}%",
        "Median LMIC Score": f"{ca['LMIC_Score'].median():.0f}" if len(ca) > 0 else "N/A",
    })

    # Clinical validation
    cv = df[df["Clinical_Validation_Norm"] != "None"]
    panel_b_rows.append({
        "Indicator": "Clinical validation reported",
        "n": len(cv),
        "%": f"{len(cv)/n*100:.1f}%",
        "Median LMIC Score": f"{cv['LMIC_Score'].median():.0f}" if len(cv) > 0 else "N/A",
    })

    # High LMIC relevance (score 4-5)
    high_lmic = df[df["LMIC_Score"] >= 4]
    panel_b_rows.append({
        "Indicator": "High LMIC relevance (Score 4-5)",
        "n": len(high_lmic),
        "%": f"{len(high_lmic)/n*100:.1f}%",
        "Median LMIC Score": f"{high_lmic['LMIC_Score'].median():.0f}" if len(high_lmic) > 0 else "N/A",
    })

    df_b = pd.DataFrame(panel_b_rows)

    # --- Panel C: Architecture breakdown for high-LMIC papers ---
    high_lmic = df[df["LMIC_Score"] >= 4]
    panel_c_rows = []
    for arch in high_lmic["Architecture_Norm"].value_counts().index:
        subset = high_lmic[high_lmic["Architecture_Norm"] == arch]
        panel_c_rows.append({
            "Architecture": arch,
            "n (Score 4-5)": len(subset),
            "% of High-LMIC": f"{len(subset)/len(high_lmic)*100:.1f}%",
        })
    df_c = pd.DataFrame(panel_c_rows)

    # Print
    print("\n=== Table 4: LMIC Applicability Assessment ===\n")

    print("  Panel A: LMIC Relevance Score Distribution")
    print(f"  {'Score':<40} {'n':>4} {'%':>7} {'LF':>4} {'RC':>4} {'Code':>5} {'CV':>4}")
    print(f"  {'-'*70}")
    for _, row in df_a.iterrows():
        print(f"  {row['LMIC Score']:<40} {row['n Papers']:>4} {row['% of Total']:>7} "
              f"{str(row['Low-Field']):>4} {str(row['Resource Addressed']):>4} "
              f"{str(row['Code Available']):>5} {str(row['Clinically Validated']):>4}")

    print(f"\n  Panel B: Key LMIC Accessibility Indicators")
    print(f"  {'Indicator':<40} {'n':>4} {'%':>7} {'Med Score':>10}")
    print(f"  {'-'*65}")
    for _, row in df_b.iterrows():
        print(f"  {row['Indicator']:<40} {row['n']:>4} {row['%']:>7} {row['Median LMIC Score']:>10}")

    print(f"\n  Panel C: Architecture Distribution (LMIC Score 4-5)")
    print(f"  {'Architecture':<20} {'n':>4} {'%':>8}")
    print(f"  {'-'*35}")
    for _, row in df_c.iterrows():
        print(f"  {row['Architecture']:<20} {row['n (Score 4-5)']:>4} {row['% of High-LMIC']:>8}")

    # Save
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    df_a.to_csv(out_dir / "table4a_lmic_score_distribution.csv", index=False)
    df_b.to_csv(out_dir / "table4b_lmic_indicators.csv", index=False)
    df_c.to_csv(out_dir / "table4c_architecture_high_lmic.csv", index=False)

    return df_a, df_b, df_c


if __name__ == "__main__":
    create_table4()
