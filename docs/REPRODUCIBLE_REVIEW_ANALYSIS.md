# Reproducible review analysis

## Scope

The local pipeline now separates source freezing, derived review analyses,
scientometric metadata, and reviewer agreement. The existing provisional
Fleiss κ output is not overwritten or reused in the corrected analyses.

## Public data boundary

The tracked `data/data-clean.csv` is the 48-study anonymized public corpus.
It excludes reviewer names, reviewer assignments, and individual ratings.
The reviewer-containing internal source is retained only in the ignored local
path `data/private/`; it is not required to reproduce the public tables and
figures. Final Fleiss kappa remains pending until complete independent ratings
are received from all reviewers.

## Corrected operational definitions

The translational-readiness score is the sum of five equally weighted binary
criteria defined in the revised manuscript:

1. **Low-Field Domain** — explicit training or fine-tuning on data at or below
   64 mT.
2. **Open Science** — a persistent public URL to source code or model weights;
   `Upon_request` is reported separately and is not public Open Science.
3. **Clinical Evaluation** — radiologist/clinical-reader assessment or a
   downstream clinical task beyond PSNR/SSIM.
4. **Hardware Awareness** — a stated hardware or inference-resource
   specification.
5. **Data Diversity** — real-world scanner, motion, portability,
   heterogeneity, or generalization evidence.

The code keeps evidence snippets and manual-review flags. It does not convert
unrecognized resource, field, dataset, or reviewer values into affirmative
values.

## Current rerun outputs

The 2026-08-03 rerun is in `analysis/review_20260803/` and includes:

- corrected per-paper TR criteria and score;
- sensitivity restricted to SR-primary cohorts, with strict and
  pure/denoising definitions shown separately;
- Spearman LMIC–TR correlations with deterministic permutation p-values;
- dataset characterization: size, sequence, contrast, real/synthetic status,
  paired/unpaired status, input/target field categories, field-pair direction,
  and ground-truth type;
- quality-score rerun and a raw-value unknown audit;
- an analysis manifest declaring Fleiss κ pending.

The current frozen source produces a quality mean of 4.1458/9 (sample SD
1.1848), not the historical repository value 4.125/9 or the manuscript text
4.08/9. This discrepancy is now reproducibly visible and must be reconciled
in the manuscript before submission; no value was silently forced to match.

The current source has 6 public-code studies and 2 `Upon_request` studies. The
corrected code reports both counts. Resource-constraint evidence is 33/48 and
is obtained through explicit binary or concrete narrative evidence rather than
an automatic `fillna("Yes")` rule.

## Reviewer-requested robustness supplements

The TR weighting sensitivity is in
`analysis/review_20260803/tr_weighting_sensitivity_20260804/`. It evaluates
four prespecified weighting schemes rather than changing the manuscript's
primary equal-weight definition. The study ranking remains highly concordant
with the primary score in every scheme (Spearman rho at least 0.946), but the
LMIC--TR permutation p-value varies across schemes. Therefore the correlation
is exploratory and must not be described as a confirmed association.
The analysis now also records 10,000-replicate bootstrap confidence intervals
and leave-one-out rho values for the primary score. The primary rho remains
positive when any single study is omitted (0.194--0.298), but its bootstrap
95% interval crosses zero; this confirms that the association is not robust
enough for a confirmatory claim.

The random-forest robustness analysis is in
`analysis/review_20260803/random_forest_robustness_20260804/`. It uses a
constrained forest, 5-fold repeated cross-validation (10 repeats), a mean
baseline, a regularized ridge benchmark, a regularized ordinal benchmark,
held-out permutation importance, and bootstrap confidence intervals. It is a
supplementary exploratory analysis only; it does not support causal claims.

`ground_truth_auto_extraction_20260804/` records the automatic, conservative
PSNR/SSIM ground-truth audit. It accepts only exact evidence from the frozen
extraction or cached Europe PMC full text, and retains `Not reported` when the
source does not establish pairedness or low-field direction. It is an
auxiliary analysis and never overwrites the canonical extraction source.

## Independent reviewer agreement

The complete IRR requires the same 48 Paper_ID rows to be scored independently
by all 11 reviewers. The finished extraction workbook contains screening and
current assignment information, but not that complete independent rating
matrix. Use the local reviewer workbook template; send separate private copies,
then merge to a long table (`Paper_ID`, `Reviewer_ID`, score, notes) and derive
the wide matrix for Fleiss κ only after receipt of all files.

## Scientometric boundary

The local OpenAlex adapter uses the extracted 48-study DOI set and cached raw
responses for DOI resolution, authors, affiliations, countries, leadership,
collaboration, coverage, and open-access metadata. It does not replace the
clinical, TR, quality, LMIC, or dataset analyses and does not require Azure,
Genderize, Scopus, or Google Scholar credentials.

The adapter now derives work-level country and institution counts from the
authorship affiliation records when the work-level OpenAlex fields are empty.
The previous all-zero work-level country-count output was therefore stale and
has been regenerated. Remaining missing first/corresponding-author country
metadata is listed, with no imputation, in
`analysis/scientometrics/openalex_20260803/scientometric_unknown_audit.csv`.

## Dataset evidence and temporal scope

The dataset-characterization output includes `Input_Resolution`,
`Target_Resolution`, `Dataset_Public_Availability`, and source-evidence
columns. A value is populated only when frozen source text explicitly
supports it; otherwise the derived table states `Not reported`.

`analysis_psnr_ssim_metric_suitability.csv` has one row per included study and
states whether a reported PSNR/SSIM value has explicit paired, ground-truth,
and field-pathway evidence. It is a descriptive evidence table, not a pooled
meta-analysis.

Temporal outputs are split deliberately. `analysis_temporal_trends.csv` is
the primary full-year 2020-2024 analysis. The two 2025 studies are retained in
`analysis_temporal_trends_2025_preliminary.csv` with the explicit status
`Preliminary and incomplete`.
