import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[2]
STATISTICAL_SCRIPTS = REPO / "scripts" / "analysis" / "statistical"
sys.path.insert(0, str(STATISTICAL_SCRIPTS))

from run_icc_from_private_xlsx import _icc_summary  # noqa: E402


def test_identical_ratings_have_perfect_absolute_agreement_icc():
    ratings = np.tile(np.array([1, 2, 3, 4, 5])[:, None], (1, 3))

    summary = _icc_summary(ratings, analysis="LMIC_Relevance_Score")

    assert summary["ICC_2_1_absolute_agreement"] == 1.0
    assert summary["ICC_2_k_absolute_agreement"] == 1.0


def test_public_icc_outputs_are_aggregate_only():
    summary = pd.read_csv(REPO / "tables" / "analysis_icc_summary.csv")

    assert summary["Analysis"].tolist() == ["LMIC_Relevance_Score", "TR_Score"]
    assert (summary["Items"] == 48).all()
    assert (summary["Raters"] == 11).all()
    assert summary["ICC_2_1_absolute_agreement"].between(-1, 1).all()
    assert summary["ICC_2_k_absolute_agreement"].between(-1, 1).all()
    assert not any("Reviewer" in column or "Rating" in column for column in summary.columns)
