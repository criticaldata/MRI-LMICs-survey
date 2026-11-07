"""Country combinations must retain known income information."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/analysis'))


def test_same_tier_multi_country_affiliation_is_not_missing():
    from affiliation_income import classify_countries
    assert classify_countries('DE|US') == ('DE|US', 'HIC')
    assert classify_countries('Switzerland; Germany') == ('CH|DE', 'HIC')


def test_distinct_tiers_and_unknown_country_are_not_silently_hic():
    from affiliation_income import classify_countries
    assert classify_countries('India; United States') == ('IN|US', 'Mixed income groups')
    assert classify_countries('Unknown') == ('Not available', 'Not available')
