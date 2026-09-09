"""Calculate ordinal weighted inter-rater agreement from a private workbook.

The input contains the 48 papers and the 11 individual reviewer ratings. It must
remain outside the public repository. The public outputs contain only aggregate
statistics and paper-level agreement, with no reviewer identities or ratings.

Because the study has 11 reviewers, the primary implementation is a generalized
weighted Fleiss kappa for ordinal categories. Pairwise weighted Cohen kappas are
also calculated for all 55 reviewer pairs and summarized descriptively.

Example:
    python scripts/analysis/statistical/run_weighted_kappa_from_private_xlsx.py \
        --input-xlsx C:/private/RECEIVED_SCORES.xlsx \
        --output-dir tables \
        --output-xlsx C:/private/MRI_LMICs_Weighted_Kappa_Results.xlsx
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from openpyxl import Workbook
from sklearn.metrics import cohen_kappa_score

try:
    from run_fleiss_kappa_from_private_xlsx import _read_matrix
except ModuleNotFoundError:  # pragma: no cover - supports direct module loading
    from scripts.analysis.statistical.run_fleiss_kappa_from_private_xlsx import _read_matrix


SUMMARY_NAME = "analysis_weighted_kappa_summary.csv"
ITEM_NAME = "analysis_weighted_kappa_item_agreement.csv"
WEIGHTINGS = ("linear", "quadratic")


def _weight_matrix(categories: Sequence[int], weighting: str) -> np.ndarray:
    if weighting not in WEIGHTINGS:
        raise ValueError(f"Unsupported weighting: {weighting}")
    if len(categories) < 2:
        raise ValueError("At least two ordinal categories are required")

    ranks = np.arange(len(categories), dtype=float)
    distance = np.abs(ranks[:, None] - ranks[None, :]) / (len(categories) - 1)
    if weighting == "linear":
        return 1.0 - distance
    return 1.0 - distance**2


def _weighted_summary(
    ratings: np.ndarray,
    *,
    categories: Sequence[int],
    analysis: str,
    weighting: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Return generalized weighted Fleiss agreement and paper-level rows.

    For each paper, observed agreement is the mean ordinal agreement weight
    across all ordered pairs of reviewers. Expected agreement uses the pooled
    category proportions. This is the direct multi-rater analogue of weighted
    kappa; it is not mislabeled as a two-rater Cohen kappa.
    """

    ratings = np.asarray(ratings, dtype=int)
    if ratings.ndim != 2 or ratings.shape[1] < 2:
        raise ValueError("ratings must be a 2-D matrix with at least two raters")
    categories = list(categories)
    if not np.isin(ratings, categories).all():
        raise ValueError("ratings contain values outside the declared categories")

    n_items, n_raters = ratings.shape
    weights = _weight_matrix(categories, weighting)
    counts = np.asarray(
        [[int(np.sum(row == category)) for category in categories] for row in ratings],
        dtype=float,
    )

    # Remove the n self-comparisons from the ordered-pair total.
    observed_by_item = (
        np.einsum("ic,cd,id->i", counts, weights, counts) - n_raters
    ) / (n_raters * (n_raters - 1))
    pooled = counts.sum(axis=0) / (n_items * n_raters)
    expected = float(pooled @ weights @ pooled)
    observed = float(observed_by_item.mean())
    denominator = 1.0 - expected
    kappa = float((observed - expected) / denominator) if denominator else float("nan")

    pairwise: list[float] = []
    for left in range(n_raters):
        for right in range(left + 1, n_raters):
            value = float(
                cohen_kappa_score(
                    ratings[:, left],
                    ratings[:, right],
                    labels=categories,
                    weights=weighting,
                )
            )
            pairwise.append(value)

    pairwise_array = np.asarray(pairwise, dtype=float)
    summary = {
        "Analysis": analysis,
        "Weighting": weighting,
        "Items": n_items,
        "Raters": n_raters,
        "Categories": ",".join(str(category) for category in categories),
        "Observed_weighted_agreement": observed,
        "Expected_weighted_agreement": expected,
        "Weighted_Fleiss_kappa": kappa,
        "Pairwise_Cohen_kappa_mean": float(pairwise_array.mean()),
        "Pairwise_Cohen_kappa_median": float(np.median(pairwise_array)),
        "Pairwise_Cohen_kappa_sd": float(pairwise_array.std(ddof=1)),
        "Pairwise_Cohen_kappa_min": float(pairwise_array.min()),
        "Pairwise_Cohen_kappa_max": float(pairwise_array.max()),
        "Pairwise_count": len(pairwise),
    }
    item_rows = [
        {
            "Analysis": analysis,
            "Weighting": weighting,
            "Paper": index,
            "Observed_weighted_agreement": float(observed_by_item[index - 1]),
        }
        for index in range(1, n_items + 1)
    ]
    return summary, item_rows


def _write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError(f"Cannot write empty output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_xlsx(path: Path, summary_rows: list[dict[str, object]], item_rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    item_sheet = workbook.create_sheet("Paper_Agreement")
    for sheet, rows in ((summary_sheet, summary_rows), (item_sheet, item_rows)):
        sheet.append(list(rows[0]))
        for row in rows:
            sheet.append([row[column] for column in rows[0]])
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-xlsx", type=Path)
    args = parser.parse_args()

    lmic, tr = _read_matrix(args.input_xlsx.resolve())
    summaries: list[dict[str, object]] = []
    item_rows: list[dict[str, object]] = []
    for name, ratings, categories in (
        ("LMIC_Relevance_Score", lmic, list(range(1, 6))),
        ("TR_Score", tr, list(range(0, 6))),
    ):
        for weighting in WEIGHTINGS:
            summary, items = _weighted_summary(
                ratings,
                categories=categories,
                analysis=name,
                weighting=weighting,
            )
            summaries.append(summary)
            item_rows.extend(items)

    output_dir = args.output_dir.resolve()
    summary_path = output_dir / SUMMARY_NAME
    item_path = output_dir / ITEM_NAME
    _write_csv(summary_path, summaries)
    _write_csv(item_path, item_rows)
    if args.output_xlsx:
        _write_xlsx(args.output_xlsx.resolve(), summaries, item_rows)

    print(
        json.dumps(
            {
                "items": 48,
                "raters": 11,
                "summary": str(summary_path),
                "item_agreement": str(item_path),
                "xlsx": str(args.output_xlsx.resolve()) if args.output_xlsx else None,
                "individual_ratings_written": False,
                "method": "generalized_weighted_fleiss_plus_pairwise_weighted_cohen_summary",
                "results": summaries,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
