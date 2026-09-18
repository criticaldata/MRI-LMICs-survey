# Reproducible review analysis

## Scope

The local pipeline now separates source freezing, derived review analyses,
scientometric metadata, and reviewer agreement. The historical provisional
Fleiss κ output is not overwritten or reused in the corrected analyses.

## Public data boundary

The tracked `data/data-clean.csv` is the 48-study anonymized public corpus.
It excludes reviewer names, reviewer assignments, and individual ratings.
The reviewer-containing internal source is retained only in the ignored local
path `data/private/`; it is not required to reproduce the public tables and
figures. Final Fleiss kappa is published only as an aggregate summary; the
private workbook and individual ratings are never tracked.

The included-study identity contract is `data/included_study_order.csv`. It
contains exactly the 48 canonical `Paper_ID` values, titles, and DOIs from
`origin/main`. All active item-level outputs are checked against this contract
by title/DOI; IDs are never repaired by numeric shifting. The agreement runners
also validate every private workbook row against the same title order before
writing any output.

## Corrected operational definitions

The translational-readiness score is the sum of five equally weighted binary
criteria defined in the revised manuscript:

1. **Low-Field Domain** — explicit training or fine-tuning on data at or below
   64 mT.
2. **Open Science** — a persistent public URL to source code or model weights;
   `Upon_request` is reported separately and is not public Open Science.
3. **Clinical Evaluation** — radiologist/clinical-reader assessment or a
   downstream clinical task beyond PSNR/SSIM.
4. **Hardware Awareness** — explicit minimum hardware requirements for
   inference. Training hardware, a workstation used for experiments, runtime,
   model size, or memory consumption alone do not satisfy this criterion.
5. **Data Diversity** — real-world scanner, motion, portability,
   heterogeneity, or generalization evidence.

The final TR evidence layer is `data/tr_criteria_evidence.csv`. It contains one
row per included study, final `Yes`/`No` decisions for all five criteria, the
supporting page/section, and a rubric-based reason. The canonical Master Data
Sheet remains unchanged and is joined to this evidence layer by `Paper_ID`.

Target-field characterization uses the separate public evidence layer
`data/field_characterization_evidence.csv`. It is matched one-to-one to the
canonical corpus by title and DOI and records the exact target-field statement,
field pathway, page/section, and supporting text. It does not overwrite the
Master Data Sheet and contains no reviewer identities or process labels.

## Current rerun outputs

The promoted 2026-09-15 rerun is in `analysis/review_20260803/` and includes:

- corrected per-paper TR criteria and score;
- sensitivity restricted to SR-primary cohorts, with strict and
  pure/denoising definitions shown separately;
- Spearman LMIC–TR correlations with deterministic permutation p-values and
  bootstrap percentile confidence intervals;
- dataset characterization: size, sequence, contrast, real/synthetic status,
  paired/unpaired status, input/target field categories, field-pair direction,
  and ground-truth type;
- quality-score rerun and a raw-value unknown audit;
- an analysis manifest that keeps private-input agreement calculation separate
  from the public core run;
- aggregate final Fleiss κ outputs for the 48-study, 11-reviewer matrix.

The TR outputs also include the flat evidence file
`analysis_tr_hardware_verification.csv`. It records the final decision,
article page/section, evidence reason, source document, and rubric version.
None of the 48 papers explicitly specified minimum hardware requirements for
inference, so Hardware Awareness is 0/48. Several papers report training GPUs,
runtime, memory use, or an experimental workstation; those near-matches are
documented but correctly score `No` under the official definition.

The final article-evidence counts are: Low-Field Domain 4/48, Open Science
4/48, Clinical Evaluation 21/48, Hardware Awareness 0/48, and Data Diversity
30/48. Mean TR is 1.2292/5 (median 1). These are reproducible article-level
decisions and remain separate from the independent 11-author scores used for
the final inter-rater agreement analysis.

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
with the primary score in every scheme (Spearman rho at least 0.951). In the
verified evidence rerun, the LMIC--TR rho ranges from 0.349 to 0.418 and all
10,000-permutation p-values are below 0.015; the corresponding bootstrap
intervals remain above zero. This association must still be described as
exploratory because the two constructs share deployment-related content; it is
separate from the final 11-author agreement analysis.

Weighting robustness is not scorer-dependence robustness. The four weighting
schemes reuse the canonical study-level inputs and test how the TR definition
changes under alternative criterion weights; they do not test whether the
LMIC--TR association depends on the people supplying ratings.

The random-forest robustness analysis is in
`analysis/review_20260803/random_forest_robustness_20260804/`. It uses a
constrained forest, 5-fold repeated cross-validation (10 repeats), a mean
baseline, a regularized ridge benchmark, a regularized ordinal benchmark,
held-out permutation importance, and bootstrap confidence intervals. It is a
supplementary exploratory analysis only; it does not support causal claims.

`ground_truth_metric_audit_20260804/` records the conservative PSNR/SSIM
ground-truth audit. It accepts only exact evidence from the frozen extraction
or cached Europe PMC full text, and retains `Not reported` when the source does
not establish pairedness or low-field direction. It is an auxiliary analysis
and never overwrites the canonical extraction source.

## Independent reviewer agreement

The final IRR uses the same 48 papers scored independently by all 11 reviewers.
The private workbook is validated and passed externally to
`run_fleiss_kappa_from_private_xlsx.py`. The runner writes only
`analysis_fleiss_kappa_summary.csv` and
`analysis_fleiss_kappa_item_agreement.csv`; it does not write reviewer names or
individual ratings. The resulting aggregate values are LMIC κ = 0.505 and TR
κ = 0.223.

The same private-input pipeline also writes supplementary ordinal-weighted
agreement (linear and quadratic generalized multi-rater weighted Fleiss
statistics plus pairwise weighted Cohen summaries) and ICC outputs. These
supplements do not replace the prespecified standard Fleiss κ.

The private-input pipeline also calculates a reviewer-consensus Spearman
sensitivity. Before any output is written, the shared workbook validator
requires exactly 48 papers in the canonical title order, 11 complete raters for
both LMIC and TR, integer LMIC values from 1 to 5, and integer TR values from 0
to 5. The runner aggregates each paper by the median of its 11 ratings and uses
the same average-rank Spearman method, deterministic two-sided 10,000-
permutation p-value, 10,000 paired bootstrap percentile interval, and seed 42
as the canonical analysis. It promotes only
`tables/analysis_lmic_tr_correlation_reviewer_consensus.csv`, with no reviewer
names, individual ratings, private paths, or paper-level medians.

The canonical study-level analysis remains primary. It reads LMIC from
`data/data-clean.csv` and TR from `data/tr_criteria_evidence.csv`; for all 48
studies it gives rho = 0.4059228847, permutation p = 0.0032996700, and 95%
bootstrap CI 0.1639207818 to 0.6065349303. The reviewer-median sensitivity gives
rho = -0.2576999801, permutation p = 0.0786921308, and 95% bootstrap CI
-0.5397196933 to 0.0397231367. This contrast is evidence of scorer-source
sensitivity that should be reported explicitly, not resolved by selecting the
more favorable estimate.

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
columns. Target field strength is explicitly reported for 22 studies, not
applicable for 15, not reported by 6, and not verifiable from the available
publisher text for 5. These states are kept separate; they are not collapsed
into a heuristic `Unknown` category.

`analysis_psnr_ssim_metric_suitability.csv` has one row per included study and
states whether a reported PSNR/SSIM value has explicit paired, ground-truth,
and field-pathway evidence. It is a descriptive evidence table, not a pooled
meta-analysis.

Temporal outputs are split deliberately. `analysis_temporal_trends.csv` is
the primary full-year 2020-2024 analysis. The two 2025 studies are retained in
`analysis_temporal_trends_2025_preliminary.csv` with the explicit status
`Preliminary and incomplete`.
