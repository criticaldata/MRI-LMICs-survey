"""
Table 5: Statistical Insights

Genera paneles con:
  A: Random Forest feature importance
  B: Mann-Whitney U test results (pairwise comparisons)
  C: Fleiss' Kappa inter-rater reliability
"""

import sys
from pathlib import Path

# Add project root and scripts/figures to path
sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))
sys.path.insert(0, str(Path(__file__).parent.parent / "analysis" / "statistical"))

import pandas as pd
import numpy as np
from mapper import load_data, get_project_root

# Reproducibilidad
np.random.seed(42)

def create_table5():
    """Genera Table 5 con resultados estadísticos."""
    
    print("\n=== Table 5: Statistical Insights ===\n")
    
    # Cargar datos
    df = load_data()
    
    # Panel A: Random Forest Feature Importance
    print("Panel A: Random Forest Feature Importance")
    try:
        from random_forest_training import train_random_forest, prepare_features
        
        X, y, features = prepare_features(df)
        rf = train_random_forest(X, y)
        
        importance_df = pd.DataFrame({
            'Feature': features,
            'Importance': rf.feature_importances_,
            'Importance_%': rf.feature_importances_ * 100
        }).sort_values('Importance', ascending=False)
        
        print(importance_df.to_string(index=False))
        
        # Guardar
        out_dir = get_project_root() / "tables"
        out_dir.mkdir(parents=True, exist_ok=True)
        importance_df.to_csv(
            out_dir / "table5a_random_forest_features.csv",
            index=False
        )
        print(f"✓ Guardado: table5a_random_forest_features.csv\n")
        
    except Exception as e:
        print(f"⚠ Error en Panel A: {e}\n")
    
    # Panel B: Mann-Whitney U Test Results
    print("Panel B: Mann-Whitney U Test Results")
    try:
        from mann_whitney_tests import run_mann_whitney_tests
        
        mw_results = run_mann_whitney_tests(df)
        print(mw_results.to_string(index=False))
        
        out_dir = get_project_root() / "tables"
        mw_results.to_csv(
            out_dir / "table5b_mann_whitney_results.csv",
            index=False
        )
        print(f"✓ Guardado: table5b_mann_whitney_results.csv\n")
        
    except Exception as e:
        print(f"⚠ Error en Panel B: {e}\n")
    
    # Panel C: Fleiss' Kappa
    print("Panel C: Fleiss' Kappa Inter-Rater Agreement")
    try:
        from fleiss_kappa_calculation import calculate_kappa
        
        kappa_results = calculate_kappa(df)
        print(kappa_results)
        
        out_dir = get_project_root() / "tables"
        if isinstance(kappa_results, pd.DataFrame):
            kappa_results.to_csv(
                out_dir / "table5c_fleiss_kappa.csv",
                index=False
            )
        print(f"✓ Guardado: table5c_fleiss_kappa.csv\n")
        
    except Exception as e:
        print(f"⚠ Error en Panel C: {e}\n")
    
    return True

if __name__ == "__main__":
    create_table5()
