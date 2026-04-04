# Contributing Guide

This guide contains detailed information for developers and contributors working on the MRI-LMICs survey project.

## System Requirements

- **Python:** 3.11 or higher (tested with Python 3.12)
- **Operating System:** macOS, Linux, or Windows
- **Memory:** At least 2GB RAM recommended
- **UV:** Latest version (for dependency management)

## Development Setup

### Using UV (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/criticaldata/MRI-LMICs-survey.git
cd MRI-LMICs-survey

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Traditional Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Testing

### Running Tests

The project includes comprehensive tests to ensure reproducibility and correctness.

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/analysis/test_data_validation.py -v   # Test data integrity
pytest tests/test_data_consistency.py -v           # Mapper / RF / Mann–Whitney N alignment
pytest tests/test_figure_generation.py -v        # Figure generation (smoke tests)
pytest tests/analysis/test_statistical_analysis.py -v
```

### Test Coverage

The test suite includes:

1. **Data Validation Tests** ([tests/analysis/test_data_validation.py](tests/analysis/test_data_validation.py))
   - Verifies `data/data-clean.csv` exists
   - Checks for 48 papers with all required columns
   - Validates normalized columns are created correctly
   - Ensures LMIC scores are in valid range (1–5)
   - Validates SSIM values are in [0, 1]
   - Checks year range (2019–2026)
   - Confirms all extractions are marked complete

2. **Data consistency** ([tests/test_data_consistency.py](tests/test_data_consistency.py)): mapper vs Random Forest vs Mann–Whitney share the same effective *N* and numeric LMIC score.

3. **Statistical smoke tests** ([tests/analysis/test_statistical_analysis.py](tests/analysis/test_statistical_analysis.py)): `load_data` and `engineer_features` on the canonical CSV.

4. **Figure Generation Tests** ([tests/test_figure_generation.py](tests/test_figure_generation.py))
   - Verifies all 5 figure scripts and table scripts exist
   - Tests mapper.py is importable
   - Parametrized smoke tests for `TABLE_SCRIPTS` in `test_figure_generation.py` (tables 1–4); run `table5_statistical_insights.py` and `table6_geographic_equity.py` per README for full analytics outputs
   - Smoke tests for first 2 figure scripts

Expected: **24 tests passing** in ~4–6 seconds

### Adding New Tests

When adding new figure scripts or modifying existing ones:

1. Add the script name to `FIGURE_SCRIPTS` or `TABLE_SCRIPTS` in [tests/test_figure_generation.py](tests/test_figure_generation.py)
2. Consider adding a smoke test if the figure has unique requirements
3. Run the full test suite to ensure nothing breaks

## Project Structure

```
MRI-LMICs-survey/
├── data/
│   └── data-clean.csv             # Source data (48 primary studies)
├── scripts/
│   ├── figures/
│   │   ├── mapper.py              # Centralized mappings, utilities, color schemes
│   │   ├── generate_all_figures.py  # Master generation script
│   │   └── fig*.py                # Individual figure scripts (5 main)
│   └── tables/
│       └── table*.py              # Individual table scripts (4 main)
├── figures/
│   ├── main/
│   │   ├── png/                   # Main figures (PNG, 300 DPI)
│   │   └── pdf/                   # Main figures (PDF, vector)
│   └── supplementary/
│       ├── png/                   # Supplementary figures
│       └── pdf/                   # Supplementary figures
├── tables/                        # Generated CSV tables
├── tests/
│   ├── test_data_consistency.py   # Triple-loader N alignment
│   ├── test_figure_generation.py  # Figure / table smoke tests
│   └── analysis/
│       ├── test_data_validation.py
│       ├── test_statistical_analysis.py
│       └── test_data_enrichment.py
├── pyproject.toml                 # Project configuration and dependencies
├── README.md                      # Quick start guide
└── CONTRIBUTING.md                # This file
```

## Reproducibility

### Guaranteed Reproducibility

All figures use `np.random.seed(42)` for reproducible layouts and jittering. To ensure identical output across different machines:

1. **Same Python version:** Use Python 3.11 or 3.12
2. **Same dependencies:** Install using `uv` or the exact versions in [pyproject.toml](pyproject.toml)
3. **Same data:** Use the provided [data/data-clean.csv](data/data-clean.csv)
4. **Run from repository root:** Always run scripts from the repository root directory

### Verification Steps

Complete verification workflow:

```bash
# 1. Verify Python version
python --version  # Should be 3.11+

# 2. Verify data integrity
pytest tests/analysis/test_data_validation.py -v

# 3. Verify figure generation works
pytest tests/test_figure_generation.py -v

# 4. Generate all figures and tables
python scripts/figures/generate_all_figures.py

# 5. Verify outputs exist
ls -lh figures/main/png/  # Should contain 5 PNG files
ls -lh figures/main/pdf/  # Should contain 5 PDF files
ls -lh tables/            # Should contain 9 CSV files
```

## Data Pipeline

All data normalization happens in `mapper.py` via centralized mapping dictionaries:

```
Raw CSV → load_data() → Normalize categories → Parse metrics → Clean DataFrame
                           ├── APPLICATION_MAP     (10 canonical areas)
                           ├── ARCHITECTURE_MAP     (8 canonical types)
                           ├── FIELD_STRENGTH_MAP   (5 canonical types)
                           ├── PRIMARY_FOCUS_MAP    (8 canonical types)
                           ├── LMIC_SCORE_MAP       (text → numeric 1-5)
                           ├── YES_NO_MAP           (normalize Yes/No variants)
                           └── _parse_first_numeric (PSNR/SSIM extraction)
```

The CSV is **never modified**. All transformations happen at load time.

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError` when running scripts
- **Solution:** Ensure you've activated your virtual environment and installed dependencies:
  ```bash
  source .venv/bin/activate
  uv pip install -e ".[dev]"
  ```

**Issue:** Figures look different from paper
- **Solution:** Verify you're using the correct Python version (3.11+) and have installed exact dependency versions:
  ```bash
  python --version
  uv pip list | grep -E "(pandas|numpy|matplotlib|seaborn)"
  ```

**Issue:** Tests fail with import errors
- **Solution:** Install the package in editable mode:
  ```bash
  uv pip install -e ".[dev]"
  ```

**Issue:** UV not found
- **Solution:** Install uv:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source $HOME/.cargo/env
  ```

### Getting Help

If you encounter issues not covered here:

1. **Run tests to identify the problem:**
   ```bash
   pytest tests/ -v
   ```

2. **Check dependencies:**
   ```bash
   uv pip list | grep -E "(pandas|numpy|matplotlib|seaborn|openpyxl)"
   ```

3. **Check for existing issues:**
   - Review open issues at [github.com/criticaldata/MRI-LMICs-survey](https://github.com/criticaldata/MRI-LMICs-survey/issues)

## Dependencies

All dependencies are managed in [pyproject.toml](pyproject.toml):

### Core Dependencies
- `pandas>=2.2.0` — Data manipulation and aggregation
- `numpy>=1.26.0` — Numerical computing
- `matplotlib>=3.8.0` — Publication-quality plotting
- `seaborn>=0.13.0` — Statistical visualization
- `openpyxl>=3.1.0` — Excel file reading

### Development Dependencies
- `pytest>=8.0.0` — Testing framework

## Code Style

- Use meaningful variable names
- Add docstrings to all scripts and functions
- Use the shared `mapper.py` for all data loading and color schemes
- Follow existing patterns: `np.random.seed(42)` at top of every figure script
- Publication-quality defaults: 300 DPI, Arial/Helvetica, PDF type 42 fonts

## Making Changes

1. Create a new branch for your changes
2. Make your modifications
3. Run the test suite: `pytest tests/ -v`
4. Generate all figures to verify: `python scripts/figures/generate_all_figures.py`
5. Commit your changes with clear messages
6. Submit a pull request

## Data

- **Source:** `data/data-clean.csv` (48 papers, extracted from the original pool)
- **Reviewers:** 2 raters calibrated using a N=10 paper subset
- **Scope:** MRI super-resolution papers published 2020–2025
- **LMIC scoring:** 1–5 scale assessing relevance to low- and middle-income countries

### Data Validation

The data is validated by automated tests to ensure:
- All 48 primary studies are present and marked as extraction complete
- Required columns exist (Paper_ID, Title, Year, etc.)
- LMIC scores are in valid range (1–5)
- SSIM values are in valid range (0–1)
- Publication years are within expected range (2019–2026)
- All normalized columns are created correctly
