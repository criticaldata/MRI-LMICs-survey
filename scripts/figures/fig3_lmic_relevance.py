"""
Figure 3: LMIC Relevance & Translational Gap Analysis

The paper's signature figure. Multi-panel:
  A. LMIC score distribution (styled horizontal bars)
  B. Accessibility indicators by LMIC score (grouped bars)
  C. Low-field mention by LMIC score
  D. Translational readiness summary
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mapper import load_data, save_figure, configure_matplotlib, panel_title

np.random.seed(42)

SCORE_PALETTE = {
    1: "#E74C3C",
    2: "#E67E22",
    3: "#F1C40F",
    4: "#2ECC71",
    5: "#1ABC9C",
}

SCORE_LABELS = {
    1: "Minimal",
    2: "Low",
    3: "Moderate",
    4: "High",
    5: "Direct LMIC\napplication",
}


def create_fig3():
    configure_matplotlib()
    df = load_data()
    scored = df.dropna(subset=["LMIC_Score"])

    fig = plt.figure(figsize=(15, 12))
    gs = gridspec.GridSpec(2, 2, hspace=0.45, wspace=0.3)

    # ========================
    # Panel A: LMIC Score Distribution (horizontal bars, ranked style)
    # ========================
    ax_a = fig.add_subplot(gs[0, 0])

    scores = [5, 4, 3, 2, 1]
    score_counts = [len(scored[scored["LMIC_Score"] == s]) for s in scores]
    colors = [SCORE_PALETTE[s] for s in scores]
    labels = [f"Score {s}\n{SCORE_LABELS[s]}" for s in scores]

    y_pos = np.arange(len(scores))
    bars = ax_a.barh(y_pos, score_counts, height=0.6, color=colors,
                     edgecolor="white", linewidth=1)

    for i, (bar, count) in enumerate(zip(bars, score_counts)):
        pct = count / len(scored) * 100
        if count >= 4:
            ax_a.text(count - 0.3, i, f"{count}  ({pct:.0f}%)",
                      ha="right", va="center", fontsize=10,
                      fontweight="bold", color="white")
        else:
            ax_a.text(count + 0.3, i, f"{count} ({pct:.0f}%)",
                      ha="left", va="center", fontsize=10,
                      fontweight="bold", color="#2C3E50")

    ax_a.set_yticks(y_pos)
    ax_a.set_yticklabels(labels, fontsize=9, fontweight="bold")
    ax_a.set_xlabel("Number of Papers", fontsize=10)
    panel_title(ax_a, "A.  LMIC Relevance Score Distribution",
                f"{len(scored)} papers scored on 1\u20135 scale")
    ax_a.spines["top"].set_visible(False)
    ax_a.spines["right"].set_visible(False)
    ax_a.tick_params(length=0)
    ax_a.grid(axis="x", linestyle="--", alpha=0.2)

    # ========================
    # Panel B: Accessibility Indicators by LMIC Score (grouped bars)
    # ========================
    ax_b = fig.add_subplot(gs[0, 1])

    indicators = {
        "Low-field\nMentioned": "Low_Field_Norm",
        "Resource\nAddressed": "Resource_Constraints_Norm",
        "Code\nAvailable": "Code_Available_Norm",
        "Clinical\nValidation": "Clinical_Validation_Norm",
    }
    indicator_colors = ["#2E86AB", "#A23B72", "#F18F01", "#44BBA4"]

    x = np.arange(5)  # scores 1-5
    bar_w = 0.18
    offsets = np.arange(len(indicators)) - (len(indicators) - 1) / 2

    for idx, (label, col) in enumerate(indicators.items()):
        pcts = []
        for s in [1, 2, 3, 4, 5]:
            subset = scored[scored["LMIC_Score"] == s]
            n_sub = len(subset)
            if n_sub == 0:
                pcts.append(0)
            elif col == "Clinical_Validation_Norm":
                pcts.append((subset[col] != "None").sum() / n_sub * 100)
            else:
                pcts.append((subset[col] == "Yes").sum() / n_sub * 100)
        ax_b.bar(x + offsets[idx] * bar_w, pcts, width=bar_w,
                 label=label, color=indicator_colors[idx],
                 edgecolor="white", linewidth=0.5)

    ax_b.set_xticks(x)
    ax_b.set_xticklabels(["1", "2", "3", "4", "5"], fontsize=10, fontweight="bold")
    ax_b.set_xlabel("LMIC Relevance Score", fontsize=10)
    ax_b.set_ylabel("% of Papers", fontsize=10)
    panel_title(ax_b, "B.  Accessibility Indicators by LMIC Score",
                "Percentage of papers meeting each criterion within score group")
    ax_b.legend(fontsize=7, ncol=2, loc="upper right", frameon=True,
                fancybox=True, edgecolor="#ddd")
    ax_b.spines["top"].set_visible(False)
    ax_b.spines["right"].set_visible(False)
    ax_b.tick_params(length=0)
    ax_b.set_ylim(0, 115)
    ax_b.grid(axis="y", linestyle="--", alpha=0.2)

    # ========================
    # Panel C: Field Strength by LMIC Score (stacked bars)
    # ========================
    ax_c = fig.add_subplot(gs[1, 0])

    fs_colors = {
        "Low-field": "#E74C3C",
        "Standard-field": "#3498DB",
        "Mixed": "#9B59B6",
        "High-field": "#2ECC71",
        "Not specified": "#BDC3C7",
    }

    fs_order = ["Low-field", "Standard-field", "Mixed", "High-field", "Not specified"]
    ct_fs = pd.crosstab(scored["LMIC_Score"], scored["Field_Strength_Norm"])
    ct_fs = ct_fs.reindex(index=[1, 2, 3, 4, 5], fill_value=0)
    ct_fs = ct_fs.reindex(columns=[c for c in fs_order if c in ct_fs.columns], fill_value=0)

    bottom = np.zeros(5)
    x = np.arange(5)
    for fs in ct_fs.columns:
        vals = ct_fs[fs].values
        ax_c.bar(x, vals, bottom=bottom, width=0.6, label=fs,
                 color=fs_colors.get(fs, "#bdc3c7"), edgecolor="white", linewidth=0.8)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v >= 2:
                ax_c.text(i, b + v / 2, str(int(v)), ha="center", va="center",
                          fontsize=8, fontweight="bold", color="white")
        bottom += vals

    ax_c.set_xticks(x)
    ax_c.set_xticklabels(["1", "2", "3", "4", "5"], fontsize=10, fontweight="bold")
    ax_c.set_xlabel("LMIC Relevance Score", fontsize=10)
    ax_c.set_ylabel("Number of Papers", fontsize=10)
    panel_title(ax_c, "C.  Field Strength Distribution by LMIC Score",
                "Low-field papers concentrate in high LMIC-relevance scores")
    ax_c.legend(fontsize=7, loc="upper right", frameon=True,
                fancybox=True, edgecolor="#ddd")
    ax_c.spines["top"].set_visible(False)
    ax_c.spines["right"].set_visible(False)
    ax_c.tick_params(length=0)
    ax_c.grid(axis="y", linestyle="--", alpha=0.2)

    # ========================
    # Panel D: Translational Readiness Summary (horizontal bar chart)
    # ========================
    ax_d = fig.add_subplot(gs[1, 1])

    # Summary indicators for the whole dataset
    n = len(df)
    summary = [
        ("Resource constraints\naddressed", (df["Resource_Constraints_Norm"] == "Yes").sum(), "#2E86AB"),
        ("Clinical validation\nreported", (df["Clinical_Validation_Norm"] != "None").sum(), "#A23B72"),
        ("High LMIC relevance\n(Score 4\u20135)", len(df[df["LMIC_Score"] >= 4]), "#2ECC71"),
        ("Low-field MRI\nmentioned", (df["Low_Field_Norm"] == "Yes").sum(), "#F18F01"),
        ("Code publicly\navailable", (df["Code_Available_Norm"] == "Yes").sum(), "#C73E1D"),
    ]

    labels, values, colors = zip(*summary)
    y_pos = np.arange(len(labels))

    bars = ax_d.barh(y_pos, values, height=0.55, color=colors,
                     edgecolor="white", linewidth=1)

    for i, (bar, val) in enumerate(zip(bars, values)):
        pct = val / n * 100
        ax_d.text(val + 0.5, i, f"{val}/{n} ({pct:.0f}%)",
                  va="center", fontsize=9, fontweight="bold", color="#2C3E50")

    ax_d.set_yticks(y_pos)
    ax_d.set_yticklabels(labels, fontsize=9, fontweight="bold")
    ax_d.invert_yaxis()
    ax_d.set_xlabel("Number of Papers", fontsize=10)
    panel_title(ax_d, "D.  Translational Readiness Overview",
                "Key indicators for LMIC deployment feasibility")
    ax_d.spines["top"].set_visible(False)
    ax_d.spines["right"].set_visible(False)
    ax_d.tick_params(length=0)
    ax_d.grid(axis="x", linestyle="--", alpha=0.2)
    ax_d.set_xlim(0, max(values) + 10)

    plt.tight_layout()
    save_figure(fig, "fig3_lmic_relevance")

    # Summary
    print("\n=== Figure 3 Summary ===")
    print(f"  Papers scored: {len(scored)}/{len(df)}")
    print(f"  Median LMIC score: {scored['LMIC_Score'].median():.0f}")
    print(f"  Score 4\u20135 (high): {(scored['LMIC_Score'] >= 4).sum()} ({(scored['LMIC_Score'] >= 4).sum()/len(scored)*100:.1f}%)")
    print(f"  Low-field mentioned: {(df['Low_Field_Norm'] == 'Yes').sum()}")
    print(f"  Code available: {(df['Code_Available_Norm'] == 'Yes').sum()}")
    print(f"  Clinical validation: {(df['Clinical_Validation_Norm'] != 'None').sum()}")

    return fig


if __name__ == "__main__":
    create_fig3()
