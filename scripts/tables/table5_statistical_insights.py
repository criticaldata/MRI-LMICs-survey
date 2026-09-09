"""
Table 5: Statistical Insights

Generates panels for:
  A: Random Forest Feature Importance (Leave-One-Out CV)
  B: Mann-Whitney U test results (Reporting Bias)
  C: Fleiss' Kappa inter-rater agreement (Moderate-Substantial)
"""

import sys
import io
from pathlib import Path

# Add project root and scripts/figures to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "figures"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "analysis" / "statistical"))

import pandas as pd
import numpy as np
from mapper import load_data, get_project_root

# Feature Importance logic
from random_forest_training import engineer_features, train_and_evaluate
# Mann-Whitney logic
from mann_whitney_tests import run_mann_whitney, run_chi_square
# Reproducibility
np.random.seed(42)

def create_table5():
    """Generates Table 5 with synthesized statistical results."""
    
    print("\n=== Table 5: Statistical Insights ===\n")
    
    # Load data
    df = load_data()
    
    # Mock log file (to satisfy signatures)
    log_file = io.StringIO()
    
    # --- PANEL A: RANDOM FOREST ---
    print("Panel A: Random Forest Feature Importance")
    try:
        X, y, feature_names, _ = engineer_features(df, log_file)
        model, importances, metrics = train_and_evaluate(X, y, feature_names, log_file)
        
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances,
            'Importance_%': importances * 100
        }).sort_values('Importance', ascending=False)
        
        print(importance_df.to_string(index=False))
        
        out_dir = get_project_root() / "tables"
        out_dir.mkdir(parents=True, exist_ok=True)
        importance_df.to_csv(out_dir / "table5a_random_forest_features.csv", index=False)
        print(f"✓ Saved: table5a_random_forest_features.csv\n")
        
    except Exception as e:
        print(f"⚠ Error in Panel A: {e}")
        import traceback
        print(traceback.format_exc())

    # --- PANEL B: MANN-WHITNEY U ---
    print("Panel B: Mann-Whitney U Test Results")
    try:
        # Note: mann_whitney_tests.py usually re-loads data, but we can call functions directly
        # For simplicity in this orchestrator, we run the tests using the modules' internal prepare logic
        mw_results = run_mann_whitney(df, log_file)
        chi_results = run_chi_square(df, log_file)
        
        combined_stats = pd.concat([mw_results, chi_results], axis=0, ignore_index=True)
        print(combined_stats[['Variable', 'p_value', 'Significant']].to_string(index=False))
        
        combined_stats.to_csv(out_dir / "table5b_mann_whitney_results.csv", index=False)
        print(f"✓ Saved: table5b_mann_whitney_results.csv\n")
        
    except Exception as e:
        print(f"⚠ Error in Panel B: {e}")

    # --- PANEL C: FLEISS KAPPA ---
    print("Panel C: Fleiss' Kappa Inter-Rater Agreement")
    try:
        # Read the aggregate output generated from the private reviewer workbook.
        summary_path = PROJECT_ROOT / "tables" / "analysis_fleiss_kappa_summary.csv"

        if summary_path.exists():
            kappa_df = pd.read_csv(summary_path)
            print(kappa_df[["Analysis", "Fleiss_kappa"]].to_string(index=False))
            kappa_df.to_csv(out_dir / "table5c_fleiss_kappa.csv", index=False)
            print(f"✓ Saved: table5c_fleiss_kappa.csv\n")
        else:
            print(
                "⚠ Aggregate kappa summary missing. Run "
                "run_fleiss_kappa_from_private_xlsx.py with the private workbook."
            )
            
    except Exception as e:
        print(f"⚠ Error in Panel C: {e}")

    return True

if __name__ == "__main__":
    create_table5()
