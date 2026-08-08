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
It is not the final IRR result and is not used by the corrected pipeline.

- **Planned statistic**: Fleiss' Kappa ($\kappa$) per scored criterion after all
  11 reviewers independently score the same 48 `Paper_ID` records. The files
  are validated for matching IDs before they are combined.
- **Interpretation**: Landis & Koch (1977) scale:
    - 0.41 - 0.60: **Moderate Agreement**.
    - 0.61 - 0.80: **Substantial Agreement**.

## 4. Geographic & Socioeconomic Mapping

- **Country Identification**: Pulled from OpenAlex affiliation metadata.
- **Economic Classification**: Mapped via ISO-2 country codes to **World Bank Income Groups** (HIC, UMIC, LMIC, LIC).
- **Equity Analysis**: Binary classification into "HIC (High-Income / Parachute Risk)" vs "Global South (Local Research)" based on the primary/corresponding author's institution.

---

*The corrected analysis uses deterministic seeds where applicable and records
the seed, inputs, outputs, and hashes in each analysis manifest.*
