"""
Figure 1: Temporal Distribution of MRI Super-Resolution Studies

Grouped horizontal bars showing publication counts by year, with stacked
breakdown by primary focus. Clean publication-quality style.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from mapper import load_data, save_figure, configure_matplotlib, PRIMARY_FOCUS_COLORS

np.random.seed(42)


def create_fig1():
    configure_matplotlib()
    df = load_data()

    # --- Prepare data ---
    focus_order = (df["Primary_Focus_Norm"].value_counts().index.tolist())
    year_order = sorted(df["Year"].dropna().unique())
    ct = pd.crosstab(df["Year"], df["Primary_Focus_Norm"])
    ct = ct.reindex(columns=focus_order, fill_value=0)
    ct = ct.reindex(index=year_order, fill_value=0)

    # --- Color palette with gradient ---
    base_colors = {
        "Pure SR": "#2E86AB",
        "SR + Denoising": "#A23B72",
        "SR + Classification": "#F18F01",
        "SR + Segmentation": "#C73E1D",
        "SR + Diagnosis": "#3B1F2B",
        "SR + Other": "#44BBA4",
        "Review/Survey": "#95a5a6",
        "Other": "#bdc3c7",
    }

    fig, ax = plt.subplots(figsize=(12, 6.5))

    # --- Stacked horizontal bars ---
    y_positions = np.arange(len(year_order))
    bar_height = 0.65
    left = np.zeros(len(year_order))

    for focus in focus_order:
        values = ct[focus].values
        color = base_colors.get(focus, "#bdc3c7")
        bars = ax.barh(y_positions, values, height=bar_height, left=left,
                       label=focus, color=color, edgecolor="white", linewidth=0.8)

        # Add count labels inside bars (only if segment > 1)
        for i, (val, l) in enumerate(zip(values, left)):
            if val >= 2:
                ax.text(l + val / 2, i, str(int(val)),
                        ha="center", va="center", fontsize=8,
                        fontweight="bold", color="white")
        left += values

    # --- Total count labels on right ---
    totals = ct.sum(axis=1)
    for i, total in enumerate(totals):
        ax.text(total + 0.5, i, f"{int(total)} papers",
                va="center", fontsize=9, fontweight="bold", color="#2C3E50")

    # --- Year labels with styling ---
    ax.set_yticks(y_positions)
    ax.set_yticklabels([str(int(y)) for y in year_order], fontsize=11, fontweight="bold")
    ax.invert_yaxis()

    # --- Title ---
    ax.set_title("MRI Super-Resolution: Publication Trends by Year",
                 fontsize=14, fontweight="bold", pad=20, loc="left")
    ax.text(0, 1.04, f"Primary focus distribution across {len(df)} studies (2020\u20132025)",
            transform=ax.transAxes, fontsize=10, color="#7f8c8d", style="italic")

    ax.set_xlabel("Number of Papers", fontsize=11)

    # --- Legend ---
    legend = ax.legend(title="Primary Focus", bbox_to_anchor=(1.01, 1), loc="upper left",
                       fontsize=8.5, title_fontsize=9.5, frameon=True, fancybox=True,
                       edgecolor="#ddd", facecolor="white")

    # --- Clean spines ---
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
    for focus in focus_order:
        n = (df["Primary_Focus_Norm"] == focus).sum()
        print(f"  {focus}: {n} ({n/len(df)*100:.1f}%)")

    return fig


if __name__ == "__main__":
    create_fig1()
