"""Render aggregate-only reviewer score distributions from a private workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from mapper import configure_matplotlib, save_figure


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis" / "statistical"))
from run_fleiss_kappa_from_private_xlsx import (  # noqa: E402
    EXPECTED_RATERS,
    _agreement_rows,
    _read_matrix,
)


COUNT_CMAP = ListedColormap(
    ["#F8FAFC", "#E8F1F8", "#D1E3F1", "#B7D3E8", "#91BDDA", "#6FA6CB",
     "#4E90BC", "#3779AA", "#286396", "#1D4F7F", "#123B65", "#082B4C"]
)


def score_count_matrix(ratings: np.ndarray, categories: list[int]) -> np.ndarray:
    values = np.asarray(ratings, dtype=int)
    if values.ndim != 2:
        raise ValueError("Reviewer scores must be an item-by-rater matrix")
    counts = np.asarray(
        [[int(np.sum(row == category)) for category in categories] for row in values],
        dtype=int,
    )
    if not np.all(counts.sum(axis=1) == values.shape[1]):
        raise ValueError("Each paper must have one valid score from every reviewer")
    return counts


def _panel(ax, counts, categories, label, kappa, observed, *, show_y):
    image = ax.imshow(counts, cmap=COUNT_CMAP, vmin=0, vmax=EXPECTED_RATERS,
                      aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(categories)))
    ax.set_xticklabels(categories, fontweight="bold")
    ax.set_xlabel("Assigned score", fontweight="bold")
    ax.set_yticks(np.arange(counts.shape[0]))
    ax.set_yticklabels([f"P{i:02d}" for i in range(1, counts.shape[0] + 1)], fontsize=6.4)
    ax.set_ylabel("Scoring form ID" if show_y else "")
    ax.set_title(f"{label}\nFleiss' $\\kappa$ = {kappa:.3f}; observed agreement = {observed:.3f}",
                 fontsize=11, fontweight="bold", pad=13)
    ax.tick_params(axis="both", length=0)
    for row in range(counts.shape[0]):
        for column in range(counts.shape[1]):
            value = int(counts[row, column])
            ax.text(column, row, str(value), ha="center", va="center", fontsize=6.2,
                    color="white" if value >= 7 else "#193548")
    colorbar = ax.figure.colorbar(image, ax=ax, fraction=0.036, pad=0.025)
    colorbar.set_label("Number of reviewers", fontsize=8.5)
    colorbar.set_ticks(range(EXPECTED_RATERS + 1))
    colorbar.ax.tick_params(labelsize=7, length=2)


def create_figure(private_workbook: Path, canonical_data: Path, output_dir: Path):
    lmic, tr = _read_matrix(
        private_workbook, canonical_data, include_excluded_items=True
    )
    expected = (48, EXPECTED_RATERS)
    if lmic.shape != expected or tr.shape != expected:
        raise ValueError("Reviewer matrices must match all 48 scored form records and 11 reviewers")

    lmic_categories = list(range(1, 6))
    tr_categories = list(range(0, 6))
    lmic_summary, _ = _agreement_rows(lmic, lmic_categories, "LMIC_Relevance_Score")
    tr_summary, _ = _agreement_rows(tr, tr_categories, "TR_Score")
    configure_matplotlib()
    figure, axes = plt.subplots(1, 2, figsize=(12.5, max(12, 0.30 * expected[0])), sharey=True)
    figure.suptitle("Supplementary Figure 3. Full-corpus reviewer score distributions",
                    fontsize=16, fontweight="bold", color="#15324A", y=0.985)
    figure.text(0.5, 0.962,
                "All 48 scoring-form records rated by 11 reviewers; 3 were later excluded from the final synthesis",
                ha="center", fontsize=10.5, color="#52616B")
    _panel(axes[0], score_count_matrix(lmic, lmic_categories), lmic_categories,
           "A. LMIC Relevance Score (1–5)", float(lmic_summary["Fleiss_kappa"]),
           float(lmic_summary["Observed_agreement_P_bar"]), show_y=True)
    _panel(axes[1], score_count_matrix(tr, tr_categories), tr_categories,
           "B. Translational Readiness Score (0–5)", float(tr_summary["Fleiss_kappa"]),
           float(tr_summary["Observed_agreement_P_bar"]), show_y=False)
    figure.text(0.5, 0.012,
                "Each cell is an aggregate count across 11 reviewers. All rated candidates are retained for reliability; no individual ratings or reviewer identities are displayed.",
                ha="center", fontsize=8.5, color="#52616B")
    figure.tight_layout(rect=(0.02, 0.035, 0.98, 0.94))
    save_figure(figure, "figS3_reviewer_score_distributions", output_dir=output_dir)
    return figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument("--canonical-data", type=Path, default=REPO / "data/data-clean.csv")
    parser.add_argument("--output-dir", type=Path, default=REPO / "figures/supplementary")
    args = parser.parse_args()
    create_figure(args.input_xlsx.resolve(), args.canonical_data.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()
