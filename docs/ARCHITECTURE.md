# Repository Architecture - MRI-LMICs-survey (Scientometrics Extension)

This extension integrates advanced statistical analysis and geographic equity assessment into the core MRI super-resolution survey pipeline.

## 1. Directory Structure

```text
MRI-LMICs-survey/
├── data/
│   ├── data-clean.csv          # REVISED: 48 primary studies (validated)
│   └── fleiss_kappa_matrix.csv # Calibration set for 2 raters
├── docs/
│   ├── ARCHITECTURE.md              # Current file
│   ├── STATISTICAL_METHODS.md       # RF, MW-U, κ, FDR
│   └── SCIENTOMETRICS_METHODOLOGY.md # OpenAlex / World Bank / Table 6
├── scripts/
│   ├── analysis/
│   │   └── statistical/        # CORE BUSINESS LOGIC
│   │       ├── random_forest_training.py
│   │       ├── mann_whitney_tests.py
│   │       ├── fleiss_kappa_calculation.py
│   │       └── utils.py          # Shared normalization logic
│   ├── data_enrichment/
│   │   └── world_bank/         # EXTERNAL API INTEGRATION
│   │       ├── world_bank_fetcher.py
│   │       └── world_bank_mapper.py
│   └── tables/                 # OUTPUT GENERATORS
│       ├── table5_statistical_insights.py
│       └── table6_geographic_equity.py
├── tests/
│   ├── test_data_consistency.py # Enforces mapper / RF / Mann–Whitney N parity
│   ├── test_manuscript_consistency.py # Verifies N=48, Kappa=0.728, CI Clamping
│   └── analysis/                # Validation & statistical smoke tests
├── CHANGELOG.md
├── CITATION.cff
└── 06_processing_outputs/      # Logs and temporary artifacts (gitignored)
```

## 2. Integrated Data Flow

1.  **Normalization**: All statistical modules import `utils.py` to ensure architectures, field strengths, and metrics are normalized identically across the repo. Also, data loading logic explicitly shares definitions under `mapper.load_data()` allowing for a triple-aligned path mapping (mapper / RF / Mann-Whitney), which is enforced by the `tests/test_data_consistency.py` CI pipeline.
2.  **Enrichment**: `world_bank_fetcher.py` queries OpenAlex for author affiliations and maps them to World Bank income groups using `world_bank_mapper.py`.
3.  **Synthesis**: `table5` and `table6` act as orchestrators, calling the analysis modules and generating publication-ready CSVs in the `tables/` directory.

## 3. Reliability & Reproducibility

- **Seed Control**: All ML models and data splits use `np.random.seed(42)`.
- **Cross-Validation**: Random Forest uses Leave-One-Out (LOO) CV for the small dataset (n=48 effective).
- **Audit Trails**: Every module execution creates a timestamped log in `06_processing_outputs/`.
