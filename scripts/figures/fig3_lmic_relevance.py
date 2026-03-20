"""
Figure 3: LMIC Relevance Analysis

Multi-panel figure showing LMIC relevance score distribution and its
relationship to key accessibility indicators.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mapper import load_data, save_figure, configure_matplotlib, LMIC_SCORE_COLORS

np.random.seed(42)


def create_fig3():
    configure_matplotlib()
    df = load_data()

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # --- Panel A: LMIC Score Distribution ---
    ax = axes[0, 0]
    score_counts = df["LMIC_Score"].value_counts().sort_index()
    colors = [LMIC_SCORE_COLORS.get(int(s), "#95a5a6") for s in score_counts.index]
    bars = ax.bar(score_counts.index.astype(int), score_counts.values, color=colors,
                  edgecolor="white", width=0.7)
    for bar, val in zip(bars, score_counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", fontsize=10, fontweight="bold")

    ax.set_xlabel("LMIC Relevance Score")
    ax.set_ylabel("Number of Papers")
    ax.set_title("A. LMIC Relevance Score Distribution")
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["1\nMinimal", "2\nLow", "3\nModerate", "4\nHigh", "5\nDirect"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # --- Panel B: Low-field mention by LMIC score ---
    ax = axes[0, 1]
    ct = pd.crosstab(df["LMIC_Score"], df["Low_Field_Norm"])
    ct = ct.reindex(columns=["Yes", "No"], fill_value=0)
    ct.plot(kind="bar", stacked=True, ax=ax, color=["#27ae60", "#e74c3c"],
            edgecolor="white", width=0.7)
    ax.set_xlabel("LMIC Relevance Score")
    ax.set_ylabel("Number of Papers")
    ax.set_title("B. Low-Field MRI Mention by LMIC Score")
    ax.legend(title="Low-Field\nMentioned")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.sca(ax)
    plt.xticks(rotation=0)

    # --- Panel C: Resource constraints by LMIC score ---
    ax = axes[1, 0]
    ct2 = pd.crosstab(df["LMIC_Score"], df["Resource_Constraints_Norm"])
    ct2 = ct2.reindex(columns=["Yes", "No"], fill_value=0)
    ct2.plot(kind="bar", stacked=True, ax=ax, color=["#2980b9", "#c0392b"],
             edgecolor="white", width=0.7)
    ax.set_xlabel("LMIC Relevance Score")
    ax.set_ylabel("Number of Papers")
    ax.set_title("C. Resource Constraints Addressed by LMIC Score")
    ax.legend(title="Resource\nAddressed")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.sca(ax)
    plt.xticks(rotation=0)

    # --- Panel D: Code availability and clinical validation by LMIC score ---
    ax = axes[1, 1]
    scores = sorted(df["LMIC_Score"].dropna().unique())
    code_pcts = []
    valid_pcts = []
    for s in scores:
        subset = df[df["LMIC_Score"] == s]
        n_sub = len(subset)
        code_pcts.append((subset["Code_Available_Norm"] == "Yes").sum() / n_sub * 100 if n_sub > 0 else 0)
        valid_pcts.append((subset["Clinical_Validation_Norm"] != "None").sum() / n_sub * 100 if n_sub > 0 else 0)

    x = np.arange(len(scores))
    width = 0.35
    ax.bar(x - width / 2, code_pcts, width, label="Code Available", color="#3498db", edgecolor="white")
    ax.bar(x + width / 2, valid_pcts, width, label="Clinical Validation", color="#e67e22", edgecolor="white")
    ax.set_xlabel("LMIC Relevance Score")
    ax.set_ylabel("% of Papers")
    ax.set_title("D. Code Availability & Clinical Validation by LMIC Score")
    ax.set_xticks(x)
    ax.set_xticklabels([int(s) for s in scores])
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    save_figure(fig, "fig3_lmic_relevance")

    # Summary
    scored = df["LMIC_Score"].dropna()
    print("\n=== Figure 3 Summary ===")
    print(f"  Papers scored: {len(scored)}/{len(df)}")
    print(f"  Median LMIC score: {scored.median():.0f}")
    print(f"  Score 4-5 (high relevance): {(scored >= 4).sum()} ({(scored >= 4).sum()/len(scored)*100:.1f}%)")
    print(f"  Low-field mentioned: {(df['Low_Field_Norm'] == 'Yes').sum()} papers")
    print(f"  Code available: {(df['Code_Available_Norm'] == 'Yes').sum()} papers")

    return fig


if __name__ == "__main__":
    create_fig3()
