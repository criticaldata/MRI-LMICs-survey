"""The reviewer comparison must use two disjoint exhaustive study groups."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/tables'))


def test_comparison_uses_complement_not_the_nested_pure_sr_cohort():
    from analysis_sr_vs_non_sr import compare_groups
    frame = pd.DataFrame({'SR_Primary_Strict': [True, True, True, False, False, False],
                          'LMIC_Score': [1, 2, 3, 4, 5, 5], 'TR_Score': [0, 1, 1, 2, 3, 3]})
    for name in ['LowFieldDomain', 'OpenScience', 'ClinicalEvaluation', 'HardwareAwareness', 'DataDiversity']:
        frame[f'TR_{name}'] = [0, 1, 0, 1, 1, 0]
    result = compare_groups(frame).set_index('Measure')
    assert result.loc['LMIC_Score', 'Strict_SR_N'] == 3
    assert result.loc['LMIC_Score', 'Other_N'] == 3
    assert result.loc['LMIC_Score', 'All_N'] == 6
    assert result.loc['LMIC_Score', 'Strict_SR_Value'] == 2
    assert result.loc['LMIC_Score', 'Other_Value'] == 14 / 3
    assert result.loc['TR_OpenScience', 'Strict_SR_Value'] == 1
    assert result.loc['TR_OpenScience', 'Other_Value'] == 2
