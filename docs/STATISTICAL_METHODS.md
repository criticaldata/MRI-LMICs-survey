# Statistical Methodology - MRI Super-Resolution Narrative Review

This document details the statistical and ML framework used to analyze factors influencing LMIC relevance and the reporting quality of MRI super-resolution (SR) studies.

## 1. Random Forest Feature Importance

To avoid over-parameterization on the small dataset (n=51 papers), we employed a **Random Forest Regressor** to predict the `LMIC_Relevance_Score` (1-5).

- **Hyperparameters**: 500 decision trees, `min_samples_split=3`, `min_samples_leaf=2`.
- **Validation**: Leave-One-Out Cross-Validation (LOO-CV).
- **Features**: Binary encodings of AI architecture (CNN, GAN, U-Net, Transformer), dataset source (Clinical vs Synthetic), code availability, low-field mentioning, and metrics reported (PSNR/SSIM).
- **Metric**: Gini Importance (Mean Decrease in Impurity) rank based on feature contributions to prediction accuracy.

## 2. Mann-Whitney U & Reporting Bias

We performed pairwise comparisons to test for "Reporting Bias." Studies that report traditional metrics (PSNR/SSIM) were compared against those that do not.

- **Continuous/Ordinal Variables**: Mann-Whitney U test (e.g., comparing `LMIC_Relevance_Score` medians).
- **Categorical Variables**: Pearson's Chi-Square test or Fisher's Exact Test (where N < 5 per cell).
- **Hypothesis**: $H_0$: There is no statistical difference in the characteristics (e.g., low-field focus, code availability) of papers based on their metric reporting status.

## 3. Fleiss' Kappa (Inter-Rater Reliability)

To validate the `LMIC_Relevance_Score`, an 11-reviewer calibration set was analyzed.

- **Statistic**: Fleiss' Kappa ($\kappa$), appropriate for multiple raters and categorical ratings.
- **Interpretation**: Landis & Koch (1977) scale:
    - 0.41 - 0.60: **Moderate Agreement**.
    - 0.61 - 0.80: **Substantial Agreement**.

## 4. Geographic & Socioeconomic Mapping

- **Country Identification**: Pulled from OpenAlex affiliation metadata.
- **Economic Classification**: Mapped via ISO-2 country codes to **World Bank Income Groups** (HIC, UMIC, LMIC, LIC).
- **Equity Analysis**: Binary classification into "HIC (High-Income / Parachute Risk)" vs "Global South (Local Research)" based on the primary/corresponding author's institution.

---

*All analyses are reproducible using the provided scripts and standard `np.random.seed(42)` initialization.*
