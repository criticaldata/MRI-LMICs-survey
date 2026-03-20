"""
Table 2 (Main): Merged Performance & LMIC Applicability Table

Combines architecture performance metrics with LMIC relevance scoring into
a single condensed table for the NMI main text (display item #4).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
import numpy as np
from mapper import load_data, get_project_root


def create_merged_table():
    df = load_data()
    n = len(df)

    rows = []
    for arch in df["Architecture_Norm"].value_counts().index:
        subset = df[df["Architecture_Norm"] == arch]
        n_papers = len(subset)
        pct = n_papers / n * 100

        # PSNR
        psnr = subset["PSNR_Numeric"].dropna()
        psnr_str = f"{psnr.median():.1f} ({psnr.min():.1f}\u2013{psnr.max():.1f})" if len(psnr) >= 2 else (
            f"{psnr.median():.1f}" if len(psnr) == 1 else "N/R"
        )
        psnr_n = len(psnr)

        # SSIM
        ssim = subset["SSIM_Numeric"].dropna()
        ssim_str = f"{ssim.median():.3f} ({ssim.min():.3f}\u2013{ssim.max():.3f})" if len(ssim) >= 2 else (
            f"{ssim.median():.3f}" if len(ssim) == 1 else "N/R"
        )
        ssim_n = len(ssim)

        # LMIC scores
        lmic = subset["LMIC_Score"].dropna()
        lmic_median = f"{lmic.median():.0f}" if len(lmic) > 0 else "N/A"
        lmic_high = (lmic >= 4).sum()
        lmic_high_pct = lmic_high / len(lmic) * 100 if len(lmic) > 0 else 0

        # Low field
        low_field = (subset["Low_Field_Norm"] == "Yes").sum()

        # Code available
        code = (subset["Code_Available_Norm"] == "Yes").sum()

        # Clinical validation
        validated = (subset["Clinical_Validation_Norm"] != "None").sum()

        # Application areas (top 2)
        top_apps = subset["Application_Norm"].value_counts().head(2)
        apps_str = ", ".join([f"{app} ({cnt})" for app, cnt in top_apps.items()])

        rows.append({
            "Architecture": arch,
            "n (%)": f"{n_papers} ({pct:.0f}%)",
            "PSNR dB, median (range)": psnr_str,
            "PSNR n": psnr_n,
            "SSIM, median (range)": ssim_str,
            "SSIM n": ssim_n,
            "LMIC Score median": lmic_median,
            "LMIC >= 4, n (%)": f"{lmic_high} ({lmic_high_pct:.0f}%)",
            "Low-field": low_field,
            "Code Avail.": code,
            "Clinical Valid.": validated,
            "Top Applications": apps_str,
        })

    result = pd.DataFrame(rows)

    # Add totals row
    total_psnr = df["PSNR_Numeric"].dropna()
    total_ssim = df["SSIM_Numeric"].dropna()
    total_lmic = df["LMIC_Score"].dropna()
    result.loc[len(result)] = {
        "Architecture": "TOTAL",
        "n (%)": f"{n} (100%)",
        "PSNR dB, median (range)": f"{total_psnr.median():.1f} ({total_psnr.min():.1f}\u2013{total_psnr.max():.1f})",
        "PSNR n": len(total_psnr),
        "SSIM, median (range)": f"{total_ssim.median():.3f} ({total_ssim.min():.3f}\u2013{total_ssim.max():.3f})",
        "SSIM n": len(total_ssim),
        "LMIC Score median": f"{total_lmic.median():.0f}",
        "LMIC >= 4, n (%)": f"{(total_lmic >= 4).sum()} ({(total_lmic >= 4).sum()/len(total_lmic)*100:.0f}%)",
        "Low-field": (df["Low_Field_Norm"] == "Yes").sum(),
        "Code Avail.": (df["Code_Available_Norm"] == "Yes").sum(),
        "Clinical Valid.": (df["Clinical_Validation_Norm"] != "None").sum(),
        "Top Applications": f"Brain (27), MSK (7), General (5)",
    }

    # Save
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_dir / "table_merged_performance_lmic.csv", index=False)

    # Print
    print("\n=== Table 2 (Main): Performance & LMIC Applicability ===\n")
    print(f"  {'Arch':<13} {'n':>8} {'PSNR':>22} {'SSIM':>22} {'LMIC':>6} {'>=4':>10} {'LF':>4} {'Code':>5} {'CV':>4}")
    print(f"  {'-'*100}")
    for _, row in result.iterrows():
        print(f"  {row['Architecture']:<13} {row['n (%)']:>8} "
              f"{row['PSNR dB, median (range)']:>22} {row['SSIM, median (range)']:>22} "
              f"{row['LMIC Score median']:>6} {row['LMIC >= 4, n (%)']:>10} "
              f"{row['Low-field']:>4} {row['Code Avail.']:>5} {row['Clinical Valid.']:>4}")

    print(f"\n  Note: PSNR reported in {len(total_psnr)}/{n} papers ({len(total_psnr)/n*100:.0f}%)")
    print(f"  Note: SSIM reported in {len(total_ssim)}/{n} papers ({len(total_ssim)/n*100:.0f}%)")

    return result


if __name__ == "__main__":
    create_merged_table()
