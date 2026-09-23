# Reproducible Review Analysis

## Analysis population and source records

The all-author scoring workbook contains 48 candidate records. Three records were excluded from the final analytic corpus after DOI/title and eligibility adjudication; the final DOI-keyed corpus contains 45 studies. The 48-record form order remains in `data/reviewer_scoring_order.csv`; final Paper_IDs 1–45 are defined by `data/included_study_order.csv`. Mapping is by DOI/title, never by numeric shifting.

The available structured-extraction source has 56 records. Eight were excluded before the 48-record scoring form and three after scoring. The 11 reasons and available supporting evidence are recorded in `data/post_extraction_exclusions.csv`. Although 183 records were identified, the available screening export does not provide a reliable stage and reason for the 127 records not carried into structured extraction; the analysis therefore does not invent title/abstract or full-text exclusion categories for those records.

## Public/private boundary

The public corpus and derived tables contain no reviewer names, assignments, individual ratings, private workbook, API key, or credential. Agreement scripts accept the private workbook as an external input, validate all 48 records against the canonical form titles and score ranges, calculate reliability over all 48 scored candidates, and publish aggregate results only. Per-item agreement outputs use scoring-form IDs and titles with agreement summaries, not final-corpus Paper_IDs or individual reviewer scores. The reviewer-median Spearman sensitivity instead filters to the 45 eligible scientific studies.

## Dataset and field evidence

`data/field_characterization_evidence.csv` and `data/dataset_characterization_evidence.csv` preserve article-linked target field, field pathway, source/target resolution, dataset type and availability, pairing, ground truth, sequence/contrast, and evidence location. These join to the final corpus through canonical identity. A value remains `Not reported`, `Not available`, `Not applicable`, or `Unclear` according to its evidence state; it is not inferred from PSNR/SSIM, matrix size, author affiliation, or keywords.

Target-field status across the 45 eligible studies is: explicitly reported 20, not applicable 14, not reported 6, and not available from accessible source text 5. PSNR or SSIM is parseable for 19 studies (18 PSNR, 17 SSIM); eight meet the defined paired/reference evidence rule, 11 do not, and 26 have neither metric. These are descriptive counts, not a pooled meta-analysis.

The primary-SR sensitivity is generated from `data/primary_sr_scope_evidence.csv`: strict primary SR n=24; pure SR or SR plus denoising n=22. The broad eligible corpus remains n=45.

## Translational readiness

The TR score is the sum of five equally weighted binary criteria:

1. Training or fine-tuning on low-field data at or below 64 mT.
2. A persistent public source-code or model-weight URL.
3. Qualitative reader assessment or a clearly defined downstream clinical task.
4. Explicit inference/deployment hardware requirements. Training hardware or training time alone does not qualify.
5. Explicit analysis of real-world data diversity or generalization.

`data/tr_criteria_evidence.csv` contains one evidence-backed decision per eligible paper and criterion, with article page/section and rationale. Criterion counts are 3/45, 4/45, 19/45, 0/45, and 28/45, respectively; mean TR is 1.20/5 (median 1). These values describe evidence reported against the rubric, not model quality or clinical effectiveness.

## Agreement and LMIC–TR association

Fleiss' κ is the prespecified primary multi-rater statistic, calculated separately for LMIC and TR across all 48 scored candidates rated by all 11 authors: LMIC κ=0.505 and TR κ=0.223. Three candidates were later excluded from the scientific synthesis but remain in the reliability analysis because they were part of the all-author scoring exercise. Linear/quadratic weighted multi-rater κ and ICC are supplementary and do not replace Fleiss' κ. Weighted estimates and ICC values are in `tables/analysis_weighted_kappa_summary.csv` and `tables/analysis_icc_summary.csv`.

The canonical LMIC–TR analysis is Spearman ρ=0.374 (n=45, two-sided 10,000-permutation p=0.0114, bootstrap 95% CI [0.096, 0.586], seed 42). The separate sensitivity using the per-paper median of 11 authors is ρ=−0.328 (p=0.0297, 95% CI [−0.601, −0.024]). The change of direction indicates sensitivity to score source; both results are retained.

## Other current analyses

- Quality: mean 4.111/9, sample SD 1.210, median 4.
- Performance: median PSNR 34.195 dB (n=18); median SSIM 0.896 (n=17).
- Random-forest robustness: 45 studies; 50 repeated held-out splits; constrained forest MAE 0.679 and R² 0.031 (SD 0.283), versus mean-baseline MAE 0.782. The forest had lower MAE in 44/50 paired splits. Its low-field feature now requires an explicitly reported numeric 0.05-0.5 T strength; generic “low-field” labels do not qualify. This is supplementary and exploratory only. Aggregate model summaries are in `tables/analysis_random_forest_robustness_summary.csv`.
- Temporal analysis: 2020–2024 is the primary full-year period (n=43); two 2025 records are separated and marked preliminary/incomplete.
- The scientometric flat export contains 45 final-corpus rows aligned to the DOI/title contract. Its source-coverage table describes the earlier API acquisition over the original 48-record form, not a new 45-study query.

## Reproduction

Run the local pipeline from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/analysis/run_full_reproducibility_pipeline.ps1 -RunDate 20260922 -PrivateRatingsXlsx C:\private\RECEIVED_SCORES.xlsx
```

Omit `-PrivateRatingsXlsx` to regenerate public analyses and figures without recalculating reviewer agreement. The pipeline uses local/cached evidence, makes no API calls, and does not publish to GitHub. It rebuilds analysis tables, figures, public-release hashes, aggregate reviewer outputs when a private workbook is supplied, and then runs the reproducibility checks and test suite.
