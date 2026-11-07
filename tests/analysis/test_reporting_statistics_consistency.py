"""All reporting analyses use the same metric eligibility and effect direction."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/analysis/statistical'))


def test_ssim_reporting_ignores_sampling_percentage_labels():
    from utils import has_metric_reported
    assert has_metric_reported('At 20% sampling, SSIM was 0.86.', 'SSIM') == 1


def test_rank_biserial_positive_means_reporter_scores_are_higher():
    from mann_whitney_tests import rank_biserial
    assert rank_biserial(4, 2, 2) == 1
    assert rank_biserial(0, 2, 2) == -1
