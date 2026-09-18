"""Calculate intraclass correlation coefficients from a private score workbook.

The input contains the 48 papers and 11 individual reviewer ratings. It remains
outside the public repository. The public output contains aggregate ANOVA
components and ICC estimates only.

The primary model is ICC(2,1): two-way random effects, absolute agreement,
single measurement. ICC(2,k) is also reported for the reliability of the mean
rating across all 11 reviewers. Consistency ICCs are included as diagnostics,
not as the primary result.

Example:
    python scripts/analysis/statistical/run_icc_from_private_xlsx.py \
        --input-xlsx C:/private/RECEIVED_SCORES.xlsx \
        --output-dir tables \
        --output-xlsx C:/private/MRI_LMICs_ICC_Results.xlsx
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from openpyxl import Workbook

try:
    from run_fleiss_kappa_from_private_xlsx import _read_matrix
except ModuleNotFoundError:  # pragma: no cover - supports direct module loading
    from scripts.analysis.statistical.run_fleiss_kappa_from_private_xlsx import _read_matrix


SUMMARY_NAME = "analysis_icc_summary.csv"


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def _icc_summary(ratings: np.ndarray, *, analysis: str) -> dict[str, object]:
    """Calculate two-way absolute-agreement and consistency ICC estimates."""

    ratings = np.asarray(ratings, dtype=float)
    if ratings.ndim != 2 or ratings.shape[0] < 2 or ratings.shape[1] < 2:
        raise ValueError("ratings must have at least two papers and two raters")

    n_items, n_raters = ratings.shape
    grand_mean = float(ratings.mean())
    item_means = ratings.mean(axis=1)
    rater_means = ratings.mean(axis=0)
    ss_items = n_raters * float(np.sum((item_means - grand_mean) ** 2))
    ss_raters = n_items * float(np.sum((rater_means - grand_mean) ** 2))
    residuals = ratings - item_means[:, None] - rater_means[None, :] + grand_mean
    ss_error = float(np.sum(residuals**2))

    ms_items = ss_items / (n_items - 1)
    ms_raters = ss_raters / (n_raters - 1)
    ms_error = ss_error / ((n_items - 1) * (n_raters - 1))

    # Shrout and Fleiss ICC(2,1) and ICC(2,k): absolute agreement.
    icc_2_1 = _safe_ratio(
        ms_items - ms_error,
        ms_items
        + (n_raters - 1) * ms_error
        + n_raters * (ms_raters - ms_error) / n_items,
    )
    icc_2_k = _safe_ratio(
        ms_items - ms_error,
        ms_items + (ms_raters - ms_error) / n_items,
    )

    # ICC(3,1) and ICC(3,k): consistency diagnostics.
    icc_3_1 = _safe_ratio(ms_items - ms_error, ms_items + (n_raters - 1) * ms_error)
    icc_3_k = _safe_ratio(ms_items - ms_error, ms_items)

    return {
        "Analysis": analysis,
        "Items": n_items,
        "Raters": n_raters,
        "ICC_Model_Primary": "ICC(2,1): two-way random, absolute agreement, single measurement",
        "ICC_2_1_absolute_agreement": icc_2_1,
        "ICC_2_k_absolute_agreement": icc_2_k,
        "ICC_3_1_consistency_diagnostic": icc_3_1,
        "ICC_3_k_consistency_diagnostic": icc_3_k,
        "MS_Items": ms_items,
        "MS_Raters": ms_raters,
        "MS_Error": ms_error,
    }


def _write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError(f"Cannot write empty output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_xlsx(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ICC_Summary"
    columns = list(rows[0])
    sheet.append(columns)
    for row in rows:
        sheet.append([row[column] for column in columns])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-xlsx", type=Path)
    parser.add_argument("--canonical-data", type=Path)
    args = parser.parse_args()

    lmic, tr = _read_matrix(
        args.input_xlsx.resolve(),
        args.canonical_data.resolve() if args.canonical_data else None,
    )
    rows = [
        _icc_summary(lmic, analysis="LMIC_Relevance_Score"),
        _icc_summary(tr, analysis="TR_Score"),
    ]
    output_dir = args.output_dir.resolve()
    summary_path = output_dir / SUMMARY_NAME
    _write_csv(summary_path, rows)
    if args.output_xlsx:
        _write_xlsx(args.output_xlsx.resolve(), rows)

    print(
        json.dumps(
            {
                "items": 48,
                "raters": 11,
                "summary": str(summary_path),
                "xlsx": str(args.output_xlsx.resolve()) if args.output_xlsx else None,
                "individual_ratings_written": False,
                "primary_model": "ICC(2,1) absolute agreement",
                "results": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
