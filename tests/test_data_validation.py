"""
Data validation tests for MRI-LMICs survey.
"""

import sys
from pathlib import Path

import pytest

# Allow imports from scripts/figures
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "figures"))

from mapper import load_data, get_project_root


def test_csv_exists():
    csv_path = get_project_root() / "data" / "mri_sr_extraction.csv"
    assert csv_path.exists(), f"Data file not found: {csv_path}"


def test_data_has_56_papers():
    df = load_data()
    assert len(df) == 51, f"Expected 51 papers, got {len(df)}"


def test_required_columns():
    df = load_data()
    required = [
        "Paper_ID", "Title", "Year", "MRI_Application_Area",
        "Field_Strength_Type", "AI_Architecture", "Primary_Focus",
        "PSNR_Value", "SSIM_Value", "LMIC_Relevance_Score",
        "Low_Field_Mentioned", "Code_Available",
    ]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


def test_normalized_columns_created():
    df = load_data()
    norm_cols = [
        "Application_Norm", "Field_Strength_Norm", "Primary_Focus_Norm",
        "Architecture_Norm", "LMIC_Score", "Low_Field_Norm",
        "Code_Available_Norm", "Clinical_Validation_Norm",
        "PSNR_Numeric", "SSIM_Numeric",
    ]
    missing = [c for c in norm_cols if c not in df.columns]
    assert not missing, f"Missing normalized columns: {missing}"


def test_lmic_scores_in_range():
    df = load_data()
    scores = df["LMIC_Score"].dropna()
    assert len(scores) > 0, "No LMIC scores found"
    assert scores.min() >= 1, f"LMIC score below 1: {scores.min()}"
    assert scores.max() <= 5, f"LMIC score above 5: {scores.max()}"


def test_ssim_in_valid_range():
    df = load_data()
    ssim = df["SSIM_Numeric"].dropna()
    assert (ssim >= 0).all(), "SSIM values below 0 found"
    assert (ssim <= 1).all(), f"SSIM values above 1 found: {ssim[ssim > 1].tolist()}"


def test_year_range():
    df = load_data()
    years = df["Year"].dropna()
    assert years.min() >= 2019, f"Year too early: {years.min()}"
    assert years.max() <= 2026, f"Year too late: {years.max()}"


def test_all_extractions_complete():
    df = load_data()
    incomplete = df[~df["Extraction_Complete"].str.lower().str.strip().isin(["yes"])]
    assert len(incomplete) == 0, f"{len(incomplete)} papers not marked complete"
