# Statistical Methodology - MRI Super-Resolution Narrative Review

This document details the statistical and ML framework used to analyze factors influencing LMIC relevance and the reporting quality of MRI super-resolution (SR) studies.

## 1. Random Forest Robustness Supplement

The current exploratory analysis uses all 48 included studies and a
**constrained Random Forest Regressor** to predict the ordinal
`LMIC_Relevance_Score` (1-5). Nominal ordinal values are explicitly coerced
to numeric via predefined dictionaries. It is supplementary, not a deployable
prediction model or causal analysis.

- **Hyperparameters**: 400 trees, `max_depth=3`, `min_samples_split=6`,
  `min_samples_leaf=4`, `max_features=0.7`.
- **Validation**: repeated 5-fold held-out validation (10 repeats; 50 test
  splits), with a mean baseline, regularized ridge benchmark, and regularized
  ordinal-logistic benchmark.
- **Features**: Binary encodings of AI architecture (CNN, GAN, U-Net, Transformer), dataset source (Clinical vs Synthetic), code availability, low-field mentioning, and metrics reported (PSNR/SSIM).
- **Metrics**: held-out MAE and R2. Feature stability is assessed with held-out
  permutation importance and 200 bootstrap resamples (seed 42).
- **Interpretation**: held-out performance is limited (mean MAE 0.622; mean
  R2 0.167). Feature measures reflect association in this sample only and
  **must not** be read as causal evidence of clinical or deployment impact.

## 2. Mann-Whitney U & Reporting Bias

We performed pairwise comparisons to test for "Reporting Bias." Studies that report traditional metrics (PSNR/SSIM) were compared against those that do not.

- **Continuous/Ordinal Variables**: Mann-Whitney U test (e.g., comparing `LMIC_Relevance_Score` medians).
- **Categorical Variables**: Pearson's Chi-Square test or Fisher's Exact Test (where N < 5 per cell).
- **Hypothesis**: $H_0$: There is no statistical difference in the characteristics (e.g., low-field focus, code availability) of papers based on their metric reporting status.
- **Multiple Comparisons**: All tests are subjected to Benjamini-Hochberg False Discovery Rate (FDR) correction ($\alpha = 0.05$). Exported tables explicitly report `q_value_fdr` to control the expected proportion of false discoveries among the rejected hypotheses.

## 3. Fleiss' Kappa (Inter-Rater Reliability)

The historical 2-rater, 10-paper calculation is a calibration artifact only.
It is not used as the final IRR result. The final analysis uses the same 48
papers scored independently by all 11 reviewers and reports separate kappa
values for the two ordinal score scales:

- **LMIC Relevance Score (1-5):** Fleiss' $\kappa$ = **0.505**.
- **TR Score (0-5):** Fleiss' $\kappa$ = **0.223**.

The calculation is the standard nominal-category Fleiss statistic, as requested
for the inter-rater analysis. The aggregate outputs are
`tables/analysis_fleiss_kappa_summary.csv` and
`tables/analysis_fleiss_kappa_item_agreement.csv`. The workbook containing
individual ratings is private and is supplied to the runner externally through
`scripts/analysis/statistical/run_fleiss_kappa_from_private_xlsx.py`.

For context, the average observed agreement was 0.648 for LMIC and 0.451 for
TR. The values should not be combined into one kappa or interpreted as clinical
validity of either score.

- **Interpretation**: Landis & Koch (1977) scale:
    - 0.21 - 0.40: **Fair Agreement**.
    - 0.41 - 0.60: **Moderate Agreement**.
    - 0.61 - 0.80: **Substantial Agreement**.

## 4. Ordinal Weighted Agreement (Supplementary)

Because both reviewer scores are ordinal, a supplementary distance-weighted
analysis was calculated after the standard Fleiss analysis. The primary
multi-rater implementation is a generalized weighted Fleiss statistic: for
each paper, agreement is averaged across all ordered reviewer pairs using
pre-specified category-distance weights, and expected agreement is computed
from the pooled category proportions. All 55 reviewer pairs are also summarized
with pairwise weighted Cohen kappas; those pairwise summaries are descriptive
and are not mislabeled as a second Fleiss statistic.

Two sensitivity schemes were prespecified:

- **Linear weights**: adjacent scores receive partial credit proportional to
  their ordinal distance.
- **Quadratic weights**: larger disagreements are penalized more strongly.

Results for the 48 papers and 11 reviewers were:

| Analysis | Linear weighted Fleiss κ | Quadratic weighted Fleiss κ |
| :--- | ---: | ---: |
| LMIC Relevance Score (1–5) | 0.528 | 0.544 |
| TR Score (0–5) | 0.393 | 0.559 |

The corresponding mean pairwise weighted Cohen κ values were 0.547 and 0.569
for LMIC (linear and quadratic) and 0.408 and 0.577 for TR. The range across
the 55 pairs is retained in the CSV output. These values show how agreement
changes when adjacent ordinal disagreements are treated as less severe than
widely separated disagreements; they do not prove validity, clinical utility,
or agreement with an external ground truth.

The standard Fleiss κ remains the primary inter-rater result because it was the
prespecified statistic for the 11-reviewer analysis. The weighted analysis must
not be selected solely because it produces a larger coefficient. Aggregate
outputs are stored in `tables/analysis_weighted_kappa_summary.csv` and
`tables/analysis_weighted_kappa_item_agreement.csv`; the private input is read
by `scripts/analysis/statistical/run_weighted_kappa_from_private_xlsx.py` and
is never written to the public repository.

## 5. Intraclass Correlation (Supplementary)

As an additional sensitivity analysis, intraclass correlation coefficients were
calculated on the numeric 1–5 LMIC and 0–5 TR scores. The prespecified ICC
model is ICC(2,1), a two-way random-effects model with absolute agreement for a
single reviewer measurement. ICC(2,k) reports the reliability of the mean score
across all 11 reviewers. Consistency ICCs are retained only as diagnostics.

| Analysis | ICC(2,1) absolute agreement | ICC(2,k) absolute agreement |
| :--- | ---: | ---: |
| LMIC Relevance Score (1–5) | 0.553 | 0.932 |
| TR Score (0–5) | 0.570 | 0.936 |

ICC treats the ordinal labels as equally spaced numeric values, so it is not a
replacement for the weighted ordinal analysis. The single-reviewer ICC is the
more conservative quantity for agreement of an individual rating; ICC(2,k) is
high because averaging 11 reviewers reduces measurement noise. Neither ICC nor
weighted κ establishes clinical validity or agreement with an external ground
truth. The aggregate output is stored in `tables/analysis_icc_summary.csv` and
is generated by `scripts/analysis/statistical/run_icc_from_private_xlsx.py`.

## 6. LMIC--TR Spearman Correlation

The primary analysis is study-level and uses the 48 canonical papers. LMIC
scores come from `data/data-clean.csv`; TR scores come from the final binary
criterion decisions in `data/tr_criteria_evidence.csv`. The all-study estimate
is primary, while the two existing SR-primary restrictions are reported as
cohort sensitivities in `tables/analysis_lmic_tr_correlation.csv`.

For every cohort, Spearman rho is Pearson correlation of average ranks, so ties
receive average ranks. Uncertainty is calculated deterministically with seed
42 using:

- a two-sided 10,000-permutation test that permutes the TR ranks and reports
  `(extreme + 1) / (10,000 + 1)`; and
- 10,000 paired paper-level bootstrap resamples with the percentile 2.5th and
  97.5th quantiles as the 95% confidence interval.

For all 48 studies, rho = 0.4059228847, permutation p = 0.0032996700, and the
bootstrap 95% CI is 0.1639207818 to 0.6065349303.

The private-workbook sensitivity first requires the exact canonical 48-title
order and complete LMIC and TR ratings from all 11 raters, with integer ranges
1--5 and 0--5 respectively. It takes the median of the 11 ratings for each
paper and applies the same rank, permutation, bootstrap, and seed rules. Only
the aggregate summary is promoted to
`tables/analysis_lmic_tr_correlation_reviewer_consensus.csv`; names, individual
ratings, private paths, and paper-level medians are not exported. The resulting
reviewer-median estimate is rho = -0.2576999801, permutation p = 0.0786921308,
with bootstrap 95% CI -0.5397196933 to 0.0397231367.

The reviewer-median result is a scorer-source sensitivity and does not replace
the canonical primary estimate. Weighting robustness is not scorer-dependence
robustness: changing weights among the five canonical TR criteria tests the
score definition, whereas replacing canonical scores with independent-rater
medians tests sensitivity to who supplied the scores. Neither analysis is
causal evidence or proof of score validity.

## 7. Geographic & Socioeconomic Mapping

- **Country Identification**: Pulled from OpenAlex affiliation metadata.
- **Economic Classification**: Mapped via ISO-2 country codes to **World Bank Income Groups** (HIC, UMIC, LMIC, LIC).
- **Equity Analysis**: Binary classification into "HIC (High-Income / Parachute Risk)" vs "Global South (Local Research)" based on the primary/corresponding author's institution.

---

*The corrected analysis uses deterministic seeds where applicable and records
the seed, inputs, outputs, and hashes in each analysis manifest.*
