import sys
import warnings
from pathlib import Path

from scipy.optimize import OptimizeWarning


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis" / "statistical"))

import run_random_forest_robustness_20260804 as robustness  # noqa: E402


def test_ordinal_fit_suppresses_only_known_mord_disp_optimizer_warning():
    """The supplementary ordinal benchmark should not emit its known dependency warning."""
    features, target, _ = robustness.make_input()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        robustness.fit_ordinal_model(features.iloc[:38], target[:38].astype(int))

    known_warning = [
        item
        for item in captured
        if issubclass(item.category, OptimizeWarning)
        and "Unknown solver options: disp" in str(item.message)
    ]
    assert known_warning == []
