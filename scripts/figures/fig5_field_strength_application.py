"""
Figure 5: Field Strength and Application Area Overview

Multi-panel:
  A. Application x Field Strength heatmap
  B. Application areas ranked by paper count, colored by median LMIC score
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from mapper import load_data, save_figure, configure_matplotlib, LMIC_SCORE_COLORS

np.random.seed(42)


def create_fig5():
    configure_matplotlib()
    df = load_data()

    fig = plt.figure(figsize=(15, 7))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.3, 1], wspace=0.3)

    # ========================
    # Panel A: Application x Field Strength heatmap
    # ========================
    ax_a = fig.add_subplot(gs[0])

    ct = pd.crosstab(df["Application_Norm"], df["Field_Strength_Norm"])
    row_order = ct.sum(axis=1).sort_values(ascending=False).index
    col_order = ["Low-field", "Standard-field", "High-field", "Mixed", "Not specified"]
    ct = ct.reindex(index=row_order)
    ct = ct.reindex(columns=[c for c in col_order if c in ct.columns], fill_value=0)

    mask = ct == 0
    cmap = sns.color_palette("YlOrRd", as_cmap=True)

    sns.heatmap(ct, annot=True, fmt="d", cmap=cmap, ax=ax_a, mask=mask,
                linewidths=1.5, linecolor="white",
                cbar_kws={"label": "Papers", "shrink": 0.6},
                annot_kws={"fontsize": 11, "fontweight": "bold"},
                square=False)

    # Dot for zeros
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            if ct.iloc[i, j] == 0:
                ax_a.text(j + 0.5, i + 0.5, "\u00b7", ha="center", va="center",
                          fontsize=16, color="#ddd")

    ax_a.set_title("A.  Application Area by Field Strength", fontsize=12,
                    fontweight="bold", loc="left", pad=12)
    ax_a.text(0, 1.03, "Distribution of studies across MRI applications and field strengths",
              transform=ax_a.transAxes, fontsize=9, color="#7f8c8d", style="italic")
    ax_a.set_xlabel("Field Strength", fontsize=10)
    ax_a.set_ylabel("")
    ax_a.tick_params(length=0)
    plt.setp(ax_a.get_xticklabels(), rotation=25, ha="right", fontsize=9)
    plt.setp(ax_a.get_yticklabels(), fontsize=9.5)

    # ========================
    # Panel B: Application areas ranked, colored by LMIC
    # ========================
    ax_b = fig.add_subplot(gs[1])

    app_stats = df.groupby("Application_Norm").agg(
        n=("Paper_ID", "count"),
        median_lmic=("LMIC_Score", "median"),
        low_field_pct=("Low_Field_Norm", lambda x: (x == "Yes").sum() / len(x) * 100),
    ).sort_values("n", ascending=True)

    colors = []
    for score in app_stats["median_lmic"]:
        if pd.isna(score):
            colors.append("#BDC3C7")
        else:
            colors.append(LMIC_SCORE_COLORS.get(int(round(score)), "#BDC3C7"))

    y_pos = np.arange(len(app_stats))
    bars = ax_b.barh(y_pos, app_stats["n"], height=0.6, color=colors,
                     edgecolor="white", linewidth=0.8)

    for i, (idx, row) in enumerate(app_stats.iterrows()):
        lmic_str = f"{row['median_lmic']:.0f}" if not pd.isna(row["median_lmic"]) else "?"
        lf_str = f"{row['low_field_pct']:.0f}%"
        label = f"n={int(row['n'])}  |  LMIC={lmic_str}  |  LF={lf_str}"
        ax_b.text(row["n"] + 0.3, i, label, va="center", fontsize=8, color="#2C3E50")

    ax_b.set_yticks(y_pos)
    ax_b.set_yticklabels(app_stats.index, fontsize=9.5, fontweight="bold")
    ax_b.set_xlabel("Number of Papers", fontsize=10)
    ax_b.set_title("B.  Application Areas by LMIC Relevance", fontsize=12,
                    fontweight="bold", loc="left", pad=12)
    ax_b.text(0, 1.03, "Bar color = median LMIC score  |  LF = % mentioning low-field",
              transform=ax_b.transAxes, fontsize=9, color="#7f8c8d", style="italic")
    ax_b.spines["top"].set_visible(False)
    ax_b.spines["right"].set_visible(False)
    ax_b.tick_params(length=0)
    ax_b.grid(axis="x", linestyle="--", alpha=0.2)
    ax_b.set_xlim(0, app_stats["n"].max() + 12)

    # Color legend for LMIC scores
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=LMIC_SCORE_COLORS[s], label=f"LMIC {s}")
                       for s in [1, 2, 3, 4, 5]]
    ax_b.legend(handles=legend_elements, fontsize=7.5, loc="lower right",
                title="Median Score", title_fontsize=8, frameon=True,
                fancybox=True, edgecolor="#ddd", ncol=1)

    plt.tight_layout()
    save_figure(fig, "fig5_field_strength_application")

    print("\n=== Figure 5 Summary ===")
    print(f"  Application areas: {df['Application_Norm'].nunique()}")
    print(f"  Low-field papers: {(df['Field_Strength_Norm'] == 'Low-field').sum()}")
    print(f"  Standard-field: {(df['Field_Strength_Norm'] == 'Standard-field').sum()}")
    print(f"  Not specified: {(df['Field_Strength_Norm'] == 'Not specified').sum()}")
    print(f"  Brain (most common): {(df['Application_Norm'] == 'Brain').sum()} papers")

    return fig


if __name__ == "__main__":
    create_fig5()
