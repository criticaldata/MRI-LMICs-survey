"""Regression tests for reviewer-requested dataset and metric outputs."""

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
sys.path.insert(0, str(REPO / "scripts" / "figures"))

from mapper import load_data  # noqa: E402
from review_metrics import build_analysis  # noqa: E402


def test_dataset_characterization_has_reviewer_required_columns():
    """The derived table must expose reviewer-requested fields without editing source data."""
    table = build_analysis(load_data())['dataset_characterization']

    assert len(table) == 48
    assert {
        "Input_Resolution",
        "Target_Resolution",
        "Dataset_Public_Availability",
        "Resolution_Evidence",
        "Dataset_Availability_Evidence",
    }.issubset(table.columns)
    assert not table["Input_Resolution"].isna().any()
    assert not table["Target_Resolution"].isna().any()
    assert not table["Dataset_Public_Availability"].isna().any()


def test_metric_suitability_has_one_conservative_row_per_included_study():
    """Metric eligibility must never infer paired ground truth from PSNR/SSIM alone."""
    table = build_analysis(load_data())['metric_suitability']

    assert len(table) == 48
    assert table["Paper_ID"].nunique() == 48
    assert set(table["PSNR_SSIM_Comparison_Eligibility"]).issubset(
        {"Eligible", "Not eligible", "Not reported"}
    )
    metric_rows = table[table["PSNR_or_SSIM_Reported"] == "Yes"]
    assert (metric_rows["PSNR_SSIM_Comparison_Eligibility"] != "Eligible").any()
