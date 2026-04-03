# MRI-LMICs Survey — Figure & Table Generation

Analysis pipeline for: *Deep Learning Super-Resolution for MRI: Technical Advances and Translational Potential for Low-Resource Settings*

Generates all figures (5 main + supplementary) and tables (6 main) for the MRI super-resolution narrative review targeting Nature Machine Intelligence.

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and sync virtual environment
uv sync

# Generate all figures and tables
python scripts/figures/generate_all_figures.py
python scripts/tables/table5_statistical_insights.py
python scripts/tables/table6_geographic_equity.py
```

That's it! Your outputs will be in:
- `figures/main/png/` and `figures/main/pdf/` (5 main figures)
- `tables/` (CSV table files covering 6 tables)

## Requirements

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Statistical & Geographic Equity Pipeline

The pipeline includes advanced analytics for manuscript revision:

- **Random Forest Feature Importance**: Predicts LMIC relevance (exploratory, LOO-CV).
- **Mann-Whitney U Tests**: Pairwise comparison of study characteristics with FDR correction (Benjamini-Hochberg).
- **Fleiss' Kappa**: Inter-rater reliability (2 raters, N=9 calibration subset, kappa=0.697).
- **Geographic Equity**: World Bank income classification mapping via OpenAlex/CrossRef APIs.

## Generate Individual Outputs

```bash
# Main figures
python scripts/figures/fig1_year_distribution.py          # Figure 1: Publication Trends
python scripts/figures/fig2_architecture_distribution.py   # Figure 2: AI Architecture Landscape
python scripts/figures/fig3_lmic_relevance.py              # Figure 3: LMIC Relevance Analysis
python scripts/figures/fig4_performance_comparison.py      # Figure 4: Performance Metrics
python scripts/figures/fig5_field_strength_application.py  # Figure 5: Field Strength & Application

# Main tables
python scripts/tables/table1_study_characteristics.py      # Table 1: Study Characteristics
python scripts/tables/table2_ai_architectures.py           # Table 2: AI Architectures
python scripts/tables/table3_performance_metrics.py        # Table 3: Performance Metrics
python scripts/tables/table4_lmic_applicability.py         # Table 4: LMIC Applicability
python scripts/tables/table5_statistical_insights.py       # Table 5: Statistical Insights
python scripts/tables/table6_geographic_equity.py          # Table 6: Geographic Equity
```

## Verify Installation

```bash
uv run pytest tests/ -v
```

All **24** tests should pass (`pytest tests/ -v`). If you encounter issues, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Data

Source data: `data/data-clean.csv` (48 primary studies, 2 raters for calibration).
Corrected dataset (v1.1.0) refined from the original pool of 183 papers.

See [data/README.md](data/README.md) for dataset governance and field descriptions.

## Key Findings

| Metric | Value |
| ------ | ----- |
| Papers included (Primary Studies) | 48 |
| Inter-rater Agreement (Fleiss' Kappa) | 0.697 (Substantial) |
| High LMIC relevance (Score 4-5) | 19 (39.6%) |
| Random Forest Top Predictor | Field Strength Accessibility |
| Dominant Region | High-Income Countries (HIC) |

## Output Traceability

| Component | Generator Script | Output Artifact |
| --------- | ---------------- | --------------- |
| **Figure 1** (Trends) | `fig1_year_distribution.py` | `figures/main/pdf/` |
| **Figure 2** (Models) | `fig2_architecture_distribution.py` | `figures/main/pdf/` |
| **Figure 3** (LMIC) | `fig3_lmic_relevance.py` | `figures/main/pdf/` |
| **Figure 4** (Metrics) | `fig4_performance_comparison.py` | `figures/main/pdf/` |
| **Figure 5** (Fields) | `fig5_field_strength_application.py` | `figures/main/pdf/` |
| **Table 1** | `table1_study_characteristics.py` | `tables/` |
| **Table 2** | `table2_ai_architectures.py` | `tables/` |
| **Table 3** | `table3_performance_metrics.py` | `tables/` |
| **Table 4** | `table4_lmic_applicability.py` | `tables/` |
| **Table 5** (Stats/RF) | `table5_statistical_insights.py` | `tables/` |
| **Table 6** (Geography) | `table6_geographic_equity.py` | `tables/` |

## Citation

If you use this repository, data, or pipeline in your work, please cite the corresponding manuscript and software. See `CITATION.cff` for structured metadata.

## More Information

- **Statistical methodology:** See [docs/STATISTICAL_METHODS.md](docs/STATISTICAL_METHODS.md)
- **Scientometrics pipeline:** See [docs/SCIENTOMETRICS_METHODOLOGY.md](docs/SCIENTOMETRICS_METHODOLOGY.md)
- **Architecture overview:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Development & testing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Dependencies:** See [pyproject.toml](pyproject.toml)
