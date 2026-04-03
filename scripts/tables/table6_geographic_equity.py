"""
Table 6: Geographic & Economic Equity

Genera paneles con:
  A: Income group distribution (World Bank)
  B: LMIC score by region
  C: Research gaps (countries vs applications)
"""

import sys
from pathlib import Path

# Add project root and scripts/figures to path
sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))
sys.path.insert(0, str(Path(__file__).parent.parent / "data_enrichment"))

import pandas as pd
import numpy as np
from mapper import load_data, get_project_root

# Reproducibilidad
np.random.seed(42)

def create_table6():
    """Genera Table 6 con análisis de equidad geográfica."""
    
    print("\n=== Table 6: Geographic & Economic Equity ===\n")
    
    # Cargar datos
    df = load_data()
    
    # Panel A: Income Group Distribution
    print("Panel A: Income Group Distribution (World Bank Classification)")
    try:
        from world_bank.world_bank_mapper import enrich_papers_with_country_data
        
        # This part requires the enrichment logic previously used in extract_affiliations
        print("⚠ Requiriendo datos de enriquecimiento...")
        # Note: In the final version, this would load the enriched CSV
        
    except Exception as e:
        print(f"⚠ Error en Panel A: {e}")
    
    # Panel B: LMIC Score by Region
    print("\nPanel B: LMIC Score by Application (Proxy for Region)")
    try:
        lmic_by_app = df.groupby("Application_Norm")["LMIC_Score"].agg([
            "count", "mean", "median", "std"
        ]).round(2)
        
        print(lmic_by_app)
        
        out_dir = get_project_root() / "tables"
        out_dir.mkdir(parents=True, exist_ok=True)
        lmic_by_app.to_csv(out_dir / "table6b_lmic_by_application.csv")
        print(f"✓ Guardado: table6b_lmic_by_application.csv")
        
    except Exception as e:
        print(f"⚠ Error en Panel B: {e}")
    
    # Panel C: Research Gaps
    print("\nPanel C: Research Gaps")
    print("  Visualización disponible en heatmaps generados por el pipeline.")
    
    return True

if __name__ == "__main__":
    create_table6()
