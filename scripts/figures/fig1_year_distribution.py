"""
Figure 1: Temporal Distribution of MRI Super-Resolution Studies

Bar chart showing publication counts by year, with stacked coloring by
primary focus category.
"""

import numpy as np
import matplotlib.pyplot as plt
from mapper import load_data, save_figure, configure_matplotlib, PRIMARY_FOCUS_COLORS

np.random.seed(42)


def create_fig1():
    configure_matplotlib()
    df = load_data()

    # Cross-tabulate year x primary focus
    ct = pd.crosstab(df["Year"], df["Primary_Focus_Norm"])

    # Order columns by total count descending
    col_order = ct.sum().sort_values(ascending=False).index
    ct = ct[col_order]

    colors = [PRIMARY_FOCUS_COLORS.get(c, "#95a5a6") for c in ct.columns]

    fig, ax = plt.subplots(figsize=(8, 5))
    ct.plot(kind="bar", stacked=True, ax=ax, color=colors, edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Publication Year")
    ax.set_ylabel("Number of Papers")
    ax.set_title("Temporal Distribution of MRI Super-Resolution Studies (n=56)")
    ax.legend(title="Primary Focus", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)

    # Add count labels on top of each bar
    for i, year in enumerate(ct.index):
        total = ct.loc[year].sum()
        ax.text(i, total + 0.3, str(int(total)), ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_ylim(0, ct.sum(axis=1).max() + 2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=0)

    plt.tight_layout()
    save_figure(fig, "fig1_year_distribution")

    # Summary
    print("\n=== Figure 1 Summary ===")
    print(f"  Total papers: {len(df)}")
    print(f"  Year range: {df['Year'].min()}-{df['Year'].max()}")
    print(f"  Peak year: {ct.sum(axis=1).idxmax()} ({ct.sum(axis=1).max()} papers)")

    return fig


if __name__ == "__main__":
    import pandas as pd
    create_fig1()
