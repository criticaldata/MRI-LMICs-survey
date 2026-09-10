"""Calculate the final reviewer agreement from a private scoring workbook.

The workbook contains individual reviewer ratings and must remain outside the
public repository.  This command validates the 48-by-11 matrix and writes only
aggregate Fleiss' kappa results and paper-level agreement summaries.

Example:
    python scripts/analysis/statistical/run_fleiss_kappa_from_private_xlsx.py \
        --input-xlsx C:/private/RECEIVED_SCORES.xlsx \
        --output-dir tables
"""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from openpyxl import load_workbook
from statsmodels.stats.inter_rater import fleiss_kappa


EXPECTED_ITEMS = 48
EXPECTED_RATERS = 11
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CANONICAL_DATA = REPO_ROOT / "data" / "data-clean.csv"
SUMMARY_NAME = "analysis_fleiss_kappa_summary.csv"
ITEM_NAME = "analysis_fleiss_kappa_item_agreement.csv"


def _as_int(value: object, *, paper: int, reviewer: int, scale: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Missing or non-numeric {scale} score for paper {paper}, "
            f"reviewer {reviewer}"
        )
    if int(value) != value:
        raise ValueError(f"Non-integer {scale} score for paper {paper}, reviewer {reviewer}")
    return int(value)


def _normalize_title(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = text.translate(str.maketrans({"–": "-", "—": "-", "’": "'", "‘": "'"}))
    return " ".join(text.replace("\u00a0", " ").split()).casefold()


def _canonical_titles(path: Path) -> list[str]:
    import pandas as pd

    if not path.exists():
        raise FileNotFoundError(f"Canonical study data not found: {path}")
    frame = pd.read_csv(path)
    required = {"Paper_ID", "Title"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Canonical study data must contain {sorted(required)}")
    frame = frame.copy()
    frame["Paper_ID"] = pd.to_numeric(frame["Paper_ID"], errors="raise").astype(int)
    if len(frame) != EXPECTED_ITEMS or frame["Paper_ID"].tolist() != list(range(1, EXPECTED_ITEMS + 1)):
        raise ValueError("Canonical study data must contain Paper_ID values 1-48 in order")
    titles = [_normalize_title(value) for value in frame["Title"]]
    if not all(titles) or len(set(titles)) != EXPECTED_ITEMS:
        raise ValueError("Canonical study titles must be non-empty and unique")
    return titles


def _read_matrix(
    path: Path,
    canonical_data: Path | None = None,
    *,
    include_titles: bool = False,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Private reviewer workbook not found: {path}")

    workbook = load_workbook(path, data_only=True, read_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) != EXPECTED_ITEMS + 2:
        raise ValueError(
            f"Expected {EXPECTED_ITEMS} papers plus two header rows; found {len(rows)} rows"
        )
    if len(rows[0]) < 3 or rows[0][0] is not None or rows[1][0] != "PAPER":
        raise ValueError("Unexpected reviewer workbook header")

    score_columns: list[tuple[int, int, str]] = []
    for lm_col in range(3, len(rows[1]), 2):
        tr_col = lm_col + 1
        if tr_col >= len(rows[1]):
            break
        reviewer = rows[0][lm_col]
        lm_header = rows[1][lm_col]
        tr_header = rows[1][tr_col]
        if not reviewer or "LMIC" not in str(lm_header) or "TR" not in str(tr_header):
            continue
        score_columns.append((lm_col, tr_col, str(reviewer)))

    if len(score_columns) != EXPECTED_RATERS:
        raise ValueError(
            f"Expected {EXPECTED_RATERS} reviewer pairs; found {len(score_columns)}"
        )

    canonical_titles = _canonical_titles(canonical_data or DEFAULT_CANONICAL_DATA)

    lmic: list[list[int]] = []
    tr: list[list[int]] = []
    for row_offset, row in enumerate(rows[2:], start=1):
        paper = row[0]
        if paper != row_offset:
            raise ValueError(f"Paper rows must be ordered 1-{EXPECTED_ITEMS}; found {paper}")
        workbook_title = _normalize_title(row[1])
        if workbook_title != canonical_titles[row_offset - 1]:
            raise ValueError(
                f"Paper {row_offset} title does not match canonical study order: "
                f"{row[1]!r}"
            )
        lmic.append(
            [
                _as_int(row[lm_col], paper=row_offset, reviewer=i, scale="LMIC")
                for i, (lm_col, _, _) in enumerate(score_columns, start=1)
            ]
        )
        tr.append(
            [
                _as_int(row[tr_col], paper=row_offset, reviewer=i, scale="TR")
                for i, (_, tr_col, _) in enumerate(score_columns, start=1)
            ]
        )

    lmic_array = np.asarray(lmic, dtype=int)
    tr_array = np.asarray(tr, dtype=int)
    if not np.all((1 <= lmic_array) & (lmic_array <= 5)):
        raise ValueError("LMIC scores must be integers from 1 to 5")
    if not np.all((0 <= tr_array) & (tr_array <= 5)):
        raise ValueError("TR scores must be integers from 0 to 5")
    if include_titles:
        return lmic_array, tr_array, canonical_titles
    return lmic_array, tr_array


def _agreement_rows(
    ratings: np.ndarray,
    categories: Sequence[int],
    analysis: str,
    titles: Sequence[str] | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    n_items, n_raters = ratings.shape
    counts = np.asarray(
        [[int(np.sum(row == category)) for category in categories] for row in ratings],
        dtype=int,
    )
    kappa = float(fleiss_kappa(counts, method="fleiss"))
    pair_agreement = (np.sum(counts**2, axis=1) - n_raters) / (
        n_raters * (n_raters - 1)
    )
    majority = counts.max(axis=1) / n_raters
    p_bar = float(pair_agreement.mean())
    p_e = float(np.square(counts.sum(axis=0) / (n_items * n_raters)).sum())
    summary = {
        "Analysis": analysis,
        "Items": n_items,
        "Raters": n_raters,
        "Fleiss_kappa": kappa,
        "Observed_agreement_P_bar": p_bar,
        "Expected_agreement_P_e": p_e,
        "Mean_majority_share": float(majority.mean()),
        "Unanimous_items": int(np.sum(counts.max(axis=1) == n_raters)),
        "Category_counts": "; ".join(
            f"{category}={int(counts[:, index].sum())}"
            for index, category in enumerate(categories)
        ),
    }
    item_rows = []
    for index, row_counts in enumerate(counts, start=1):
        max_count = int(row_counts.max())
        modal = [
            str(category)
            for category, count in zip(categories, row_counts)
            if count == max_count
        ]
        item = {
                "Analysis": analysis,
                "Paper_ID": index,
                "Mean_pairwise_agreement": float(pair_agreement[index - 1]),
                "Majority_share": float(majority[index - 1]),
                "Modal_score": "/".join(modal),
                "Unanimous": bool(max_count == n_raters),
        }
        if titles is not None:
            item["Title"] = titles[index - 1]
        item_rows.append(item)
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--canonical-data", type=Path, default=DEFAULT_CANONICAL_DATA)
    args = parser.parse_args()

    lmic, tr, titles = _read_matrix(
        args.input_xlsx.resolve(), args.canonical_data.resolve(), include_titles=True
    )
    summaries = []
    item_rows = []
    for name, ratings, categories in (
        ("LMIC_Relevance_Score", lmic, list(range(1, 6))),
        ("TR_Score", tr, list(range(0, 6))),
    ):
        summary, items = _agreement_rows(ratings, categories, name, titles)
        summaries.append(summary)
        item_rows.extend(items)

    output_dir = args.output_dir.resolve()
    summary_path = output_dir / SUMMARY_NAME
    item_path = output_dir / ITEM_NAME
    _write_csv(summary_path, summaries)
    _write_csv(item_path, item_rows)
    print(
        json.dumps(
            {
                "items": EXPECTED_ITEMS,
                "raters": EXPECTED_RATERS,
                "summary": str(summary_path),
                "item_agreement": str(item_path),
                "results": summaries,
                "individual_ratings_written": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
