"""
Figure 2: AI Architecture Landscape

Multi-panel figure:
  A. Grouped horizontal bars of architecture types (styled like omics-bias pipeline bars)
  B. Architecture x Application heatmap
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from mapper import load_data, save_figure, configure_matplotlib, panel_title

np.random.seed(42)

# Curated palette — each architecture gets a distinct hue
ARCH_PALETTE = {
    "CNN":         "#2E86AB",
    "U-Net":       "#A23B72",
    "Hybrid":      "#F18F01",
    "GAN":         "#C73E1D",
    "Other":       "#7f8c8d",
    "Diffusion":   "#44BBA4",
    "Non-AI":      "#95a5a6",
    "Transformer": "#6C5B7B",
}


def create_fig2():
    configure_matplotlib()
    df = load_data()

    fig = plt.figure(figsize=(15, 7))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1, 1.4], wspace=0.35)

    # ========================
    # Panel A: Architecture distribution (horizontal bars)
    # ========================
    ax_a = fig.add_subplot(gs[0])

    arch_counts = df["Architecture_Norm"].value_counts()
    archs = arch_counts.index.tolist()
    counts = arch_counts.values

    colors = [ARCH_PALETTE.get(a, "#bdc3c7") for a in archs]
    y_pos = np.arange(len(archs))

    bars = ax_a.barh(y_pos, counts, height=0.6, color=colors,
                     edgecolor="white", linewidth=0.8)

    # Labels inside or beside bars
    for i, (bar, count, arch) in enumerate(zip(bars, counts, archs)):
        pct = count / len(df) * 100
        if count >= 4:
            ax_a.text(count - 0.5, i, f"{count} ({pct:.0f}%)",
                      ha="right", va="center", fontsize=9,
                      fontweight="bold", color="white")
        else:
            ax_a.text(count + 0.3, i, f"{count} ({pct:.0f}%)",
                      ha="left", va="center", fontsize=9,
                      fontweight="bold", color="#2C3E50")

    ax_a.set_yticks(y_pos)
    ax_a.set_yticklabels(archs, fontsize=10, fontweight="bold")
    ax_a.invert_yaxis()
    ax_a.set_xlabel("Number of Papers", fontsize=10)
    panel_title(ax_a, "A.  Architecture Distribution",
                f"{len(df)} studies | {len(archs)} architecture types")

    ax_a.spines["top"].set_visible(False)
    ax_a.spines["right"].set_visible(False)
    ax_a.spines["left"].set_linewidth(0.5)
    ax_a.spines["bottom"].set_linewidth(0.5)
    ax_a.tick_params(axis="both", length=0)
    ax_a.grid(axis="x", linestyle="--", alpha=0.2)
    ax_a.set_xlim(0, counts[0] + 5)

    # ========================
    # Panel B: Architecture x Application heatmap
    # ========================
    ax_b = fig.add_subplot(gs[1])

    ct = pd.crosstab(df["Architecture_Norm"], df["Application_Norm"])
    # Sort by row and column totals
    row_order = ct.sum(axis=1).sort_values(ascending=False).index
    col_order = ct.sum(axis=0).sort_values(ascending=False).index
    ct = ct.loc[row_order, col_order]

    # Custom colormap
    cmap = sns.color_palette("YlOrRd", as_cmap=True)
    mask = ct == 0

    sns.heatmap(ct, annot=True, fmt="d", cmap=cmap, ax=ax_b, mask=mask,
                linewidths=1.5, linecolor="white",
                cbar_kws={"label": "Number of Papers", "shrink": 0.7},
                annot_kws={"fontsize": 10, "fontweight": "bold"},
                square=False)

    # Style zeros differently
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            if ct.iloc[i, j] == 0:
                ax_b.text(j + 0.5, i + 0.5, "·", ha="center", va="center",
                          fontsize=14, color="#ddd")

    panel_title(ax_b, "B.  Architecture by Application Area",
                "Cell values show number of papers at each intersection")
    ax_b.set_xlabel("Application Area", fontsize=10)
    ax_b.set_ylabel("")
    ax_b.tick_params(axis="both", length=0)
    plt.setp(ax_b.get_xticklabels(), rotation=35, ha="right", fontsize=9)
    plt.setp(ax_b.get_yticklabels(), fontsize=9)

    plt.tight_layout()
    save_figure(fig, "fig2_architecture_distribution")

    print("\n=== Figure 2 Summary ===")
    print(f"  Most common: {archs[0]} ({counts[0]} papers, {counts[0]/len(df)*100:.1f}%)")
    print(f"  Top 3: {', '.join(archs[:3])}")
    print(f"  Unique architectures: {len(archs)}")
    print(f"  Brain + CNN papers: {ct.loc['CNN', 'Brain'] if 'Brain' in ct.columns else 0}")

    return fig


if __name__ == "__main__":
    create_fig2()
