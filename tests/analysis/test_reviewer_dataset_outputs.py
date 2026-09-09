"""Regression tests for reviewer-requested dataset and metric outputs."""

import sys
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
sys.path.insert(0, str(REPO / "scripts" / "figures"))

from mapper import load_data  # noqa: E402
from review_metrics import _hardware_awareness, build_analysis  # noqa: E402


TR_EVIDENCE_PATH = REPO / "data" / "tr_criteria_evidence.csv"
TR_CRITERIA = [
    "LowFieldDomain",
    "OpenScience",
    "ClinicalEvaluation",
    "HardwareAwareness",
    "DataDiversity",
]


def test_verified_tr_evidence_is_complete_and_binary():
    """The frozen full-text evidence layer must contain final decisions, not a review queue."""
    evidence = pd.read_csv(TR_EVIDENCE_PATH)

    assert len(evidence) == 48
    assert evidence["Paper_ID"].nunique() == 48
    assert evidence["DOI"].str.strip().ne("").all()
    assert not any("human" in column.casefold() or "provisional" in column.casefold() for column in evidence.columns)
    for criterion in TR_CRITERIA:
        decision = f"TR_{criterion}_Decision"
        binary = f"TR_{criterion}"
        reason = f"TR_{criterion}_Reason"
        assert set(evidence[decision]) <= {"Yes", "No"}
        assert set(evidence[binary]) <= {0, 1}
        assert evidence[reason].fillna("").str.strip().ne("").all()
        assert evidence[decision].eq(evidence[binary].map({1: "Yes", 0: "No"})).all()
    assert evidence["TR_Score"].eq(evidence[[f"TR_{c}" for c in TR_CRITERIA]].sum(axis=1)).all()


def test_analysis_uses_the_frozen_tr_evidence_layer():
    evidence = pd.read_csv(TR_EVIDENCE_PATH).sort_values("Paper_ID").reset_index(drop=True)
    tr = build_analysis(load_data())["tr"].sort_values("Paper_ID").reset_index(drop=True)

    assert "TR_Manual_Review" not in tr.columns
    for criterion in TR_CRITERIA:
        column = f"TR_{criterion}"
        assert tr[column].tolist() == evidence[column].tolist()
    assert tr["TR_Score"].tolist() == evidence["TR_Score"].tolist()


def test_dataset_characterization_has_reviewer_required_columns():
    """The derived table must expose reviewer-requested fields without editing source data."""
    table = build_analysis(load_data())['dataset_characterization']

    assert len(table) == 48
    assert {
        "Input_Resolution",
        "Target_Resolution",
        "Dataset_Public_Availability",
        "Resolution_Evidence",
        "Dataset_Availability_Evidence",
    }.issubset(table.columns)
    assert not table["Input_Resolution"].isna().any()
    assert not table["Target_Resolution"].isna().any()
    assert not table["Dataset_Public_Availability"].isna().any()
    assert "Field_Manual_Review" not in table.columns
    assert not any(
        token in column.casefold()
        for column in table.columns
        for token in ("ai_", "_ai", "auto_", "provisional", "human", "manual")
    )


def test_public_review_outputs_use_neutral_source_labels():
    """Public outputs describe source evidence, not the extraction process."""
    for frame_name in ("tr", "field_ground_truth", "dataset_characterization"):
        frame = build_analysis(load_data())[frame_name]
        assert not any(
            token in column.casefold()
            for column in frame.columns
            for token in ("ai_evidence", "auto_", "provisional", "human", "manual")
        )


def test_metric_suitability_has_one_conservative_row_per_included_study():
    """Metric eligibility must never infer paired ground truth from PSNR/SSIM alone."""
    table = build_analysis(load_data())['metric_suitability']

    assert len(table) == 48
    assert table["Paper_ID"].nunique() == 48
    assert set(table["PSNR_SSIM_Comparison_Eligibility"]).issubset(
        {"Eligible", "Not eligible", "Not reported"}
    )
    metric_rows = table[table["PSNR_or_SSIM_Reported"] == "Yes"]
    assert (metric_rows["PSNR_SSIM_Comparison_Eligibility"] != "Eligible").any()


def test_training_hardware_does_not_satisfy_inference_hardware_awareness():
    row = pd.Series(
        {
            "Architecture_Specifics": "trained on a NVIDIA V100 GPU",
            "Performance_Summary": "training required 12 hours",
            "Clinical_Results": "",
            "Notes_Questions": "",
            "Limitations_Mentioned": "",
            "Main_Finding_1": "",
            "Main_Finding_2": "",
            "Main_Finding_3": "",
        }
    )

    result = _hardware_awareness(row)

    assert result["TR_HardwareAwareness"] == 0
    assert result["TR_HardwareAwareness_Status"] == "No"
    assert "training hardware" in result["TR_HardwareAwareness_Reason"]


def test_explicit_inference_requirement_satisfies_hardware_awareness():
    row = pd.Series(
        {
            "Architecture_Specifics": "",
            "Performance_Summary": "Minimum inference requirement: 8 GB RAM and an NVIDIA GPU.",
            "Clinical_Results": "",
            "Notes_Questions": "",
            "Limitations_Mentioned": "",
            "Main_Finding_1": "",
            "Main_Finding_2": "",
            "Main_Finding_3": "",
        }
    )

    result = _hardware_awareness(row)

    assert result["TR_HardwareAwareness"] == 1
    assert result["TR_HardwareAwareness_Status"] == "Yes"
    assert result["TR_HardwareAwareness_Evidence"]


def test_resource_constrained_training_gpu_is_not_inference_hardware():
    row = load_data().query("Paper_ID == 38").iloc[0]

    result = _hardware_awareness(row)

    assert result["TR_HardwareAwareness"] == 0
    assert result["TR_HardwareAwareness_Status"] == "No"
    assert "training hardware" in result["TR_HardwareAwareness_Reason"]


def test_deployment_pathway_without_inference_hardware_is_not_enough():
    row = load_data().query("Paper_ID == 31").iloc[0]

    result = _hardware_awareness(row)

    assert result["TR_HardwareAwareness"] == 0
    assert result["TR_HardwareAwareness_Status"] == "No"
    assert "training hardware" in result["TR_HardwareAwareness_Reason"]


def test_hardware_decisions_follow_the_official_minimum_inference_requirement():
    tr = build_analysis(load_data())["tr"]

    assert tr["TR_HardwareAwareness"].eq(0).all()
    assert tr["TR_HardwareAwareness_Decision"].eq("No").all()
    assert tr["TR_HardwareAwareness_Reason"].fillna("").str.strip().ne("").all()


def test_hardware_evidence_table_is_flat_final_and_has_no_review_queue():
    table = build_analysis(load_data())["hardware_verification"]
    required = {
        "Paper_ID",
        "DOI",
        "TR_HardwareAwareness",
        "Decision",
        "Evidence_Page",
        "Evidence_Section",
        "Evidence_Reason",
        "Evidence_Document",
        "Rubric_Version",
    }

    assert len(table) == 48
    assert table["Paper_ID"].nunique() == 48
    assert required.issubset(table.columns)
    assert table["Decision"].eq("No").all()
    assert table["TR_HardwareAwareness"].eq(0).all()
    assert table["Evidence_Page"].fillna("").str.strip().ne("").all()
    assert table["Evidence_Section"].ne("").all()
    assert not any("human" in column.casefold() or "pending" in column.casefold() for column in table.columns)
