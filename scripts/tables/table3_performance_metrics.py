"""
Table 3: Performance Metrics Summary

Generates a summary of PSNR and SSIM values reported across studies,
broken down by architecture type and field strength.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
import numpy as np
from mapper import load_data, get_project_root


def create_table3():
    df = load_data()
    n = len(df)

    # --- Overall metrics ---
    print("\n=== Table 3: Performance Metrics Summary ===\n")

    sections = []

    # Section A: Overall reporting rates
    psnr_reported = df["PSNR_Numeric"].notna().sum()
    ssim_reported = df["SSIM_Numeric"].notna().sum()

    section_a = []
    section_a.append({
        "Metric": "PSNR (dB)",
        "n Reporting": psnr_reported,
        "% Reporting": f"{psnr_reported/n*100:.1f}%",
        "Median": f"{df['PSNR_Numeric'].median():.2f}" if psnr_reported > 0 else "N/A",
        "Mean (SD)": f"{df['PSNR_Numeric'].mean():.2f} ({df['PSNR_Numeric'].std():.2f})" if psnr_reported > 0 else "N/A",
        "Range": f"{df['PSNR_Numeric'].min():.2f}\u2013{df['PSNR_Numeric'].max():.2f}" if psnr_reported > 0 else "N/A",
    })
    section_a.append({
        "Metric": "SSIM",
        "n Reporting": ssim_reported,
        "% Reporting": f"{ssim_reported/n*100:.1f}%",
        "Median": f"{df['SSIM_Numeric'].median():.4f}" if ssim_reported > 0 else "N/A",
        "Mean (SD)": f"{df['SSIM_Numeric'].mean():.4f} ({df['SSIM_Numeric'].std():.4f})" if ssim_reported > 0 else "N/A",
        "Range": f"{df['SSIM_Numeric'].min():.4f}\u2013{df['SSIM_Numeric'].max():.4f}" if ssim_reported > 0 else "N/A",
    })
    df_a = pd.DataFrame(section_a)

    # Section B: PSNR by architecture
    section_b = []
    for arch in df["Architecture_Norm"].value_counts().index:
        subset = df[df["Architecture_Norm"] == arch]["PSNR_Numeric"].dropna()
        if len(subset) > 0:
            section_b.append({
                "Architecture": arch,
                "n": len(subset),
                "Median PSNR (dB)": f"{subset.median():.2f}",
                "Range": f"{subset.min():.2f}\u2013{subset.max():.2f}",
            })
    df_b = pd.DataFrame(section_b)

    # Section C: SSIM by architecture
    section_c = []
    for arch in df["Architecture_Norm"].value_counts().index:
        subset = df[df["Architecture_Norm"] == arch]["SSIM_Numeric"].dropna()
        if len(subset) > 0:
            section_c.append({
                "Architecture": arch,
                "n": len(subset),
                "Median SSIM": f"{subset.median():.4f}",
                "Range": f"{subset.min():.4f}\u2013{subset.max():.4f}",
            })
    df_c = pd.DataFrame(section_c)

    # Section D: Metrics by field strength
    section_d = []
    for fs in df["Field_Strength_Norm"].value_counts().index:
        subset = df[df["Field_Strength_Norm"] == fs]
        psnr = subset["PSNR_Numeric"].dropna()
        ssim = subset["SSIM_Numeric"].dropna()
        section_d.append({
            "Field Strength": fs,
            "n Papers": len(subset),
            "PSNR Reported": len(psnr),
            "Median PSNR (dB)": f"{psnr.median():.2f}" if len(psnr) > 0 else "N/R",
            "SSIM Reported": len(ssim),
            "Median SSIM": f"{ssim.median():.4f}" if len(ssim) > 0 else "N/R",
        })
    df_d = pd.DataFrame(section_d)

    # Print all sections
    print("  Panel A: Overall Metrics")
    print(f"  {'Metric':<12} {'n':>4} {'%':>7} {'Median':>9} {'Mean (SD)':>18} {'Range':>18}")
    print(f"  {'-'*70}")
    for _, row in df_a.iterrows():
        print(f"  {row['Metric']:<12} {row['n Reporting']:>4} {row['% Reporting']:>7} "
              f"{row['Median']:>9} {row['Mean (SD)']:>18} {row['Range']:>18}")

    print(f"\n  Panel B: PSNR by Architecture")
    print(f"  {'Architecture':<15} {'n':>4} {'Median (dB)':>14} {'Range':>20}")
    print(f"  {'-'*55}")
    for _, row in df_b.iterrows():
        print(f"  {row['Architecture']:<15} {row['n']:>4} {row['Median PSNR (dB)']:>14} {row['Range']:>20}")

    print(f"\n  Panel C: SSIM by Architecture")
    print(f"  {'Architecture':<15} {'n':>4} {'Median':>10} {'Range':>22}")
    print(f"  {'-'*55}")
    for _, row in df_c.iterrows():
        print(f"  {row['Architecture']:<15} {row['n']:>4} {row['Median SSIM']:>10} {row['Range']:>22}")

    print(f"\n  Panel D: Metrics by Field Strength")
    print(f"  {'Field Strength':<18} {'n':>4} {'PSNR n':>7} {'Med PSNR':>10} {'SSIM n':>7} {'Med SSIM':>10}")
    print(f"  {'-'*60}")
    for _, row in df_d.iterrows():
        print(f"  {row['Field Strength']:<18} {row['n Papers']:>4} {row['PSNR Reported']:>7} "
              f"{row['Median PSNR (dB)']:>10} {row['SSIM Reported']:>7} {row['Median SSIM']:>10}")

    # Save all panels
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    df_a.to_csv(out_dir / "table3a_overall_metrics.csv", index=False)
    df_b.to_csv(out_dir / "table3b_psnr_by_architecture.csv", index=False)
    df_c.to_csv(out_dir / "table3c_ssim_by_architecture.csv", index=False)
    df_d.to_csv(out_dir / "table3d_metrics_by_field_strength.csv", index=False)

    return df_a, df_b, df_c, df_d


if __name__ == "__main__":
    create_table3()
