# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.1.0] - NMI Pipeline Alignment (2026-04)

### Added
- `test_data_consistency.py` testing module to ensure triple-loader consistency across `mapper.py`, Random Forest, and Mann-Whitney U modules.
- `data/README.md` to document the state and governance of the immutable dataset (`data-clean.csv`).
- `docs/SCIENTOMETRICS_METHODOLOGY.md` explaining OpenAlex and World Bank integration for geographic equity tracking (Table 6).
- Explicit `q_value_fdr` variable outputs tracking Benjamini-Hochberg False Discovery Rate corrections in all tables reporting Mann-Whitney U P-values.
- Clamp for Fleiss' Kappa confidence intervals tracking theoretical minimum and maximums. 
- Python `uv` workflow instructions.

### Changed
- Refactored `mapper.load_data()` to be the sole orchestrator of data structure.
- Removed legacy `review_mask` references that were improperly masking `N=48` down to `N=41` within ML pipelines.
- Standardized document references and key manuscript findings across `README.md`, `ARCHITECTURE.md`, `STATISTICAL_METHODS.md`, and `CONTRIBUTING.md` (e.g. legacy N=51 -> N=48, legacy 11-reviewers -> 2-raters framework).
- Rephrased theoretical implications of Fleiss' Kappa when utilizing `n=2` raters ensuring methodological correctness for NMI tracking.

### Deprecated
- `mri_sr_extraction.csv` replaced entirely by programmatic mapping output from `data-clean.csv` to ensure unified inputs across descriptive figures and analytical modeling. 
