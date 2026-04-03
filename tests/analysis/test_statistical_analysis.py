"""
Tests para módulos de análisis estadístico.
"""

import sys
from pathlib import Path

# Add project root and relevant scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "figures"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "analysis" / "statistical"))

import pytest
import numpy as np
from mapper import load_data


def test_data_loads_correctly():
    """Test que load_data retorna 51 papers."""
    df = load_data()
    assert len(df) == 51, f"Expected 51 papers, got {len(df)}"
    assert "LMIC_Score" in df.columns


def test_random_seed_reproducibility():
    """Test que np.random.seed(42) produce resultados reproducibles."""
    np.random.seed(42)
    array1 = np.random.rand(10)
    
    np.random.seed(42)
    array2 = np.random.rand(10)
    
    np.testing.assert_array_equal(array1, array2)


def test_random_forest_preparation():
    """Test que la preparación de features para RF funciona."""
    from random_forest_training import engineer_features
    import io
    
    df = load_data()
    # Mock log file
    log_file = io.StringIO()
    X, y, features, _ = engineer_features(df, log_file)
    
    assert X.shape[0] == 51, f"Expected 51 samples, got {X.shape[0]}"
    assert len(features) > 0, "No features identified"
    assert len(y) == 51, "Target vector length mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
