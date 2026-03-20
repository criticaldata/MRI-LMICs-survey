"""
Figure 1: Temporal Distribution of MRI Super-Resolution Studies

Grouped horizontal bars showing publication counts by year, with stacked
breakdown by primary focus. Clean publication-quality style.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mapper import load_data, save_figure, configure_matplotlib, panel_title

np.random.seed(42)

BASE_COLORS = {
    "Pure SR": "#2E86AB",
    "SR + Denoising": "#A23B72",
    "SR + Classification": "#F18F01",
    "SR + Segmentation": "#C73E1D",
    "SR + Diagnosis": "#3B1F2B",
    "SR + Other": "#44BBA4",
    "Review/Survey": "#95a5a6",
    "Other": "#bdc3c7",
}


def create_fig1():
    configure_matplotlib()
    df = load_data()

    focus_order = df["Primary_Focus_Norm"].value_counts().index.tolist()
    year_order = sorted(df["Year"].dropna().unique())
    ct = pd.crosstab(df["Year"], df["Primary_Focus_Norm"])
    ct = ct.reindex(columns=focus_order, fill_value=0).reindex(index=year_order, fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))

    y_positions = np.arange(len(year_order))
    bar_height = 0.65
    left = np.zeros(len(year_order))

    for focus in focus_order:
        values = ct[focus].values
        color = BASE_COLORS.get(focus, "#bdc3c7")
        ax.barh(y_positions, values, height=bar_height, left=left,
                label=focus, color=color, edgecolor="white", linewidth=0.8)
        for i, (val, l) in enumerate(zip(values, left)):
            if val >= 2:
                ax.text(l + val / 2, i, str(int(val)),
                        ha="center", va="center", fontsize=8,
                        fontweight="bold", color="white")
        left += values

    totals = ct.sum(axis=1)
    for i, total in enumerate(totals):
        ax.text(total + 0.5, i, f"{int(total)} papers",
                va="center", fontsize=9, fontweight="bold", color="#2C3E50")

    ax.set_yticks(y_positions)
    ax.set_yticklabels([str(int(y)) for y in year_order], fontsize=11, fontweight="bold")
    ax.invert_yaxis()

    panel_title(ax, "MRI Super-Resolution: Publication Trends by Year",
                f"Primary focus distribution across {len(df)} studies (2020\u20132025)",
                fontsize=13)

    ax.set_xlabel("Number of Papers", fontsize=11)
    ax.legend(title="Primary Focus", bbox_to_anchor=(1.01, 1), loc="upper left",
              fontsize=8.5, title_fontsize=9.5, frameon=True, fancybox=True,
              edgecolor="#ddd", facecolor="white")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.5)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.tick_params(axis="both", which="both", length=0)
    ax.set_xlim(0, totals.max() + 5)
    ax.grid(axis="x", linestyle="--", alpha=0.2, color="#bdc3c7")

    plt.tight_layout()
    save_figure(fig, "fig1_year_distribution")

    print("\n=== Figure 1 Summary ===")
    print(f"  Total papers: {len(df)}")
    print(f"  Year range: {int(df['Year'].min())}\u2013{int(df['Year'].max())}")
    print(f"  Peak year: {int(totals.idxmax())} ({int(totals.max())} papers)")
    return fig


if __name__ == "__main__":
    create_fig1()
