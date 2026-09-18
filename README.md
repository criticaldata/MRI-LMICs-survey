# MRI-LMICs Survey — Figure, Table & Statistical Analysis Pipeline

Analysis pipeline for: *Deep Learning Super-Resolution for MRI: Technical Advances and Translational Potential for Low-Resource Settings*.

The reviewer-correction pipeline regenerates the corrected analyses, promoted tables, and affected figures locally. It never publishes data or modifies GitHub.

## Quick Start

```powershell
# Creates the isolated environment if missing; regenerates promoted reviewer-corrected
# tables and affected figures; then runs all offline verifiers and tests.
powershell -ExecutionPolicy Bypass -File scripts/analysis/run_full_reproducibility_pipeline.ps1 -RunDate 20260817

# Supplying the private reviewer workbook additionally regenerates Fleiss'
# kappa, ordinal-weighted agreement, ICC, and the reviewer-consensus Spearman
# sensitivity analysis. The workbook is validated against the canonical title
# order and is never copied into the repository.
powershell -ExecutionPolicy Bypass -File scripts/analysis/run_full_reproducibility_pipeline.ps1 `
  -RunDate 20260909 `
  -PrivateRatingsXlsx C:\private\RECEIVED_SCORES.xlsx
```

## Requirements

- Python 3.11 or higher
- A Python virtual environment (the supplied bootstrap script uses Python 3.11+)

## Statistical & Geographic Equity Pipeline

The pipeline includes advanced analytics for manuscript revision:
- **Random Forest Robustness Supplement**: constrained repeated held-out
  validation with regularized benchmarks; exploratory only.
- **Mann-Whitney U Tests**: Pairwise comparison of study characteristics.
- **Fleiss' Kappa**: final aggregate agreement for 48 studies scored by 11
  reviewers. Individual ratings remain private.
- **Ordinal weighted agreement**: supplementary multi-rater sensitivity analysis
  with linear and quadratic category-distance weights. Individual ratings remain
  private.
- **Intraclass correlation**: supplementary two-way absolute-agreement ICC for
  single ratings and the mean of the 11 reviewers. Individual ratings remain
  private.
- **LMIC--TR Spearman analysis**: primary study-level correlation from
  `data/data-clean.csv` and `data/tr_criteria_evidence.csv`, plus an optional
  reviewer-median sensitivity summary from the private workbook.
- **Geographic Equity**: World Bank income classification mapping.

To regenerate the aggregate agreement outputs from the private workbook, run:

```powershell
python scripts/analysis/statistical/run_fleiss_kappa_from_private_xlsx.py `
  --input-xlsx <private-reviewer-workbook.xlsx> `
  --output-dir tables
```

The command validates the 48-by-11 matrix and writes only aggregate CSV
outputs; it never copies the private workbook into the repository.

To regenerate the supplementary ordinal-weighted agreement outputs from the
same private workbook, run:

```powershell
python scripts/analysis/statistical/run_weighted_kappa_from_private_xlsx.py `
  --input-xlsx <private-reviewer-workbook.xlsx> `
  --output-dir tables `
  --output-xlsx <private-weighted-results.xlsx>
```

This calculates generalized weighted Fleiss agreement for 11 reviewers and
summarizes all 55 pairwise weighted Cohen kappas. The weighted results are
supplementary and do not replace the prespecified standard Fleiss statistics.

To regenerate the supplementary ICC outputs from the same private workbook, run:

```powershell
python scripts/analysis/statistical/run_icc_from_private_xlsx.py `
  --input-xlsx <private-reviewer-workbook.xlsx> `
  --output-dir tables `
  --output-xlsx <private-icc-results.xlsx>
```

The primary ICC is ICC(2,1), two-way random effects with absolute agreement;
ICC(2,k) is also reported for the mean of all 11 reviewers.

To regenerate the reviewer-consensus Spearman sensitivity summary, run:

```powershell
python scripts/analysis/statistical/run_lmic_tr_correlation_from_private_xlsx.py `
  --input-xlsx <private-reviewer-workbook.xlsx> `
  --output-dir tables `
  --canonical-data data/data-clean.csv
```

The runner requires exactly 48 papers in canonical title order and 11 complete
raters for both scores. It validates LMIC scores in 1--5 and TR scores in 0--5
before writing. It then takes the per-paper median across the 11 raters and
writes only `tables/analysis_lmic_tr_correlation_reviewer_consensus.csv`; no
names, individual ratings, private path, or per-paper median is exported.

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

The historical two-reviewer/10-study calibration is archived under provenance
and is not an active result. The current aggregate agreement outputs are
`tables/analysis_fleiss_kappa_summary.csv` and
`tables/analysis_fleiss_kappa_item_agreement.csv`. The supplementary ordinal
weighted outputs are `tables/analysis_weighted_kappa_summary.csv` and
`tables/analysis_weighted_kappa_item_agreement.csv`; the supplementary ICC
output is `tables/analysis_icc_summary.csv`. The canonical Spearman output is
`tables/analysis_lmic_tr_correlation.csv`, and the aggregate reviewer-median
sensitivity is `tables/analysis_lmic_tr_correlation_reviewer_consensus.csv`.

## Data

Source data: `data/data-clean.csv` (48 primary studies; anonymized public corpus).
The separate `data/tr_criteria_evidence.csv` file contains the final
article-level evidence and binary decisions used to reproduce the TR analysis
without modifying the canonical source.
Reviewer identities, reviewer assignments, individual ratings, and historical
calibration files remain local-only and are not part of this repository.

The public study identity contract is `data/included_study_order.csv`. It fixes
the included corpus to canonical `Paper_ID` values 1–48 by title and DOI;
derived tables and the private reviewer workbook are validated against this
contract. Paper 24 is the *Pushing the limits of low-cost ultra-low-field MRI*
study. IDs are never remapped by numeric shifting.

The primary LMIC--TR estimate is the canonical study-level analysis: LMIC is
read from `data/data-clean.csv`, and TR is read from
`data/tr_criteria_evidence.csv`. For all 48 studies, Spearman rho is 0.4059,
the deterministic two-sided 10,000-permutation p-value is 0.00330, and the
10,000-bootstrap percentile 95% CI is 0.1639 to 0.6065 (seed 42; average ranks
for ties). The separate reviewer-median sensitivity gives rho -0.2577,
p = 0.07869, and a 95% CI of -0.5397 to 0.0397. Weighting robustness is not
scorer-dependence robustness: changing TR criterion weights does not test
whether the association changes when scores come from independent reviewers.

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
| LMIC Fleiss' Kappa (11 reviewers, 48 studies) | 0.505 |
| TR Fleiss' Kappa (11 reviewers, 48 studies) | 0.223 |

## More Information

- **Development & testing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Dependencies:** See [pyproject.toml](pyproject.toml)
- **Statistical methods:** See [docs/STATISTICAL_METHODS.md](docs/STATISTICAL_METHODS.md)
- **Current reproducibility and reviewer analyses:** See [docs/REPRODUCIBLE_REVIEW_ANALYSIS.md](docs/REPRODUCIBLE_REVIEW_ANALYSIS.md)
- **Latest local verification:** See [docs/LOCAL_VALIDATION_REPORT_20260908.md](docs/LOCAL_VALIDATION_REPORT_20260908.md)
