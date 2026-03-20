# MRI-LMICs Survey — Figure & Table Generation

Analysis pipeline for: *Deep Learning Super-Resolution for MRI: Technical Advances and Translational Potential for Low-Resource Settings*

Generates all figures (5 main + supplementary) and tables (4 main) for the MRI super-resolution narrative review targeting Nature Machine Intelligence.

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Generate all figures and tables
python scripts/figures/generate_all_figures.py
```

That's it! Your outputs will be in:
- `figures/main/png/` and `figures/main/pdf/` (5 main figures)
- `tables/` (9 CSV table files covering 4 tables)

## Requirements

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Generate Individual Figures

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
```

## Verify Installation

```bash
pytest tests/ -v
```

All 17 tests should pass. If you encounter issues, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Data

Source data: `data/mri_sr_extraction.csv` (56 papers, 32 extraction fields across 11 reviewers)

Extracted from 56 MRI super-resolution papers published 2020–2025, filtered from an initial pool of 183 papers.

## Key Findings

| Metric | Value |
|--------|-------|
| Papers included | 56 |
| Brain MRI (dominant area) | 27 (48.2%) |
| CNN (most common architecture) | 26 (46.4%) |
| Low-field MRI mentioned | 15 (26.8%) |
| High LMIC relevance (Score 4–5) | 19 (33.9%) |
| Clinical validation reported | 21 (37.5%) |
| Code publicly available | 9 (16.1%) |
| Median PSNR | 34.1 dB |
| Median SSIM | 0.913 |

## More Information

- **Development & testing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Dependencies:** See [pyproject.toml](pyproject.toml)
