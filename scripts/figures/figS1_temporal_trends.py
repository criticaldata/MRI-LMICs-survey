"""
Supplementary Figure S1: Temporal Trends

2-panel figure:
  A. Stacked bar of LMIC scores by year
  B. Line chart: % low-field, % code available, % clinical validation per year
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mapper import (
    load_data, save_figure, configure_matplotlib, panel_title, get_project_root,
    LMIC_SCORE_COLORS,
)

np.random.seed(42)


def create_figS1():
    configure_matplotlib()
    df = load_data()
    scored = df.dropna(subset=["LMIC_Score"])

    years = sorted(df["Year"].dropna().unique())
    years_int = [int(y) for y in years]

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 5.5))

    # ========================
    # Panel A: Stacked bar of LMIC scores by year
    # ========================
    ct = pd.crosstab(scored["Year"], scored["LMIC_Score"])
    ct = ct.reindex(index=years, fill_value=0)
    ct = ct.reindex(columns=[1, 2, 3, 4, 5], fill_value=0)

    x = np.arange(len(years))
    bottom = np.zeros(len(years))
    bar_width = 0.65

    for score in [1, 2, 3, 4, 5]:
        vals = ct[score].values if score in ct.columns else np.zeros(len(years))
        ax_a.bar(x, vals, bottom=bottom, width=bar_width,
                 label=f"Score {score}", color=LMIC_SCORE_COLORS[score],
                 edgecolor="white", linewidth=0.8)
        # Label bars with count if >= 2
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v >= 2:
                ax_a.text(i, b + v / 2, str(int(v)), ha="center", va="center",
                          fontsize=8, fontweight="bold", color="white")
        bottom += vals

    ax_a.set_xticks(x)
    ax_a.set_xticklabels(years_int, rotation=45, ha="right")
    ax_a.set_xlabel("Publication Year")
    ax_a.set_ylabel("Number of Papers")
    panel_title(ax_a, "A.  LMIC Score Distribution by Year",
                "Stacked counts of LMIC relevance scores (1–5)")
    ax_a.legend(fontsize=8, loc="upper left", frameon=True,
                fancybox=True, edgecolor="#ddd")
    ax_a.spines["top"].set_visible(False)
    ax_a.spines["right"].set_visible(False)
    ax_a.tick_params(length=0)
    ax_a.grid(axis="y", linestyle="--", alpha=0.2)

    # ========================
    # Panel B: Line chart of % low-field, % code, % clinical validation
    # ========================
    pct_data = {"Year": [], "% Low-field": [], "% Code Available": [],
                "% Clinical Validation": []}

    for year in years:
        subset = df[df["Year"] == year]
        n = len(subset)
        if n == 0:
            continue
        pct_data["Year"].append(int(year))
        pct_data["% Low-field"].append(
            (subset["Low_Field_Norm"] == "Yes").sum() / n * 100
        )
        pct_data["% Code Available"].append(
            (subset["Code_Available_Norm"] == "Yes").sum() / n * 100
        )
        pct_data["% Clinical Validation"].append(
            (subset["Clinical_Validation_Norm"] != "None").sum() / n * 100
        )

    pct_df = pd.DataFrame(pct_data)

    line_styles = {
        "% Low-field": {"color": "#E74C3C", "marker": "o", "linestyle": "-"},
        "% Code Available": {"color": "#3498DB", "marker": "s", "linestyle": "--"},
        "% Clinical Validation": {"color": "#2ECC71", "marker": "^", "linestyle": "-."},
    }

    for metric, style in line_styles.items():
        ax_b.plot(pct_df["Year"], pct_df[metric], label=metric,
                  markersize=7, linewidth=2, **style)

    ax_b.set_xlabel("Publication Year")
    ax_b.set_ylabel("Percentage of Papers (%)")
    ax_b.set_xticks(years_int)
    ax_b.set_xticklabels(years_int, rotation=45, ha="right")
    ax_b.set_ylim(0, 105)
    panel_title(ax_b, "B.  Key Indicators Over Time",
                "Percentage of papers with low-field, code, and clinical validation")
    ax_b.legend(fontsize=9, loc="upper left", frameon=True,
                fancybox=True, edgecolor="#ddd")
    ax_b.spines["top"].set_visible(False)
    ax_b.spines["right"].set_visible(False)
    ax_b.tick_params(length=0)
    ax_b.grid(axis="y", linestyle="--", alpha=0.2)

    plt.tight_layout()
    save_figure(fig, "figS1_temporal_trends",
                output_dir=get_project_root() / "figures" / "supplementary")

    # Summary
    print("\n=== Figure S1 Summary ===")
    print(f"  Years covered: {years_int[0]}–{years_int[-1]}")
    print(f"  Total papers: {len(df)}")
    print(f"  Papers with LMIC score: {len(scored)}")
    print(f"  Overall % low-field: {(df['Low_Field_Norm'] == 'Yes').sum() / len(df) * 100:.1f}%")
    print(f"  Overall % code available: {(df['Code_Available_Norm'] == 'Yes').sum() / len(df) * 100:.1f}%")
    print(f"  Overall % clinical validation: {(df['Clinical_Validation_Norm'] != 'None').sum() / len(df) * 100:.1f}%")

    return fig


if __name__ == "__main__":
    create_figS1()
