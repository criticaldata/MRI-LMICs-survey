"""Regression tests for the September 2026 cross-document corrections."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
sys.path.insert(0, str(REPO / "scripts" / "analysis" / "statistical"))
sys.path.insert(0, str(REPO / "scripts" / "figures"))
sys.path.insert(0, str(REPO / "scripts" / "tables"))

from mapper import load_data, normalize_field_strength as normalize_figure_field  # noqa: E402
from review_metrics import (  # noqa: E402
    build_analysis,
    normalize_field_category as normalize_review_field,
    normalize_primary_focus,
)
from mann_whitney_tests import load_and_prepare, run_mann_whitney  # noqa: E402
from table_merged_performance_lmic import create_merged_table  # noqa: E402
from analysis_dataset_diversity import analyze_dataset_diversity  # noqa: E402
from analysis_cross_field_generalization import classify_field_category  # noqa: E402
from utils import normalize_field_strength as normalize_statistical_field  # noqa: E402
from scripts.field_taxonomy import has_reported_low_field_strength  # noqa: E402
from table1_study_characteristics import create_table1  # noqa: E402
from table6_geographic_equity import create_table6  # noqa: E402
import fig1_year_distribution as fig1_year_distribution  # noqa: E402


DATASET_EVIDENCE = REPO / "data" / "dataset_characterization_evidence.csv"


def test_dataset_evidence_is_canonical_neutral_and_complete():
    evidence = pd.read_csv(DATASET_EVIDENCE)
    canonical = pd.read_csv(REPO / "data" / "included_study_order.csv")

    assert evidence["Paper_ID"].tolist() == list(range(1, 46))
    assert evidence["Title"].tolist() == canonical["Title"].tolist()
    assert evidence["DOI"].str.casefold().tolist() == canonical["DOI"].str.casefold().tolist()
    assert not any(
        token in column.casefold()
        for column in evidence.columns
        for token in ("ai_", "_ai", "provisional", "human", "manual")
    )
    assert evidence["Dataset_Evidence_Status"].fillna("").str.strip().ne("").all()


def test_dataset_characterization_uses_full_text_evidence_not_keyword_inference():
    table = build_analysis(load_data())["dataset_characterization"]

    assert table["Dataset_Real_Simulated"].value_counts().to_dict() == {
        "Mixed": 16,
        "Real": 17,
        "Not available": 5,
        "Not reported": 4,
        "Synthetic/derived": 2,
        "Unclear": 1,
    }
    assert table["Dataset_Public_Availability"].value_counts().to_dict() == {
        "Public": 13,
        "Private": 9,
        "Not reported": 9,
        "Not available": 7,
        "Mixed": 6,
        "Unclear": 1,
    }
    assert table["Paired_Unpaired"].value_counts().to_dict() == {
        "Paired by construction": 22,
        "Not applicable": 14,
        "Paired": 5,
        "Not reported": 1,
        "Unclear": 1,
        "Not available": 1,
        "Mixed": 1,
    }


def test_dataset_diversity_table_uses_verified_real_simulated_labels():
    result = analyze_dataset_diversity()
    actual = result.loc[
        result["Section"].eq("Dataset Type Counts") & result["Column"].eq("Count")
    ].set_index("Row")["Value"].astype(int).to_dict()
    evidence = pd.read_csv(DATASET_EVIDENCE)
    expected = evidence["Dataset_Real_Simulated"].value_counts().to_dict()

    assert actual == expected


def test_psnr_reporting_test_uses_parseable_values(tmp_path):
    log_path = tmp_path / "stats.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        prepared = load_and_prepare(log_file)
        result = run_mann_whitney(prepared, log_file)

    row = result.loc[result["Variable"].eq("LMIC_Relevance_Score")].iloc[0]
    assert int(row["Group_A_n"]) == 18
    assert int(row["Group_B_n"]) == 27
    assert float(row["U_statistic"]) == pytest.approx(277.5)
    # SciPy's asymptotic-tail implementation can vary by sub-micro precision
    # across supported versions; the inferential result is unchanged.
    assert float(row["p_value"]) == pytest.approx(0.407294, abs=1e-6)
    assert int(prepared["Reports_SSIM"].sum()) == 17
    assert int(prepared["Reports_Any_Metric"].sum()) == 19


def test_main_performance_table_preserves_half_step_lmic_medians():
    table = create_merged_table()
    gan = table.loc[table["Architecture"].eq("GAN")].iloc[0]
    cnn = table.loc[table["Architecture"].eq("CNN")].iloc[0]

    assert gan["LMIC Score median"] == "3.0"
    assert str(cnn["SSIM, median (range)"]).startswith("0.916")


def test_random_forest_public_summary_matches_current_45_study_run():
    summary = pd.read_csv(REPO / "tables" / "analysis_random_forest_robustness_summary.csv")
    forest = summary.loc[summary["Model"].eq("Constrained Random Forest")].iloc[0]

    assert int(forest["N_Studies"]) == 45
    assert int(forest["Resampling_Splits"]) == 50
    assert int(forest["Seed"]) == 42
    assert float(forest["MAE_Mean"]) == pytest.approx(0.678696, abs=1e-6)
    assert float(forest["R2_Mean"]) == pytest.approx(0.031143, abs=1e-6)
    assert int(forest["Positive_MAE_Improvement_Splits"]) == 44


def test_geographic_income_table_uses_multisource_affiliation_resolution():
    create_table6()
    income = pd.read_csv(REPO / "tables" / "table6a_income_distribution.csv")
    actual = income.set_index("First_Author_WB_Group")["Studies"].astype(int).to_dict()
    scientometric = pd.read_csv(REPO / "tables" / "mri_scientometric_results.csv")

    assert scientometric["Suggested_First_Country"].fillna("").str.strip().ne("").all()
    assert actual == {"HIC": 25, "UMC": 10, "LMC": 7, "Not available": 3}


def test_canonical_figure_sources_replace_misnumbered_legacy_names():
    expected = {
        "fig1_year_distribution.py",
        "fig2_architecture_distribution.py",
        "fig3_performance_comparison.py",
        "fig4_lmic_translational_gap.py",
        "fig5_field_strength_application.py",
        "fig6_translational_roadmap.py",
        "figS1_temporal_trends.py",
        "figS2_prisma_flow.py",
        "figS3_reviewer_score_distributions.py",
    }
    actual = {path.name for path in (REPO / "scripts" / "figures").glob("fig*.py")}

    assert expected <= actual
    assert "fig3_lmic_relevance.py" not in actual
    assert "fig4_performance_comparison.py" not in actual
    assert "fig1_prisma_flow.py" not in actual


@pytest.mark.parametrize(
    ("raw_focus", "expected"),
    [
        ("Assessing generalization and applying Transfer Learning", "Other"),
        ("Reconstruction of undersampled MRI (accelerated acquisition)", "Other"),
        ("denoising and distortion correction in low-field MRI", "Other"),
        ("Denoising+SR", "SR + Denoising"),
        ("SR + acceleration", "SR + Other"),
        ("Pure_SR", "Pure SR"),
    ],
)
def test_primary_sr_scope_requires_explicit_sr_evidence(raw_focus, expected):
    assert normalize_primary_focus(raw_focus) == expected


def test_primary_sr_sensitivity_cohorts_exclude_non_sr_tasks():
    outputs = build_analysis(load_data())
    sensitivity = outputs["sensitivity"]

    assert sensitivity["N"].tolist() == [45, 24, 22]
    assert outputs["correlation"]["n"].tolist() == [45, 24, 22]


def test_table1_primary_focus_matches_the_evidence_based_sr_scope():
    table = create_table1()
    focus_header = table.index[table["Characteristic"].eq("Primary Focus")][0]
    focus_end = next(
        index
        for index in table.index
        if index > focus_header and table.loc[index, "Characteristic"] == ""
    )
    focus_rows = table.loc[focus_header + 1 : focus_end - 1]

    assert {
        row["Characteristic"].strip(): int(row["n"])
        for _, row in focus_rows.iterrows()
    } == {
        "Pure SR": 16,
        "SR + Denoising": 6,
        "SR + Classification": 6,
        "Other": 7,
        "SR + Segmentation": 4,
        "SR + Diagnosis": 4,
        "SR + Other": 2,
    }


def test_figure1_primary_focus_counts_match_final_corpus(monkeypatch):
    monkeypatch.setattr(fig1_year_distribution, "save_figure", lambda *_args: None)
    figure = fig1_year_distribution.create_fig1()
    legend_labels = [
        text.get_text() for text in figure.axes[0].get_legend().get_texts()
    ]
    actual_counts = {
        label: int(sum(patch.get_width() for patch in container.patches))
        for label, container in zip(legend_labels, figure.axes[0].containers)
    }

    assert actual_counts == {
        "Pure SR": 16,
        "SR + Denoising": 6,
        "SR + Classification": 6,
        "Other": 7,
        "SR + Segmentation": 4,
        "SR + Diagnosis": 4,
        "SR + Other": 2,
    }


@pytest.mark.parametrize(
    ("raw_field", "expected"),
    [
        ("0.049 T", "Ultra-low-field (<0.05 T)"),
        ("50 mT", "Low-field (0.05-0.5 T)"),
        ("0.5 T", "Low-field (0.05-0.5 T)"),
        ("0.6 T", "Intermediate-field (>0.5-<1.5 T)"),
        ("1.5 T", "Standard-field (1.5-3 T)"),
        ("3 T", "Standard-field (1.5-3 T)"),
        ("3.1 T", "High-field (>3 T)"),
        ("Low-field", "Low-field (threshold unspecified)"),
        ("Standard-field", "Standard-field (strength unspecified)"),
        ("High-field", "High-field (threshold unspecified)"),
        ("Low-field (0.4 T) + high-field reference (3 T)", "Mixed"),
        ("1.5 T and 3 T MRI scanners", "Standard-field (1.5-3 T)"),
        ("Mixed", "Mixed"),
        ("Not_specified", "Not specified"),
        ("Not reported", "Not reported"),
    ],
)
def test_field_taxonomy_uses_reported_tesla_ranges_and_preserves_uncertainty(
    raw_field, expected
):
    assert normalize_review_field(raw_field) == expected
    assert normalize_figure_field(raw_field) == expected
    assert normalize_statistical_field(raw_field) == expected


@pytest.mark.parametrize(
    ("raw_field", "expected"),
    [
        ("Low-field", "Single field strength"),
        ("0.4 T plus 3 T reference", "True cross-field"),
        ("1.5 and 3 T MRI", "Multi-scanner standard"),
        ("3 T MRI", "Single field strength"),
    ],
)
def test_cross_field_analysis_requires_explicit_numeric_strengths(raw_field, expected):
    row = pd.Series({"Field_Strength_Type": raw_field})
    assert classify_field_category(row) == expected


def test_numeric_low_field_feature_does_not_treat_generic_mentions_as_measurements():
    assert has_reported_low_field_strength("Low-field") is False
    assert has_reported_low_field_strength("0.1 T low-field MRI") is True
    assert has_reported_low_field_strength("0.4 T plus 3 T reference") is True
