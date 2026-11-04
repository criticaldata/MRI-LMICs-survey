"""Evidence rules that prevent baseline selection and unsupported score claims."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'analysis'))
sys.path.insert(0, str(ROOT / 'scripts' / 'tables'))


@pytest.mark.parametrize('status', ['Unclear', 'Not available', 'Not applicable'])
def test_unresolved_pathway_is_preserved_but_cannot_be_eligible(status):
    from review_metrics import _metric_suitability_table
    frame = pd.DataFrame([{'Paper_ID': 1, 'DOI': '10.1/example', 'Title': 'Example',
                           'PSNR_Numeric': 30., 'SSIM_Numeric': .9,
                           'Field_Pair_Category': status, 'Paired_Unpaired': 'Paired',
                           'Ground_Truth_Type': 'Measured same-subject reference'}])
    row = _metric_suitability_table(frame).iloc[0]
    assert row.Field_Pathway == status
    assert row.PSNR_SSIM_Comparison_Eligibility == 'Not eligible'


def test_unresolved_ground_truth_is_not_a_reference_even_with_known_pathway():
    from review_metrics import _metric_suitability_table
    frame = pd.DataFrame([{'Paper_ID': 1, 'Title': 'Example',
                           'PSNR_Numeric': 30., 'SSIM_Numeric': .9,
                           'Field_Pair_Category': 'standard/high-field only',
                           'Paired_Unpaired': 'Paired', 'Ground_Truth_Type': 'Unclear'}])
    assert _metric_suitability_table(frame).iloc[0].PSNR_SSIM_Comparison_Eligibility == 'Not eligible'


def test_reporting_profile_uses_numeric_metric_and_partitions_the_actual_corpus():
    from table3_performance_metrics import reporting_profile
    frame = pd.DataFrame({'PSNR_Numeric': [30., np.nan, 32., np.nan],
                          'SSIM_Numeric': [.9, .8, np.nan, np.nan],
                          'Year': [2020, 2021, 2022, 2023],
                          'Architecture_Norm': ['CNN'] * 4,
                          'Field_Strength_Norm': ['Standard-field'] * 4,
                          'LMIC_Score': [2, 3, 4, 5],
                          'Clinical_Validation_Norm': ['None'] * 4,
                          'Low_Field_Norm': ['No'] * 4})
    profile = reporting_profile(frame, 'PSNR')
    assert profile['n'].tolist() == [2, 2]
    assert profile.n.sum() == len(frame)
    assert profile.Median_LMIC_Score.tolist() == [3., 4.]


def _source_and_evidence():
    source = pd.DataFrame([{'Paper_ID': 1, 'DOI': '10.1/example', 'Title': 'Example',
                            'LMIC_Relevance_Score': '3', 'LMIC_Relevance_Justification': 'Original'}])
    evidence = pd.DataFrame([{'Paper_ID': 1, 'DOI': '10.1/example', 'Title': 'Example',
                              'Original_LMIC_Score': 3, 'Highest_Other_Level': 3,
                              'LMIC_Coauthorship_Status': 'Yes', 'LMIC_Data_Setting': 'No',
                              'Portable_Clinical_Validation': 'No',
                              'Evidence_Page': '1', 'Evidence_Section': 'Author affiliations',
                              'Evidence_Quote': 'National Institute of Technology Calicut, India',
                              'Decision_Reason': 'Published affiliation in an LMC economy'}])
    return source, evidence


def test_publication_lmic_coauthorship_promotes_level_five_without_erasing_original():
    from apply_lmic_relevance_evidence import apply_verified_scores
    source, evidence = _source_and_evidence()
    result = apply_verified_scores(source, evidence)
    assert result.iloc[0].LMIC_Relevance_Score == 5
    assert result.iloc[0].LMIC_Relevance_Score_Original == 3
    again = apply_verified_scores(result, evidence)
    assert again.iloc[0].LMIC_Relevance_Score_Original == 3


def test_geography_candidate_alone_does_not_promote_level_five():
    from apply_lmic_relevance_evidence import apply_verified_scores
    source, evidence = _source_and_evidence()
    evidence['LMIC_Coauthorship_Status'] = 'Unclear'
    result = apply_verified_scores(source, evidence)
    assert result.iloc[0].LMIC_Relevance_Score == 3


def test_lmic_correction_rejects_wrong_doi_or_missing_evidence():
    from apply_lmic_relevance_evidence import apply_verified_scores
    source, evidence = _source_and_evidence()
    evidence['DOI'] = '10.1/wrong'
    with pytest.raises(ValueError, match='DOI'):
        apply_verified_scores(source, evidence)
    evidence['DOI'] = '10.1/example'
    evidence['Evidence_Quote'] = ''
    with pytest.raises(ValueError, match='evidence'):
        apply_verified_scores(source, evidence)
