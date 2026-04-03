"""
Tests para módulos de enriquecimiento de datos (World Bank).
"""

import sys
from pathlib import Path

# Add project root and figures/data_enrichment to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "figures"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "data_enrichment"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "data_enrichment" / "world_bank"))

import pytest
from mapper import load_data


def test_cache_directory_exists():
    """Test que el directorio de caché de datos existe."""
    cache_path = Path("data/.cache")
    assert cache_path.exists(), "Cache directory doesn't exist"


def test_data_enrichment_schema_integrity():
    """Test que la carga de datos mantiene el esquema requerido."""
    df = load_data()
    
    # Debería haber al menos las columnas originales
    required_cols = {
        "Paper_ID", "Year", "LMIC_Score", "Application_Norm"
    }
    
    assert required_cols.issubset(set(df.columns)), f"Missing columns: {required_cols - set(df.columns)}"


def test_country_mapping_stub():
    # Note: Import depends on the sys.path.insert above
    from world_bank_mapper import get_world_bank_group, get_equity_classification
    
    # Test la lógica de clasificación de equidad
    assert get_equity_classification("HIC") == "HIC (High-Income / Parachute Risk)"
    assert get_equity_classification("LMIC") == "Global South (Local Research)"
    assert get_equity_classification("UNKNOWN") == "UNKNOWN (Manual Review)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
