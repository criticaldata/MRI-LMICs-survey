# Dataset & Governance (MRI-LMICs-survey)

This directory contains the core datasets powering the MRI Super-Resolution and LMIC Equity survey.

## Base Files

- **`data-clean.csv` (v1.1.0)**: The single source of truth for the statistical and scientometric pipeline.
  - Contains **N=48 primary studies** manually extracted and cleaned.
  - Fields include metadata (Title, Year, DOI), application areas, field strength, architecture types, performance metrics (PSNR, SSIM), and the manually graded `LMIC_Score` (1-5).
  - This file replaces legacy datasets (such as `mri_sr_extraction.csv`) to ensure alignment across Random Forest, Mann-Whitney, and table/figure generation pipelines.

- **`excluded_papers.csv`**: Contains the records of studies that were excluded during the full-text screening process. Note: This file does not participate in the core analytical pipeline (`test_data_consistency.py` explicitly tracks `data-clean.csv`).

- **`fleiss_kappa_matrix.csv`**: The calibration dataset containing blind ratings across a subset of 9 papers randomly selected to compute the Fleiss' Kappa inter-rater agreement for `LMIC_Score`. It involves 2 raters.

- **`.cache/`**: Contains locally cached JSON responses from external APIs (such as OpenAlex and World Bank) to prevent rate limiting and ensure deterministic testing over a 30-day window.

## Data Governance & Contribution Policy

1. **Immutability**: `data-clean.csv` is considered immutable by the scripts. All programmatic normalization (e.g., categorizing architectures, converting Yes/No values) occurs dynamically at load time via `scripts/figures/mapper.py -> load_data()`.
2. **Sensitive Data**: This repository is public and is not permitted to host any protected health information (PHI) or sensitive raw medical images. Only aggregated bibliographic and systematic review metadata is tracked.
3. **Licensing**: Data is provided under an open-access license (CC-BY 4.0 or equivalent, subject to final manuscript publication terms) specifically for reproducing the results in the Nature Machine Intelligence submission. 
