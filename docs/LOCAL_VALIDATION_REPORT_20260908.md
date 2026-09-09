# Local Validation Report - 2026-09-08

This report records the current offline validation of the reviewer-corrected
MRI-LMICs analysis package. No network calls or GitHub writes were made by the
pipeline.

## Validation results

- Core reproducibility verifier: PASS
- Public scientometric audit: PASS
- Test suite: 48 passed
- Screening source: 183 records, 48 included and 135 excluded
- Quality score: mean 4.1458/9; sample SD 1.1848
- Public code: 6; upon request: 2
- Resource constraints: 33 yes; 15 no; 0 unknown

## Reviewer agreement

The private workbook was validated as 48 papers scored by 11 reviewers. Only
aggregate results are tracked in the public package:

- LMIC Relevance Score: Fleiss' kappa = 0.5046
- TR Score: Fleiss' kappa = 0.2235

The individual ratings workbook is not included in the repository. The
aggregate outputs are `tables/analysis_fleiss_kappa_summary.csv` and
`tables/analysis_fleiss_kappa_item_agreement.csv`.

## Privacy and reproducibility boundary

Reviewer names, assignments, individual ratings, credentials, raw API caches,
and article PDFs are excluded from the public package. The optional private
input runner is `scripts/analysis/statistical/run_fleiss_kappa_from_private_xlsx.py`.
