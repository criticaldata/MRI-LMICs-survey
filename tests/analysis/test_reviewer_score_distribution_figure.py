"""Tests for the privacy-preserving full-corpus reviewer-score figure."""

import sys
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "figures"))
from figS3_reviewer_score_distributions import score_count_matrix  # noqa: E402


def test_score_distribution_aggregates_without_reviewer_columns():
    ratings = np.array([[1, 1, 3, 5], [2, 2, 2, 4], [5, 5, 5, 5]], dtype=int)
    counts = score_count_matrix(ratings, [1, 2, 3, 4, 5])
    assert counts.tolist() == [[2, 0, 1, 0, 1], [0, 3, 0, 1, 0], [0, 0, 0, 0, 4]]
    assert np.all(counts.sum(axis=1) == 4)
