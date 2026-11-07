import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


REPO = Path(__file__).resolve().parents[2]
STATISTICAL_SCRIPTS = REPO / "scripts" / "analysis" / "statistical"
sys.path.insert(0, str(STATISTICAL_SCRIPTS))

from run_weighted_kappa_from_private_xlsx import _weighted_summary  # noqa: E402


def test_identical_ordinal_ratings_have_perfect_weighted_agreement():
    ratings = np.tile(np.array([1, 2, 3, 4, 5])[:, None], (1, 3))

    for weighting in ("linear", "quadratic"):
        summary, item_rows = _weighted_summary(
            ratings, categories=list(range(1, 6)), analysis="LMIC_Relevance_Score", weighting=weighting
        )

        assert summary["Weighted_Fleiss_kappa"] == 1.0
        assert summary["Pairwise_Cohen_kappa_mean"] == 1.0
        assert len(item_rows) == 5


def test_public_weighted_outputs_are_aggregate_only():
    summary = pd.read_csv(REPO / "tables" / "analysis_weighted_kappa_summary.csv")
    item_agreement = pd.read_csv(REPO / "tables" / "analysis_weighted_kappa_item_agreement.csv")

    assert set(summary["Analysis"]) == {"LMIC_Relevance_Score", "TR_Score"}
    assert set(summary["Weighting"]) == {"linear", "quadratic"}
    assert (summary["Items"] == 48).all()
    assert (summary["Raters"] == 11).all()
    assert summary["Weighted_Fleiss_kappa"].between(-1, 1).all()
    assert summary["Pairwise_Cohen_kappa_mean"].between(-1, 1).all()
    expected = [0.5277717161902787, 0.5443474538700254, 0.39267010269126407, 0.5592799831081077]
    assert summary["Weighted_Fleiss_kappa"].tolist() == pytest.approx(expected)
    assert len(item_agreement) == 192
    assert set(item_agreement["Analysis"]) == {"LMIC_Relevance_Score", "TR_Score"}
    assert set(item_agreement["Weighting"]) == {"linear", "quadratic"}
    assert item_agreement["Scoring_Form_ID"].between(1, 48).all()
    assert "Paper_ID" not in item_agreement.columns
    assert "Title" in item_agreement.columns
    assert not any("Reviewer" in column or "Rating" in column for column in summary.columns)
    assert not any("Reviewer" in column or "Rating" in column for column in item_agreement.columns)
