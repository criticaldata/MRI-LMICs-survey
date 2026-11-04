"""Compare the strict primary-SR cohort with its complement in the final corpus."""

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/analysis'))
from review_metrics import TR_CRITERIA, _metric_suitability_table, add_derived_fields, load_data, spearman_inference


def compare_groups(derived):
    flag = derived.SR_Primary_Strict
    if flag.isna().any() or not set(flag.unique()) <= {True, False}:
        raise ValueError('Primary-SR membership must be complete and binary')
    groups = [derived.loc[flag], derived.loc[~flag], derived]
    if not len(groups[0]) or not len(groups[1]):
        raise ValueError('Both comparison groups require studies')
    rows = []
    for measure in ['LMIC_Score', 'TR_Score', 'LMIC_Level_4_or_5', *[f'TR_{c}' for c in TR_CRITERIA]]:
        is_score = measure in {'LMIC_Score', 'TR_Score'}
        values = [g[measure] if measure != 'LMIC_Level_4_or_5' else g.LMIC_Score.ge(4).astype(int) for g in groups]
        if is_score:
            p = mannwhitneyu(values[0], values[1], alternative='two-sided', method='asymptotic').pvalue
        else:
            yes = [int(v.sum()) for v in values]
            p = fisher_exact([[yes[0], len(values[0])-yes[0]], [yes[1], len(values[1])-yes[1]]]).pvalue
        row = {'Measure': measure, 'Test': 'Mann-Whitney U (two-sided, tie-corrected asymptotic)' if is_score else 'Fisher exact (two-sided)', 'p_value': float(p)}
        for label, g, v in zip(['Strict_SR', 'Other', 'All'], groups, values):
            row[f'{label}_N'] = len(g)
            row[f'{label}_Value'] = float(v.mean()) if is_score else int(v.sum())
            row[f'{label}_Median'] = float(v.median())
            row[f'{label}_Percent'] = None if is_score else float(v.mean()*100)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    data = add_derived_fields(load_data())
    compare_groups(data).to_csv(ROOT / 'tables/analysis_sr_vs_other_enhancement.csv', index=False)
    correlations = []
    for label, subset in [('Strict SR-primary', data.loc[data.SR_Primary_Strict]),
                          ('Other enhancement', data.loc[~data.SR_Primary_Strict]),
                          ('All included studies', data)]:
        correlations.append({'Cohort': label, **spearman_inference(subset.LMIC_Score, subset.TR_Score)})
    pd.DataFrame(correlations).to_csv(ROOT / 'tables/analysis_lmic_tr_correlation_by_scope.csv', index=False)
    paired = data.dropna(subset=['PSNR_Numeric', 'SSIM_Numeric'])
    suitability = _metric_suitability_table(data)
    eligible_ids = suitability.loc[suitability.PSNR_SSIM_Comparison_Eligibility.eq('Eligible'), 'Paper_ID']
    eligible = paired.loc[paired.Paper_ID.isin(eligible_ids)]
    pd.DataFrame([{'Analysis': label, **spearman_inference(frame.PSNR_Numeric, frame.SSIM_Numeric),
                   'Study_Level_Reference_Eligible': int(frame.Paper_ID.isin(eligible_ids).sum()),
                   'Interpretation': 'Association of extracted scalars; same model and condition across metrics not verified.'}
                  for label, frame in [('Exploratory PSNR-SSIM association', paired),
                                       ('Restricted to study-level reference eligibility', eligible)]]).to_csv(
        ROOT / 'tables/analysis_psnr_ssim_correlation.csv', index=False)
    # This paper uses radial undersampling and its source does not clearly
    # distinguish spatial-resolution improvement from reconstruction alone.
    # Keep the published scope contract; assess its influence separately.
    smir = '10.1109/icmipe53131.2021.9698880'
    reassigned = data.copy()
    reassigned.loc[reassigned.DOI.str.casefold().eq(smir), 'SR_Primary_Strict'] = False
    compare_groups(reassigned).to_csv(ROOT / 'tables/analysis_sr_scope_smir_sensitivity.csv', index=False)
    print(f'Compared {int(data.SR_Primary_Strict.sum())} primary-SR and {int((~data.SR_Primary_Strict).sum())} other studies; no multiplicity adjustment.')


if __name__ == '__main__':
    main()
