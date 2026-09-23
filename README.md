# MRI-LMICs Survey: Reproducible Review Analyses

Code and public, aggregate data for *Deep Learning Super-Resolution for MRI: Technical Advances and Translational Potential for Low-Resource Settings*.

The final analytic corpus contains **45 eligible studies**. All 11 authors independently scored the same 48 candidate records; three records were subsequently excluded from the scientific synthesis after title/DOI and eligibility adjudication. Reliability estimates use the full 48-record scoring exercise; substantive analyses use the final 45 eligible studies.

## Reproduce the analysis

Use Python 3.11 or later. The local pipeline finalizes the DOI-keyed corpus, rebuilds analysis tables and figures, validates public exports, and runs the test suite. A private ratings workbook is optional; when supplied, it is read in place and only aggregate agreement outputs are written.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/analysis/run_full_reproducibility_pipeline.ps1 -RunDate 20260922 -PrivateRatingsXlsx C:\private\RECEIVED_SCORES.xlsx
```

Without `-PrivateRatingsXlsx`, public analyses and figures are regenerated without recalculating reviewer-agreement outputs. The pipeline uses local inputs and cached evidence; it does not publish to GitHub or call external APIs.

With the private workbook, the runner validates all 48 records against canonical titles and score ranges. It calculates Fleiss' kappa, ordinal-weighted multi-rater agreement, ICC, and the aggregate-only reviewer-score figure on all 48 scored records; the reviewer-median Spearman sensitivity is restricted to the 45 studies retained in the scientific corpus. Individual ratings and reviewer identities are never copied into the repository.

## Corpus and scope

- The search identified 183 records; 56 have structured extraction records.
- Eight records were excluded before the all-author scoring form and three were excluded during final eligibility reconciliation, leaving 45 included studies. The available source records do not support reconstructing stage-specific reasons for the other 127 identified records; these are not assigned invented title/abstract or full-text exclusion stages.
- `data/included_study_order.csv` defines the canonical contiguous Paper_IDs 1–45 by DOI and title.
- `data/reviewer_scoring_order.csv` preserves the separate 1–48 scoring-form order and maps each form record to its final eligibility and, when included, canonical Paper_ID.
- `data/post_extraction_exclusions.csv` records all 11 documented exclusions and the available reason/evidence.
- `data/field_characterization_evidence.csv` and `data/dataset_characterization_evidence.csv` preserve article-linked field, dataset, resolution, pairing, and ground-truth evidence.
- `data/primary_sr_scope_evidence.csv` defines the reviewer-requested primary-SR sensitivities: strict primary SR, n=24; pure SR or SR plus denoising, n=22.

The exclusion record identifies four exclusions as not MRI modality, three as review/survey, three as duplicate records/reports, and one as lacking an AI/deep-learning method. The three post-scoring cases are documented individually, including the retained peer-reviewed LowGAN article, the generic natural-image enhancement study without an MRI experiment, and the FouSR study whose Methods state that it does not use deep learning.

## Agreement and association

Standard nominal multi-rater Fleiss' kappa is the primary agreement statistic. All 11 authors scored both scales on the 48-record form; agreement calculations use all 48 scored records, including the three later excluded from the scientific synthesis. This preserves the inter-rater estimand for the task the authors completed. Study-level scientific analyses use the separate 45-study eligible corpus.

| Scale | Scored form records | Fleiss' kappa |
|---|---:|---:|
| LMIC Relevance Score | 48 | 0.505 |
| Translational Readiness Score | 48 | 0.223 |

Ordinal-weighted generalized multi-rater kappa and ICC are supplementary; neither replaces the prespecified Fleiss statistic. For the 48 scored records, linear/quadratic weighted multi-rater kappa estimates are 0.528/0.544 for LMIC relevance and 0.393/0.559 for TR. Two-way random-effects absolute-agreement ICC(2,1) is 0.553 for LMIC and 0.570 for TR; ICC(2,k), for the mean of 11 raters, is 0.932 and 0.936, respectively. ICC treats these ordinal categories as equally spaced and should be interpreted alongside kappa.

The canonical study-level LMIC–TR Spearman analysis uses the structured extraction and evidence-coded TR: n=45, ρ=0.374, two-sided 10,000-permutation p=0.0114, bootstrap 95% CI [0.096, 0.586]. A separate sensitivity using the per-study median of the 11 authors' scores is n=45, ρ=−0.328, p=0.0297, 95% CI [−0.601, −0.024]. The direction changes by score source; both results are retained and the association is not described as robust across scoring sources.

The five evidence-coded TR criterion counts are: low-field domain 3/45, open science 4/45, clinical evaluation 19/45, explicit inference-hardware requirements 0/45, and data diversity 28/45. Mean TR is 1.20/5 (median 1). This is a measure of reported evidence against the specified rubric, not clinical effectiveness.

The three alternative TR weighting schemes produced mean scores of 1.35, 1.18, and 1.33 versus 1.20 under equal weights. Study-score rank correlations ranged from 0.942 to 1.000; the 2:2:2:1:2 scheme was numerically identical to equal weights because Hardware Awareness was 0/45. LMIC–TR correlations remained positive but varied from 0.312 to 0.386, so weighting sensitivity does not establish robustness of that association.

Field-strength categories use reported numeric strengths: ultra-low `<0.05 T`, low-field `0.05-0.5 T`, intermediate `>0.5-<1.5 T`, standard `1.5-3 T`, and high-field `>3 T`. A generic “low-field” label without a numeric tesla value is kept separate as threshold-unspecified; multi-bin studies are labeled mixed. This general descriptive taxonomy is distinct from the TR criterion (`<=64 mT`); input and target field strengths are characterized separately.

## Selected descriptive results

| Measure | Current result |
|---|---:|
| Included studies | 45 |
| Brain MRI application | 22/45 |
| CNN architecture | 22/45 |
| Studies reporting parseable PSNR | 18/45 |
| Studies reporting parseable SSIM | 17/45 |
| Median PSNR | 34.195 dB |
| Median SSIM | 0.896 |
| Mean quality score | 4.111/9 (sample SD 1.210) |
| Metric-reporting studies meeting the paired/reference evidence rule | 8/19 |
| Public source code | 4/45 |
| Code available upon request | 2/45 |

The supplementary constrained Random Forest has mean held-out MAE 0.679 and mean held-out R² 0.031 (SD 0.283) across 50 repeated 5-fold splits. The mean-baseline MAE is 0.782; the forest has lower MAE in 44/50 paired splits. Numeric low-field input is coded only when a 0.05-0.5 T value is explicitly reported; a generic “low-field” label is not treated as a measured value. This small-sample analysis is exploratory, not causal or a claim of deployable prediction. A public aggregate summary is in `tables/analysis_random_forest_robustness_summary.csv`; detailed reproducibility outputs are generated locally under `analysis/review_20260803/random_forest_robustness_20260804/`.

The primary temporal analysis covers full years 2020–2024 (n=43); the two 2025 records are shown separately as preliminary and incomplete.

## Scientometric export

`tables/mri_scientometric_results.csv` is aligned to the final 45-study DOI/title contract. Its source-coverage companion refers to the earlier API acquisition over the 48-record scoring form, not a newly queried 45-study run; this distinction is recorded in `tables/mri_scientometric_export_manifest.json`. The flat export can be re-aligned without network access:

```powershell
py -3.12 scripts/analysis/align_mri_scientometric_export.py
```

## Privacy and outputs

Reviewer names, assignments, individual ratings, private workbooks, and API credentials are excluded. Agreement runners read the private workbook externally, validate its complete form order, and write aggregate outputs only. Public-release hashes are recorded in `data/public_release_manifest.json`. The full pipeline runs the reproducibility verifier and privacy tests.

Figures are generated under `figures/main/` and `figures/supplementary/`. Supplementary Figure 3 displays only aggregate score counts by paper and score category; it contains no individual ratings or reviewer identities.

For definitions and interpretation see `docs/STATISTICAL_METHODS.md`; implementation and source details are in `docs/REPRODUCIBLE_REVIEW_ANALYSIS.md`.
