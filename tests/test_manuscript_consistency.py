import pandas as pd
import pytest
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TABLES_DIR = PROJECT_ROOT / "tables"
DATA_DIR = PROJECT_ROOT / "data"

def test_primary_studies_count():
    """Verify Table 1 reports exactly 48 primary studies."""
    table1_path = TABLES_DIR / "table1_study_characteristics.csv"
    assert table1_path.exists(), "Table 1 is missing."
    
    df = pd.read_csv(table1_path)
    total_row = df[df['Characteristic'] == 'Total papers included']
    assert not total_row.empty, "Total papers row missing from Table 1."
    
    n_papers = int(total_row['n'].iloc[0])
    assert n_papers == 48, f"Expected 48 papers, found {n_papers}."

def test_calibration_subset_count():
    """Verify Fleiss' Kappa results are based on exactly 10 subjects."""
    kappa_results_path = TABLES_DIR / "module3_fleiss_kappa_results.csv"
    assert kappa_results_path.exists(), "Kappa results file is missing."
    
    df = pd.read_csv(kappa_results_path)
    n_subjects = int(df['N_subjects'].iloc[0])
    assert n_subjects == 10, f"Expected 10 subjects in calibration subset, found {n_subjects}."

def test_kappa_value_and_clamping():
    """Verify Fleiss' Kappa is precisely 0.728 and CI upper is clamped to 1.0."""
    kappa_results_path = TABLES_DIR / "module3_fleiss_kappa_results.csv"
    assert kappa_results_path.exists(), "Kappa results file is missing."
    
    df = pd.read_csv(kappa_results_path)
    kappa = float(df['Fleiss_Kappa'].iloc[0])
    ci_upper = float(df['CI_95_Upper'].iloc[0])
    
    # Check Kappa (rounded to 3 decimal places)
    assert round(kappa, 3) == 0.728, f"Expected Kappa 0.728, found {kappa:.3f}."
    
    # Check CI Clamping
    assert ci_upper == 1.0, f"Expected CI upper limit to be clamped to 1.0, found {ci_upper}."

def test_data_integrity():
    """Verify data-clean.csv has exactly 48 rows."""
    data_path = DATA_DIR / "data-clean.csv"
    assert data_path.exists(), "data-clean.csv is missing."
    
    df = pd.read_csv(data_path)
    assert len(df) == 48, f"Expected 48 rows in data-clean.csv, found {len(df)}."

if __name__ == "__main__":
    pytest.main([__file__])
