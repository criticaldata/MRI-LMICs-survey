# MRI-LMICs Survey — Figure, Table & Statistical Analysis Pipeline

Analysis pipeline for: *Deep Learning Super-Resolution for MRI: Technical Advances and Translational Potential for Low-Resource Settings*.

The reviewer-correction pipeline regenerates the corrected analyses, promoted tables, and affected figures locally. It never publishes data or modifies GitHub.

## Quick Start

```powershell
# Creates the isolated environment if missing; regenerates promoted reviewer-corrected
# tables and affected figures; then runs all offline verifiers and tests.
powershell -ExecutionPolicy Bypass -File scripts/analysis/run_full_reproducibility_pipeline.ps1 -RunDate 20260808
```

## Requirements

- Python 3.11 or higher
- A Python virtual environment (the supplied bootstrap script uses Python 3.11+)

## Statistical & Geographic Equity Pipeline

The pipeline includes advanced analytics for manuscript revision:
- **Random Forest Robustness Supplement**: constrained repeated held-out
  validation with regularized benchmarks; exploratory only.
- **Mann-Whitney U Tests**: Pairwise comparison of study characteristics.
- **Fleiss' Kappa**: prepared for 11 independent reviewers; pending receipt of
  the complete ratings.
- **Geographic Equity**: World Bank income classification mapping.

## Generate Individual Outputs

```bash
# Main figures
python scripts/figures/fig1_year_distribution.py          # Figure 1: Publication Trends
python scripts/figures/fig2_architecture_distribution.py   # Figure 2: AI Architecture Landscape
python scripts/figures/fig3_lmic_relevance.py              # Figure 3: LMIC Relevance Analysis
python scripts/figures/fig4_performance_comparison.py      # Figure 4: Performance Metrics
python scripts/figures/fig5_field_strength_application.py  # Figure 5: Field Strength & Application
# Figure 6: Translational Roadmap (Manual PNG, converted to PDF by master script)

# Main tables
python scripts/tables/table1_study_characteristics.py      # Table 1: Study Characteristics
python scripts/tables/table2_ai_architectures.py           # Table 2: AI Architectures
python scripts/tables/table3_performance_metrics.py        # Table 3: Performance Metrics
python scripts/tables/table4_lmic_applicability.py         # Table 4: LMIC Applicability
python scripts/tables/table5_statistical_insights.py       # Table 5: Statistical Insights
python scripts/tables/table6_geographic_equity.py          # Table 6: Geographic Equity
```

## Verify Installation

```powershell
& .\.venv-reproducible\Scripts\python.exe -m pytest -q
```

The 2026-08-08 local validation ran 34 tests successfully. The historical
two-reviewer/10-study calibration is archived under provenance and is not an
active result. Final Fleiss' kappa remains pending until all 11 independent
reviewer files are returned and validated.

## Data

Source data: `data/data-clean.csv` (48 primary studies; anonymized public corpus).
Reviewer identities, reviewer assignments, individual ratings, and historical
calibration files remain local-only and are not part of this repository.

Corrected dataset refined from an initial pool of 183 papers (2020-2025).

## Key Findings

| Metric | Value |
| :--- | :--- |
| Papers included (Primary Studies) | 48 |
| Brain MRI (dominant area) | 24 (50.0%) |
| CNN (most common architecture) | 23 (47.9%) |
| Low-field MRI mentioned | 14 (29.2%) |
| High LMIC relevance (Score 4-5) | 19 (39.6%) |
| Clinical validation reported | 19 (39.6%) |
| Code publicly available | 6 (12.5%) |
| Median PSNR | 32.6 dB |
| Median SSIM | 0.917 |
| Inter-rater Agreement (Fleiss' Kappa) | Pending 11 independent ratings |

## More Information

- **Development & testing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Dependencies:** See [pyproject.toml](pyproject.toml)
- **Statistical methods:** See [docs/STATISTICAL_METHODS.md](docs/STATISTICAL_METHODS.md)
- **Current reproducibility and reviewer analyses:** See [docs/REPRODUCIBLE_REVIEW_ANALYSIS.md](docs/REPRODUCIBLE_REVIEW_ANALYSIS.md)
- **Latest local verification:** See [docs/LOCAL_VALIDATION_REPORT_20260808.md](docs/LOCAL_VALIDATION_REPORT_20260808.md)
