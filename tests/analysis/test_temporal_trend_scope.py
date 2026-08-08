"""Regression tests for reviewer-requested temporal trend scope."""

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "tables"))
sys.path.insert(0, str(REPO / "scripts" / "figures"))

from analysis_temporal_trends import build_temporal_trends  # noqa: E402
from mapper import load_data  # noqa: E402


def test_primary_temporal_results_exclude_2025_and_retain_it_separately():
    """The full-year primary trend cannot be influenced by incomplete 2025 data."""
    primary, preliminary = build_temporal_trends(load_data())

    assert primary["Year"].tolist() == [2020, 2021, 2022, 2023, 2024]
    assert preliminary["Year"].tolist() == [2025]
    assert preliminary["Status"].tolist() == ["Preliminary and incomplete"]
    assert primary["Status"].eq("Primary full-year analysis").all()
