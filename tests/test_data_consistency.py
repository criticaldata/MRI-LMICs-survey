import pytest
import pandas as pd
from unittest.mock import MagicMock
from scripts.figures.mapper import load_data
from scripts.analysis.statistical.random_forest_training import load_and_filter_data
from scripts.analysis.statistical.mann_whitney_tests import load_and_prepare

def test_mapper_and_rf_data_consistency():
    """
    Validates that the central mapper dataset and the Random Forest filtered dataset
    yield the same effective sample size (N) for LMIC Relevance Score analysis.
    This prevents 'Issue C3' (data pipeline divergence) by enforcing consistency.
    """
    # 1. Load data via mapper (used by tables/orchestrator)
    df_mapper = load_data()
    # The mapper logic expects dropping NA values to get the effective size for ML
    mapper_n = len(df_mapper.dropna(subset=['LMIC_Relevance_Score']))
    
    # 2. Load data via RF module independent loader
    mock_log = MagicMock() # Mock the log_file object required by the function
    df_rf = load_and_filter_data(mock_log)
    rf_n = len(df_rf)

    # 3. Load data via Mann-Whitney module independent loader
    df_mw = load_and_prepare(mock_log)
    mw_n = len(df_mw.dropna(subset=['LMIC_Relevance_Score']))
    
    # Assert they are identical
    assert mapper_n == rf_n, f"Pipeline divergence! Mapper yields N={mapper_n}, RF yields N={rf_n}"
    assert mapper_n == mw_n, f"Pipeline divergence! Mapper yields N={mapper_n}, Mann-Whitney yields N={mw_n}"
    
    # Double check that LMIC_Relevance_Score is properly numeric in both to prevent ValueError
    assert pd.api.types.is_numeric_dtype(df_mapper['LMIC_Relevance_Score']), "Mapper failed to coerce LMIC score to numeric"
    assert pd.api.types.is_numeric_dtype(df_rf['LMIC_Relevance_Score']), "RF module failed to cast LMIC score to numeric"
    assert pd.api.types.is_numeric_dtype(df_mw['LMIC_Relevance_Score']), "Mann-Whitney module failed to cast LMIC score to numeric"
