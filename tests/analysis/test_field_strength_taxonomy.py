"""Every module must read field strength the same way.

scripts/figures/mapper.py drives the descriptive tables and figures,
scripts/analysis/review_metrics.py drives the promoted reviewer analyses, and
scripts/analysis/statistical/utils.py drives the bias figures. When they
disagree, one study lands in two categories, which is how Figure 3D once
contradicted Supplementary Table 10. The synthetic labels below are the point of
this test: checking only values already in the curated dict would pass even if
the fallback logic diverged again.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("scripts/analysis", "scripts/figures", "scripts/analysis/statistical"):
    sys.path.insert(0, str(ROOT / sub))

SYNTHETIC = [
    ("7T", "High-field"),
    ("9.4 T", "High-field"),
    ("1.5T", "Standard-field"),
    ("3 T", "Standard-field"),
    ("3T MRI", "Standard-field"),
    ("standard field", "Standard-field"),
    ("64 mT", "Low-field"),
    ("0.064 T", "Low-field"),
    ("ultra-low field", "Low-field"),
    ("Mixed", "Mixed"),
    ("Mixed (0.36 T and 1.5 T)", "Mixed"),
    ("Low field (64 mT) and Standard field (3 T)", "Low-field"),
    ("Not_specified", "Not specified"),
    ("", "Not specified"),
    (None, "Not specified"),
]


def _normalizers():
    from field_strength import normalize, normalize_legacy, LEGACY
    from mapper import normalize_field_strength
    from review_metrics import normalize_field_category
    from utils import normalize_field_strength as stats_normalize

    return normalize, normalize_field_strength, normalize_field_category, stats_normalize, normalize_legacy, LEGACY


def test_synthetic_labels_agree_everywhere():
    canonical, fig, analysis, stats, legacy, LEGACY = _normalizers()
    for raw, expected in SYNTHETIC:
        assert canonical(raw) == expected, raw
        assert fig(raw) == expected, raw
        assert analysis(raw) == expected, raw
        assert stats(raw) == LEGACY[expected], raw


def test_every_raw_value_in_the_data_agrees():
    import pandas as pd

    canonical, fig, analysis, stats, legacy, LEGACY = _normalizers()
    raw = pd.read_csv(ROOT / "data" / "data-clean.csv")["Field_Strength_Type"]
    for value in raw.dropna().unique():
        expected = canonical(value)
        assert fig(value) == expected, value
        assert analysis(value) == expected, value
        assert stats(value) == LEGACY[expected], value


def test_each_module_imports_the_shared_taxonomy():
    """The aggregate rules live in one file; the others delegate to it.

    This is the structural half of the guarantee: the behavioural tests above
    would still pass if someone re-implemented the same rules by hand today and
    let them drift tomorrow.
    """
    for rel in (
        "scripts/figures/mapper.py",
        "scripts/analysis/review_metrics.py",
        "scripts/analysis/statistical/utils.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "from field_strength import" in text, rel
