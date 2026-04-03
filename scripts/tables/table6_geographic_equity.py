"""
Table 6: Geographic & Economic Equity

Generates panels for:
  A: Income group distribution (World Bank)
  B: LMIC score by application area (Proxy for regional mapping)
  C: Research Gap analysis (HIC vs Global South)
"""

import sys
import os
from pathlib import Path

# Add project root and scripts/figures to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "figures"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "data_enrichment" / "world_bank"))

import pandas as pd
import numpy as np
from mapper import load_data, get_project_root
from world_bank_mapper import get_equity_classification

# Reproducibilidad
np.random.seed(42)

def create_table6():
    """Generates Table 6 with geographic equity metrics."""
    
    print("\n=== Table 6: Geographic & Economic Equity ===\n")
    
    # Cargar datos
    df = load_data()
    
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- PANEL A: INCOME GROUP DISTRIBUTION ---
    print("Panel A: Socioeconomic Classification Baseline")
    try:
        # We load the enriched author data if available, otherwise use study types
        author_path = out_dir / "Author_Equity_Analysis.csv"
        
        if os.path.exists(author_path):
            author_df = pd.read_csv(author_path)
            income_dist = author_df['WorldBank_Group'].value_counts(normalize=True).round(4) * 100
            print(f"Author Income Distribution (%):\n{income_dist}")
            
            income_dist_df = income_dist.reset_index()
            income_dist_df.columns = ['Income_Group', 'Percentage']
            income_dist_df.to_csv(out_dir / "table6a_income_distribution.csv", index=False)
            print(f"✓ Saved: table6a_income_distribution.csv\n")
        else:
            print("⚠ Author_Equity_Analysis.csv missing. Run world_bank_fetcher stand-alone first.")
            print("  Falling back to Study Classification...\n")

    except Exception as e:
        print(f"⚠ Error in Panel A: {e}")

    # --- PANEL B: LMIC SCORE BY APPLICATION ---
    print("Panel B: LMIC Score by Application (Functional Mapping)")
    try:
        # Grouping by normalized application to see where the highest relevance lies
        lmic_by_app = df.groupby("Application_Norm")["LMIC_Score"].agg([
            "count", "mean", "median", "std"
        ]).round(2)
        
        print(lmic_by_app)
        lmic_by_app.to_csv(out_dir / "table6b_lmic_by_application.csv")
        print(f"✓ Saved: table6b_lmic_by_application.csv\n")
        
    except Exception as e:
        print(f"⚠ Error in Panel B: {e}")

    # --- PANEL C: RESEARCH GAPS ---
    print("Panel C: Equity Metrics (HIC vs Global South)")
    try:
        # High LMIC Relevance papers (Score 4-5) distribution
        high_rel = df[df['LMIC_Score'] >= 4]
        gap_analysis = {
            'Metric': ['Total_High_Relevance', 'Median_Year', 'Standard_Field_%', 'Low_Field_%'],
            'Value': [
                len(high_rel),
                high_rel['Year'].median(),
                (high_rel['Field_Strength_Type'].str.lower().str.contains('standard|high').fillna(False).mean() * 100).round(1),
                (high_rel['Field_Strength_Type'].str.lower().str.contains('low').fillna(False).mean() * 100).round(1)
            ]
        }
        
        gap_df = pd.DataFrame(gap_analysis)
        print(gap_df.to_string(index=False))
        gap_df.to_csv(out_dir / "table6c_research_gaps.csv", index=False)
        print(f"✓ Saved: table6c_research_gaps.csv\n")
        
    except Exception as e:
        print(f"⚠ Error in Panel C: {e}")

    return True

if __name__ == "__main__":
    create_table6()
