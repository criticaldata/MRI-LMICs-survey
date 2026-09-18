"""
Figure 4: Performance Metrics Comparison

Multi-panel figure with clean box+strip plots and scatter:
  A. PSNR by Architecture
  B. SSIM by Architecture
  C. PSNR vs SSIM scatter (colored by architecture)
  D. Translational readiness criteria
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import sys
from pathlib import Path
from mapper import load_data, save_figure, configure_matplotlib, panel_title

sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))
from review_metrics import add_derived_fields

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
    panel_title(ax, title, subtitle)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="y", linestyle="--", alpha=0.2)
    plt.sca(ax)
    plt.xticks(rotation=30, ha="right", fontsize=9)


def create_fig4():
    configure_matplotlib()
    df = add_derived_fields(load_data())

    fig = plt.figure(figsize=(15, 12))
    gs = gridspec.GridSpec(2, 2, hspace=0.5, wspace=0.3)

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
    panel_title(ax_c, "C.  PSNR vs SSIM by Architecture",
                f"{len(df_both)} papers reporting both metrics")
    ax_c.legend(fontsize=7.5, loc="lower right", frameon=True,
                fancybox=True, edgecolor="#ddd")
    ax_c.spines["top"].set_visible(False)
    ax_c.spines["right"].set_visible(False)
    ax_c.tick_params(length=0)
    ax_c.grid(linestyle="--", alpha=0.15)

    # Panel D: use the exact five TR criteria defined in Methods.  The former
    # panel plotted PSNR by field strength, which did not match the manuscript
    # label or the reviewer-requested TR construct.
    ax_d = fig.add_subplot(gs[1, 1])
    tr_criteria = [
        ("Low-Field Domain", "TR_LowFieldDomain", "#E74C3C"),
        ("Open Science", "TR_OpenScience", "#2E86AB"),
        ("Clinical Evaluation", "TR_ClinicalEvaluation", "#2ECC71"),
        ("Hardware Awareness", "TR_HardwareAwareness", "#9B59B6"),
        ("Data Diversity", "TR_DataDiversity", "#F18F01"),
    ]
    labels = [item[0] for item in tr_criteria]
    values = [int(df[item[1]].sum()) for item in tr_criteria]
    colors = [item[2] for item in tr_criteria]
    y_pos = np.arange(len(labels))
    bars = ax_d.barh(y_pos, values, height=0.55, color=colors,
                     edgecolor="white", linewidth=1)
    for i, value in enumerate(values):
        ax_d.text(value + 0.4, i, f"{value}/{len(df)} ({value / len(df) * 100:.0f}%)",
                  va="center", fontsize=8.5, fontweight="bold", color="#2C3E50")
    ax_d.set_yticks(y_pos)
    ax_d.set_yticklabels(labels, fontsize=8.5, fontweight="bold")
    ax_d.invert_yaxis()
    ax_d.set_xlabel("Number of Papers", fontsize=10)
    panel_title(ax_d, "D.  Translational Readiness Criteria",
                "Exact five-criterion TR definition; n=48 included studies")
    ax_d.spines["top"].set_visible(False)
    ax_d.spines["right"].set_visible(False)
    ax_d.tick_params(length=0)
    ax_d.grid(axis="x", linestyle="--", alpha=0.2)
    ax_d.set_xlim(0, max(values) + 10)

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
