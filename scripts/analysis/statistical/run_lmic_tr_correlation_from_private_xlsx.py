"""Calculate reviewer-consensus LMIC--TR correlation from a private workbook.

The private workbook is supplied as an external CLI argument. It is validated
as an exact 48-paper by 11-rater matrix before any output is created. The only
written artifact is an aggregate correlation summary; reviewer identities,
individual ratings, workbook paths, and per-paper medians are never written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from review_metrics import spearman_inference  # noqa: E402

try:
    from run_fleiss_kappa_from_private_xlsx import (  # noqa: E402
        DEFAULT_CANONICAL_DATA,
        EXPECTED_ITEMS,
        EXPECTED_RATERS,
        _read_matrix,
    )
except ModuleNotFoundError:  # pragma: no cover - supports module loading
    from scripts.analysis.statistical.run_fleiss_kappa_from_private_xlsx import (  # noqa: E402
        DEFAULT_CANONICAL_DATA,
        EXPECTED_ITEMS,
        EXPECTED_RATERS,
        _read_matrix,
    )


SUMMARY_NAME = "analysis_lmic_tr_correlation_reviewer_consensus.csv"
AGGREGATION = "per-paper median of 11 complete raters"


def _consensus_summary(lmic: np.ndarray, tr: np.ndarray) -> dict[str, object]:
    if lmic.shape != (EXPECTED_ITEMS, EXPECTED_RATERS):
        raise ValueError("LMIC ratings must form an exact 48-paper by 11-rater matrix")
    if tr.shape != (EXPECTED_ITEMS, EXPECTED_RATERS):
        raise ValueError("TR ratings must form an exact 48-paper by 11-rater matrix")
    lmic_median = np.median(lmic, axis=1)
    tr_median = np.median(tr, axis=1)
    inference = spearman_inference(
        pd.Series(lmic_median),
        pd.Series(tr_median),
        permutations=10_000,
        bootstrap_replicates=10_000,
        seed=42,
    )
    return {
        "Cohort": "All included studies: reviewer median",
        **inference,
        "aggregation": AGGREGATION,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--canonical-data", type=Path, default=DEFAULT_CANONICAL_DATA)
    args = parser.parse_args()

    # All workbook/title/completeness/range checks happen before output setup.
    lmic, tr = _read_matrix(
        args.input_xlsx.resolve(), args.canonical_data.resolve()
    )
    summary = _consensus_summary(lmic, tr)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / SUMMARY_NAME
    pd.DataFrame([summary]).to_csv(output_path, index=False, encoding="utf-8")
    print(
        json.dumps(
            {
                "items": EXPECTED_ITEMS,
                "raters": EXPECTED_RATERS,
                "summary": SUMMARY_NAME,
                "individual_ratings_written": False,
                "per_paper_medians_written": False,
                "result": summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
