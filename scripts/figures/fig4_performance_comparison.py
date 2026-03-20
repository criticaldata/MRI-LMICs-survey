"""
Figure 4: Performance Metrics Comparison

Scatter and box plots comparing PSNR/SSIM across architectures and field strengths.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mapper import load_data, save_figure, configure_matplotlib, ARCHITECTURE_COLORS, FIELD_STRENGTH_COLORS

np.random.seed(42)


def create_fig4():
    configure_matplotlib()
    df = load_data()

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # --- Panel A: PSNR by Architecture (box + strip) ---
    ax = axes[0, 0]
    df_psnr = df.dropna(subset=["PSNR_Numeric"])
    # Only show architectures with >= 2 data points
    arch_counts = df_psnr["Architecture_Norm"].value_counts()
    valid_archs = arch_counts[arch_counts >= 2].index.tolist()
    df_psnr_filt = df_psnr[df_psnr["Architecture_Norm"].isin(valid_archs)]

    if len(df_psnr_filt) > 0:
        order = df_psnr_filt.groupby("Architecture_Norm")["PSNR_Numeric"].median().sort_values(ascending=False).index
        palette = {a: ARCHITECTURE_COLORS.get(a, "#95a5a6") for a in order}
        sns.boxplot(data=df_psnr_filt, x="Architecture_Norm", y="PSNR_Numeric",
                    order=order, palette=palette, ax=ax, width=0.5, fliersize=0)
        sns.stripplot(data=df_psnr_filt, x="Architecture_Norm", y="PSNR_Numeric",
                      order=order, color="black", alpha=0.5, size=5, ax=ax, jitter=True)
    ax.set_xlabel("Architecture")
    ax.set_ylabel("PSNR (dB)")
    ax.set_title("A. PSNR by Architecture")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.sca(ax)
    plt.xticks(rotation=30, ha="right")

    # --- Panel B: SSIM by Architecture ---
    ax = axes[0, 1]
    df_ssim = df.dropna(subset=["SSIM_Numeric"])
    arch_counts_ssim = df_ssim["Architecture_Norm"].value_counts()
    valid_archs_ssim = arch_counts_ssim[arch_counts_ssim >= 2].index.tolist()
    df_ssim_filt = df_ssim[df_ssim["Architecture_Norm"].isin(valid_archs_ssim)]

    if len(df_ssim_filt) > 0:
        order_s = df_ssim_filt.groupby("Architecture_Norm")["SSIM_Numeric"].median().sort_values(ascending=False).index
        palette_s = {a: ARCHITECTURE_COLORS.get(a, "#95a5a6") for a in order_s}
        sns.boxplot(data=df_ssim_filt, x="Architecture_Norm", y="SSIM_Numeric",
                    order=order_s, palette=palette_s, ax=ax, width=0.5, fliersize=0)
        sns.stripplot(data=df_ssim_filt, x="Architecture_Norm", y="SSIM_Numeric",
                      order=order_s, color="black", alpha=0.5, size=5, ax=ax, jitter=True)
    ax.set_xlabel("Architecture")
    ax.set_ylabel("SSIM")
    ax.set_title("B. SSIM by Architecture")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.sca(ax)
    plt.xticks(rotation=30, ha="right")

    # --- Panel C: PSNR vs SSIM scatter colored by architecture ---
    ax = axes[1, 0]
    df_both = df.dropna(subset=["PSNR_Numeric", "SSIM_Numeric"])
    if len(df_both) > 0:
        for arch in df_both["Architecture_Norm"].unique():
            subset = df_both[df_both["Architecture_Norm"] == arch]
            ax.scatter(subset["PSNR_Numeric"], subset["SSIM_Numeric"],
                       c=ARCHITECTURE_COLORS.get(arch, "#95a5a6"),
                       label=arch, s=60, alpha=0.7, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("PSNR (dB)")
    ax.set_ylabel("SSIM")
    ax.set_title("C. PSNR vs SSIM by Architecture")
    ax.legend(fontsize=7, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # --- Panel D: PSNR by Field Strength ---
    ax = axes[1, 1]
    df_psnr_fs = df.dropna(subset=["PSNR_Numeric"])
    fs_counts = df_psnr_fs["Field_Strength_Norm"].value_counts()
    valid_fs = fs_counts[fs_counts >= 2].index.tolist()
    df_psnr_fs = df_psnr_fs[df_psnr_fs["Field_Strength_Norm"].isin(valid_fs)]

    if len(df_psnr_fs) > 0:
        order_fs = df_psnr_fs.groupby("Field_Strength_Norm")["PSNR_Numeric"].median().sort_values(ascending=False).index
        palette_fs = {f: FIELD_STRENGTH_COLORS.get(f, "#95a5a6") for f in order_fs}
        sns.boxplot(data=df_psnr_fs, x="Field_Strength_Norm", y="PSNR_Numeric",
                    order=order_fs, palette=palette_fs, ax=ax, width=0.5, fliersize=0)
        sns.stripplot(data=df_psnr_fs, x="Field_Strength_Norm", y="PSNR_Numeric",
                      order=order_fs, color="black", alpha=0.5, size=5, ax=ax, jitter=True)
    ax.set_xlabel("Field Strength")
    ax.set_ylabel("PSNR (dB)")
    ax.set_title("D. PSNR by Field Strength")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.sca(ax)
    plt.xticks(rotation=30, ha="right")

    plt.tight_layout()
    save_figure(fig, "fig4_performance_comparison")

    # Summary
    print("\n=== Figure 4 Summary ===")
    print(f"  Papers with PSNR: {df['PSNR_Numeric'].notna().sum()}")
    print(f"  Papers with SSIM: {df['SSIM_Numeric'].notna().sum()}")
    print(f"  Papers with both: {len(df_both)}")
    if len(df_both) > 0:
        print(f"  Overall median PSNR: {df['PSNR_Numeric'].median():.2f} dB")
        print(f"  Overall median SSIM: {df['SSIM_Numeric'].median():.4f}")

    return fig


if __name__ == "__main__":
    create_fig4()
