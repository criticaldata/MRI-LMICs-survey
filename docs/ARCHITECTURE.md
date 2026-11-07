# Repository Architecture - MRI-LMICs-survey (Scientometrics Extension)

This extension integrates advanced statistical analysis and geographic equity assessment into the core MRI super-resolution survey pipeline.

> The current source of truth is `REPRODUCIBLE_REVIEW_ANALYSIS.md`. The
> 2-rater/10-paper Fleiss kappa is calibration only and is not final IRR.

## 1. Directory Structure

```text
MRI-LMICs-survey/
├── data/
│   └── data-clean.csv          # Anonymized public corpus: 48 primary studies
├── docs/
│   ├── ARCHITECTURE.md              # Current file
│   ├── STATISTICAL_METHODS.md       # RF, MW-U, κ, FDR
│   └── SCIENTOMETRICS_METHODOLOGY.md # Multi-source adapter and coverage
├── scripts/
│   ├── analysis/
│   │   └── statistical/        # CORE BUSINESS LOGIC
│   │       ├── random_forest_training.py
│   │       ├── mann_whitney_tests.py
│   │       ├── run_fleiss_kappa_from_private_xlsx.py
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
│   ├── test_manuscript_consistency.py # Verifies current corpus and consistency invariants
│   └── analysis/                # Validation & statistical smoke tests
├── CHANGELOG.md
├── CITATION.cff
└── 06_processing_outputs/      # Logs and temporary artifacts (gitignored)
```

## 2. Integrated Data Flow

1.  **Normalization**: Field-strength categories are defined once in `scripts/field_taxonomy.py`; `mapper.py`, `review_metrics.py`, and the statistical `utils.py` wrapper use that function. Numeric bins are assigned only when T/mT is reported, while generic labels remain unquantified. The TR low-field criterion (`<=64 mT`) is a separate rule, and input/target field strengths remain separate evidence fields. Shared data-loading logic is provided by `mapper.load_data()`.
2.  **Enrichment**: `world_bank_fetcher.py` queries OpenAlex for author affiliations and maps them to World Bank income groups using `world_bank_mapper.py`.
3.  **Synthesis**: `table5` and `table6` act as orchestrators, calling the analysis modules and generating publication-ready CSVs in the `tables/` directory.

## 3. Reliability & Reproducibility

- **Seed Control**: All ML models and data splits use `np.random.seed(42)`.
- **Cross-Validation**: the current supplementary forest uses repeated 5-fold held-out validation (10 repeats; 50 test splits).
- **Audit Trails**: Every module execution creates a timestamped log in `06_processing_outputs/`.
- **Privacy boundary**: reviewer names, assignments, individual ratings, raw
  provider responses, and credential files are intentionally excluded from the
  public repository. Only aggregate reviewer agreement results are tracked.
