"""Supplementary Figure S1: primary 2020-2024 trends and preliminary 2025 markers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mapper import (
    LMIC_SCORE_COLORS,
    configure_matplotlib,
    get_project_root,
    load_data,
    panel_title,
    save_figure,
)


PRIMARY_YEAR_START = 2020
PRIMARY_YEAR_END = 2024
PRELIMINARY_YEAR = 2025


def _indicator_percentages(df: pd.DataFrame) -> dict[str, float]:
    n = len(df)
    return {
        "% Low-field": (df["Low_Field_Norm"] == "Yes").sum() / n * 100,
        "% Code Available": (df["Code_Available_Norm"] == "Yes").sum() / n * 100,
        "% Clinical Validation": (df["Clinical_Validation_Norm"] != "None").sum() / n * 100,
    }


def create_figS1():
    """Render the full-year trend and distinguish incomplete 2025 observations."""
    configure_matplotlib()
    data = load_data()
    primary = data.loc[data["Year"].between(PRIMARY_YEAR_START, PRIMARY_YEAR_END)].copy()
    preliminary = data.loc[data["Year"] == PRELIMINARY_YEAR].copy()
    scored = primary.dropna(subset=["LMIC_Score"])
    years = sorted(primary["Year"].dropna().astype(int).unique())

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 5.5))

    score_counts = pd.crosstab(scored["Year"], scored["LMIC_Score"])
    score_counts = score_counts.reindex(index=years, columns=[1, 2, 3, 4, 5], fill_value=0)
    x = np.arange(len(years))
    bottom = np.zeros(len(years))
    for score in [1, 2, 3, 4, 5]:
        values = score_counts[score].to_numpy()
        ax_a.bar(x, values, bottom=bottom, width=0.65, label=f"Score {score}",
                 color=LMIC_SCORE_COLORS[score], edgecolor="white", linewidth=0.8)
        bottom += values
    ax_a.set_xticks(x, labels=years)
    ax_a.set_xlabel("Publication year")
    ax_a.set_ylabel("Number of papers")
    panel_title(
        ax_a,
        "A. LMIC score distribution by year",
        "Primary full-year analysis, 2020-2024",
    )
    ax_a.legend(fontsize=8, loc="upper left", frameon=True, edgecolor="#dddddd")
    ax_a.text(
        0.5,
        -0.20,
        f"2025 preliminary data (n={len(preliminary)}) are reported separately and are not included here.",
        transform=ax_a.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color="#555555",
    )
    ax_a.spines[["top", "right"]].set_visible(False)
    ax_a.tick_params(length=0)
    ax_a.grid(axis="y", linestyle="--", alpha=0.2)

    series_styles = {
        "% Low-field": {"color": "#E74C3C", "marker": "o", "linestyle": "-"},
        "% Code Available": {"color": "#2E86AB", "marker": "s", "linestyle": "--"},
        "% Clinical Validation": {"color": "#F18F01", "marker": "^", "linestyle": "-."},
    }
    yearly = []
    for year in years:
        yearly.append({"Year": year, **_indicator_percentages(primary.loc[primary["Year"] == year])})
    primary_percentages = pd.DataFrame(yearly)
    for metric, style in series_styles.items():
        ax_b.plot(primary_percentages["Year"], primary_percentages[metric], label=metric,
                  markersize=7, linewidth=2, **style)
    if not preliminary.empty:
        preliminary_percentages = _indicator_percentages(preliminary)
        marker_offsets = {"% Low-field": -0.08, "% Code Available": 0.0, "% Clinical Validation": 0.08}
        for metric, style in series_styles.items():
            ax_b.plot(
                [PRELIMINARY_YEAR + marker_offsets[metric]],
                [preliminary_percentages[metric]],
                marker=style["marker"],
                markersize=7,
                markerfacecolor="white",
                markeredgecolor=style["color"],
                markeredgewidth=1.5,
                linestyle="None",
            )
        ax_b.annotate(
            f"2025 preliminary (n={len(preliminary)})",
            (PRELIMINARY_YEAR, 92),
            xytext=(0, 0),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color="#555555",
        )
    ax_b.set_xticks(years + [PRELIMINARY_YEAR], labels=years + ["2025\npreliminary"])
    ax_b.set_xlabel("Publication year")
    ax_b.set_ylabel("Percentage of papers")
    ax_b.set_ylim(0, 105)
    panel_title(
        ax_b,
        "B. Key indicators over time",
        "Lines: primary full-year analysis (2020-2024); open markers: preliminary 2025",
    )
    ax_b.legend(fontsize=8, loc="upper left", frameon=True, edgecolor="#dddddd")
    ax_b.spines[["top", "right"]].set_visible(False)
    ax_b.tick_params(length=0)
    ax_b.grid(axis="y", linestyle="--", alpha=0.2)

    plt.tight_layout()
    save_figure(fig, "figS1_temporal_trends", output_dir=get_project_root() / "figures" / "supplementary")
    return fig


if __name__ == "__main__":
    create_figS1()
