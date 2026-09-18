"""The two field-strength taxonomies must stay identical.

scripts/figures/mapper.py drives the descriptive tables and figures, while
scripts/analysis/review_metrics.py drives the promoted reviewer analyses. When
they disagree, the same study is counted in two different field-strength
categories, which is how Figure 3D once contradicted Supplementary Table 10.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))


def test_curated_field_strength_maps_agree():
    from review_metrics import FIELD_STRENGTH_LABELS
    from mapper import FIELD_STRENGTH_MAP

    assert FIELD_STRENGTH_LABELS == FIELD_STRENGTH_MAP


def test_both_normalizers_agree_on_every_raw_value():
    import pandas as pd
    from review_metrics import normalize_field_category
    from mapper import normalize_field_strength

    raw = pd.read_csv(ROOT / "data" / "data-clean.csv")["Field_Strength_Type"]
    for value in raw.dropna().unique():
        assert normalize_field_category(value) == normalize_field_strength(value), value
