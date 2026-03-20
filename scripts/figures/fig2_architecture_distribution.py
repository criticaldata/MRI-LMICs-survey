"""
Figure 2: AI Architecture Distribution

Horizontal bar chart of architecture types with nested application area breakdown.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mapper import load_data, save_figure, configure_matplotlib, ARCHITECTURE_COLORS, APPLICATION_COLORS

np.random.seed(42)


def create_fig2():
    configure_matplotlib()
    df = load_data()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [1, 1.3]})

    # --- Panel A: Architecture counts ---
    ax = axes[0]
    arch_counts = df["Architecture_Norm"].value_counts()
    colors = [ARCHITECTURE_COLORS.get(a, "#95a5a6") for a in arch_counts.index]

    bars = ax.barh(range(len(arch_counts)), arch_counts.values, color=colors, edgecolor="white")
    ax.set_yticks(range(len(arch_counts)))
    ax.set_yticklabels(arch_counts.index)
    ax.set_xlabel("Number of Papers")
    ax.set_title("A. AI Architecture Distribution")
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, v in enumerate(arch_counts.values):
        ax.text(v + 0.3, i, str(v), va="center", fontsize=9)

    # --- Panel B: Architecture x Application heatmap ---
    ax = axes[1]
    ct = pd.crosstab(df["Architecture_Norm"], df["Application_Norm"])
    # Sort by row and column totals
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]
    ct = ct[ct.sum().sort_values(ascending=False).index]

    import seaborn as sns
    sns.heatmap(ct, annot=True, fmt="d", cmap="YlOrRd", ax=ax,
                linewidths=0.5, linecolor="white", cbar_kws={"label": "Papers"})
    ax.set_title("B. Architecture by Application Area")
    ax.set_xlabel("Application Area")
    ax.set_ylabel("")

    plt.tight_layout()
    save_figure(fig, "fig2_architecture_distribution")

    # Summary
    print("\n=== Figure 2 Summary ===")
    print(f"  Most common architecture: {arch_counts.index[0]} ({arch_counts.values[0]} papers)")
    print(f"  Architecture types: {len(arch_counts)}")

    return fig


if __name__ == "__main__":
    create_fig2()
