import json
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

def test_historical_calibration_is_archived_not_active():
    """The 10-study/two-rater exercise cannot appear as final IRR output."""
    assert not (TABLES_DIR / "module3_fleiss_kappa_results.csv").exists()
    assert not (DATA_DIR / "fleiss_kappa_matrix.csv").exists()


def test_full_irr_is_explicitly_pending():
    """Do not present the provisional calibration as the 11-reviewer IRR."""
    manifest_path = DATA_DIR / "public_release_manifest.json"
    assert manifest_path.exists(), "Public release manifest is missing."
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["fleiss_kappa_status"] == "pending_until_complete_independent_ratings"

def test_data_integrity():
    """Verify data-clean.csv has exactly 48 rows."""
    data_path = DATA_DIR / "data-clean.csv"
    assert data_path.exists(), "data-clean.csv is missing."
    
    df = pd.read_csv(data_path)
    assert len(df) == 48, f"Expected 48 rows in data-clean.csv, found {len(df)}."

if __name__ == "__main__":
    pytest.main([__file__])
