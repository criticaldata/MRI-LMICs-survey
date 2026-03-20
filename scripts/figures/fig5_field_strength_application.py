"""
Figure 5: Field Strength and Application Area Overview

Heatmap and stacked bars showing the intersection of MRI application areas,
field strengths, and LMIC relevance.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mapper import (load_data, save_figure, configure_matplotlib,
                    APPLICATION_COLORS, FIELD_STRENGTH_COLORS, LMIC_SCORE_COLORS)

np.random.seed(42)


def create_fig5():
    configure_matplotlib()
    df = load_data()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.2, 1]})

    # --- Panel A: Application x Field Strength heatmap ---
    ax = axes[0]
    ct = pd.crosstab(df["Application_Norm"], df["Field_Strength_Norm"])
    # Sort rows by total
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]
    # Reorder columns
    col_order = ["Low-field", "Standard-field", "High-field", "Mixed", "Not specified"]
    ct = ct.reindex(columns=[c for c in col_order if c in ct.columns], fill_value=0)

    sns.heatmap(ct, annot=True, fmt="d", cmap="YlOrRd", ax=ax,
                linewidths=0.5, linecolor="white", cbar_kws={"label": "Papers"})
    ax.set_title("A. Application Area by Field Strength")
    ax.set_xlabel("Field Strength")
    ax.set_ylabel("Application Area")

    # --- Panel B: Application area colored by median LMIC score ---
    ax = axes[1]
    app_lmic = df.groupby("Application_Norm").agg(
        n_papers=("Paper_ID", "count"),
        median_lmic=("LMIC_Score", "median"),
    ).sort_values("n_papers", ascending=True)

    colors = []
    for score in app_lmic["median_lmic"]:
        if pd.isna(score):
            colors.append("#bdc3c7")
        else:
            colors.append(LMIC_SCORE_COLORS.get(int(round(score)), "#bdc3c7"))

    bars = ax.barh(range(len(app_lmic)), app_lmic["n_papers"], color=colors, edgecolor="white")
    ax.set_yticks(range(len(app_lmic)))
    ax.set_yticklabels(app_lmic.index)
    ax.set_xlabel("Number of Papers")
    ax.set_title("B. Application Areas (colored by median LMIC score)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add LMIC score annotations
    for i, (_, row) in enumerate(app_lmic.iterrows()):
        score_str = f"{row['median_lmic']:.0f}" if not pd.isna(row['median_lmic']) else "?"
        ax.text(row['n_papers'] + 0.3, i, f"n={int(row['n_papers'])}, LMIC={score_str}",
                va="center", fontsize=8)

    plt.tight_layout()
    save_figure(fig, "fig5_field_strength_application")

    # Summary
    print("\n=== Figure 5 Summary ===")
    print(f"  Application areas: {df['Application_Norm'].nunique()}")
    print(f"  Low-field papers: {(df['Field_Strength_Norm'] == 'Low-field').sum()}")
    print(f"  Standard-field papers: {(df['Field_Strength_Norm'] == 'Standard-field').sum()}")

    return fig


if __name__ == "__main__":
    create_fig5()
