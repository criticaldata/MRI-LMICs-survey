"""Normalize publication-affiliation countries using the frozen World Bank data."""

from pathlib import Path
import re
import unicodedata
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO / 'data/affiliation_country_income_groups.csv'
ALIASES = {'unitedstates': 'US', 'usa': 'US', 'unitedstatesofamerica': 'US',
           'uk': 'GB', 'unitedkingdom': 'GB', 'england': 'GB',
           'southkorea': 'KR', 'republicofkorea': 'KR', 'korea': 'KR',
           'iran': 'IR', 'hongkong': 'HK', 'hongkongsarchina': 'HK',
           'taiwan': 'TW', 'taiwanchina': 'TW', 'russia': 'RU',
           'egypt': 'EG', 'netherlands': 'NL', 'thenetherlands': 'NL',
           'vietnam': 'VN', 'turkey': 'TR', 'tuerkiye': 'TR'}


def _key(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(value)).casefold())


def classify_countries(value, snapshot=SNAPSHOT):
    """Return ISO2 set and an explicit common, mixed, or missing income group."""
    countries = pd.read_csv(snapshot, keep_default_na=False)
    lookup = {_key(r.Country): r.ISO2 for r in countries.itertuples()}
    lookup.update({_key(r.ISO2): r.ISO2 for r in countries.itertuples()})
    lookup.update(ALIASES)
    groups = countries.set_index('ISO2').WB_Income_Group.to_dict()
    tokens = [v.strip() for v in re.split(r'[;|]', str(value)) if v.strip()]
    codes = sorted(set(lookup.get(_key(v), '') for v in tokens))
    if not codes or '' in codes or any(c not in groups for c in codes):
        return 'Not available', 'Not available'
    tiers = {groups[c] for c in codes}
    return '|'.join(codes), next(iter(tiers)) if len(tiers)==1 else 'Mixed income groups'
