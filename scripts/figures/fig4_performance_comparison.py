"""
Figure 4: Performance Metrics Comparison

Multi-panel figure with clean box+strip plots and scatter:
  A. PSNR by Architecture
  B. SSIM by Architecture
  C. PSNR vs SSIM scatter (colored by architecture)
  D. PSNR by Field Strength
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from mapper import load_data, save_figure, configure_matplotlib

np.random.seed(42)

PALETTE = {
    "CNN":         "#2E86AB",
    "U-Net":       "#A23B72",
    "Hybrid":      "#F18F01",
    "GAN":         "#C73E1D",
    "Other":       "#7f8c8d",
    "Diffusion":   "#44BBA4",
    "Non-AI":      "#95a5a6",
    "Transformer": "#6C5B7B",
}

FS_PALETTE = {
    "Low-field":      "#E74C3C",
    "Standard-field": "#2E86AB",
    "Mixed":          "#9B59B6",
    "High-field":     "#2ECC71",
    "Not specified":  "#BDC3C7",
}


def _style_box_panel(ax, data, x_col, y_col, palette, ylabel, title, subtitle):
    """Style a box+strip panel consistently."""
    valid = data.dropna(subset=[y_col])
    counts = valid[x_col].value_counts()
    valid_cats = counts[counts >= 2].index.tolist()
    valid = valid[valid[x_col].isin(valid_cats)]

    if len(valid) == 0:
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center",
                transform=ax.transAxes, fontsize=11, color="#95a5a6")
        ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=12)
        return

    order = valid.groupby(x_col)[y_col].median().sort_values(ascending=False).index
    pal = {k: palette.get(k, "#95a5a6") for k in order}

    bp = sns.boxplot(data=valid, x=x_col, y=y_col, order=order, palette=pal,
                     ax=ax, width=0.5, fliersize=0, linewidth=1,
                     boxprops=dict(alpha=0.7), medianprops=dict(color="white", linewidth=2))
    sns.stripplot(data=valid, x=x_col, y=y_col, order=order,
                  color="#2C3E50", alpha=0.6, size=6, ax=ax, jitter=0.15,
                  edgecolor="white", linewidth=0.5)

    # Add n= labels below each box
    for i, cat in enumerate(order):
        n = counts.get(cat, 0)
        med = valid[valid[x_col] == cat][y_col].median()
        ax.text(i, ax.get_ylim()[0] + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02,
                f"n={n}", ha="center", fontsize=7, color="#7f8c8d")

    ax.set_xlabel("")
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=12)
    ax.text(0, 1.04, subtitle,
            transform=ax.transAxes, fontsize=9, color="#7f8c8d", style="italic")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="y", linestyle="--", alpha=0.2)
    plt.sca(ax)
    plt.xticks(rotation=30, ha="right", fontsize=9)


def create_fig4():
    configure_matplotlib()
    df = load_data()

    fig = plt.figure(figsize=(15, 11))
    gs = gridspec.GridSpec(2, 2, hspace=0.4, wspace=0.3)

    # Panel A: PSNR by Architecture
    ax_a = fig.add_subplot(gs[0, 0])
    _style_box_panel(ax_a, df, "Architecture_Norm", "PSNR_Numeric", PALETTE,
                     "PSNR (dB)", "A.  PSNR by Architecture",
                     "Higher PSNR indicates better reconstruction quality")

    # Panel B: SSIM by Architecture
    ax_b = fig.add_subplot(gs[0, 1])
    _style_box_panel(ax_b, df, "Architecture_Norm", "SSIM_Numeric", PALETTE,
                     "SSIM", "B.  SSIM by Architecture",
                     "SSIM ranges from 0 (no similarity) to 1 (identical)")

    # Panel C: PSNR vs SSIM scatter
    ax_c = fig.add_subplot(gs[1, 0])
    df_both = df.dropna(subset=["PSNR_Numeric", "SSIM_Numeric"])

    if len(df_both) > 0:
        for arch in df_both["Architecture_Norm"].unique():
            subset = df_both[df_both["Architecture_Norm"] == arch]
            ax_c.scatter(subset["PSNR_Numeric"], subset["SSIM_Numeric"],
                         c=PALETTE.get(arch, "#95a5a6"), label=f"{arch} (n={len(subset)})",
                         s=80, alpha=0.75, edgecolors="white", linewidth=0.8, zorder=3)

    ax_c.set_xlabel("PSNR (dB)", fontsize=10)
    ax_c.set_ylabel("SSIM", fontsize=10)
    ax_c.set_title("C.  PSNR vs SSIM by Architecture", fontsize=12,
                    fontweight="bold", loc="left", pad=12)
    ax_c.text(0, 1.04, f"{len(df_both)} papers reporting both metrics",
              transform=ax_c.transAxes, fontsize=9, color="#7f8c8d", style="italic")
    ax_c.legend(fontsize=7.5, loc="lower right", frameon=True,
                fancybox=True, edgecolor="#ddd")
    ax_c.spines["top"].set_visible(False)
    ax_c.spines["right"].set_visible(False)
    ax_c.tick_params(length=0)
    ax_c.grid(linestyle="--", alpha=0.15)

    # Panel D: PSNR by Field Strength
    ax_d = fig.add_subplot(gs[1, 1])
    _style_box_panel(ax_d, df, "Field_Strength_Norm", "PSNR_Numeric", FS_PALETTE,
                     "PSNR (dB)", "D.  PSNR by Field Strength",
                     "Comparison across MRI field strength categories")

    plt.tight_layout()
    save_figure(fig, "fig4_performance_comparison")

    print("\n=== Figure 4 Summary ===")
    print(f"  Papers with PSNR: {df['PSNR_Numeric'].notna().sum()}")
    print(f"  Papers with SSIM: {df['SSIM_Numeric'].notna().sum()}")
    print(f"  Papers with both: {len(df_both)}")
    if df["PSNR_Numeric"].notna().any():
        print(f"  Median PSNR: {df['PSNR_Numeric'].median():.2f} dB")
    if df["SSIM_Numeric"].notna().any():
        print(f"  Median SSIM: {df['SSIM_Numeric'].median():.4f}")

    return fig


if __name__ == "__main__":
    create_fig4()
