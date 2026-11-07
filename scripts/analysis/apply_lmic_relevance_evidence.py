"""Apply DOI-verified Level 5 evidence while preserving original extraction values."""

from pathlib import Path
import argparse
import re

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
BRANCHES = ('LMIC_Coauthorship_Status', 'LMIC_Data_Setting', 'Portable_Clinical_Validation')


def _score(value):
    labels = {'low': 1, 'medium': 3, 'moderate': 3, 'high': 4}
    if str(value).strip().casefold() in labels:
        return labels[str(value).strip().casefold()]
    match = re.search(r'[1-5]', str(value))
    if not match:
        raise ValueError(f'Invalid LMIC score: {value!r}')
    return int(match.group())


def apply_verified_scores(source: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    """Apply the highest supported level; original reviewer ratings are never read."""
    required = {'Paper_ID', 'DOI', 'Title', 'Original_LMIC_Score', 'Highest_Other_Level',
                'Evidence_Page', 'Evidence_Section', 'Evidence_Quote', 'Decision_Reason', *BRANCHES}
    missing = required - set(evidence)
    if missing:
        raise ValueError(f'Missing LMIC evidence columns: {sorted(missing)}')
    if len(source) != len(evidence) or evidence.Paper_ID.duplicated().any():
        raise ValueError('LMIC evidence must cover the entire canonical DOI set once')
    result = source.copy()
    by_id = evidence.set_index('Paper_ID')
    if set(source.Paper_ID) != set(by_id.index):
        raise ValueError('LMIC evidence Paper_ID set differs from the source')
    aligned = by_id.loc[source.Paper_ID].reset_index()
    for column in ['DOI', 'Title']:
        left = source[column].astype(str).str.strip().str.casefold().tolist()
        right = aligned[column].astype(str).str.strip().str.casefold().tolist()
        if left != right:
            raise ValueError(f'LMIC evidence {column} does not match the canonical study')
    if aligned[list(BRANCHES)].isna().any().any() or not all(
        set(aligned[c]) <= {'Yes', 'No', 'Unclear', 'Not assessed (other branch sufficient)'} for c in BRANCHES
    ):
        raise ValueError('LMIC evidence requires explicit Yes, No or Unclear branch decisions')
    for column in ['Evidence_Page', 'Evidence_Section', 'Evidence_Quote', 'Decision_Reason']:
        if aligned[column].fillna('').astype(str).str.strip().eq('').any():
            raise ValueError(f'LMIC evidence is incomplete: {column}')
    original = aligned.Original_LMIC_Score.map(_score).to_numpy()
    source_original = result.get('LMIC_Relevance_Score_Original', result.LMIC_Relevance_Score).map(_score)
    if source_original.tolist() != original.tolist():
        raise ValueError('LMIC evidence original scores do not match preserved extraction scores')
    other = pd.to_numeric(aligned.Highest_Other_Level, errors='raise').astype(int)
    if not other.between(1, 4).all():
        raise ValueError('Highest_Other_Level must be in 1-4')
    qualifies = aligned[list(BRANCHES)].eq('Yes').any(axis=1)
    corrected = other.where(~qualifies, 5).astype(int)
    result['LMIC_Relevance_Score_Original'] = original
    if 'LMIC_Relevance_Justification_Original' not in result:
        result['LMIC_Relevance_Justification_Original'] = result.LMIC_Relevance_Justification
    result['LMIC_Relevance_Score'] = corrected.to_numpy()
    result['LMIC_Relevance_Justification'] = aligned.Decision_Reason.to_numpy()
    result['LMIC_Level5_Evidence_Source'] = 'data/lmic_relevance_evidence.csv'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=REPO / 'data/data-clean.csv')
    parser.add_argument('--evidence', type=Path, default=REPO / 'data/lmic_relevance_evidence.csv')
    args = parser.parse_args()
    result = apply_verified_scores(pd.read_csv(args.data), pd.read_csv(args.evidence))
    result.to_csv(args.data, index=False, encoding='utf-8', lineterminator='\n')
    changed = result.LMIC_Relevance_Score.ne(result.LMIC_Relevance_Score_Original).sum()
    print(f'Verified {len(result)} studies; {changed} extraction scores corrected; original scores preserved.')


if __name__ == '__main__':
    main()
