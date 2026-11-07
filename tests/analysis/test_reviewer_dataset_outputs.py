"""Regression tests for reviewer-requested dataset and metric outputs."""

import sys
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
sys.path.insert(0, str(REPO / "scripts" / "figures"))

from mapper import load_data  # noqa: E402
from review_metrics import _hardware_awareness, build_analysis, sha256_file, write_analysis_outputs  # noqa: E402


TR_EVIDENCE_PATH = REPO / "data" / "tr_criteria_evidence.csv"
FIELD_EVIDENCE_PATH = REPO / "data" / "field_characterization_evidence.csv"
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

    assert len(evidence) == 45
    assert evidence["Paper_ID"].nunique() == 45
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

    assert len(table) == 45
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


def test_verified_field_evidence_is_complete_and_canonical():
    """The public field-evidence layer must map one-to-one to the canonical corpus."""
    evidence = pd.read_csv(FIELD_EVIDENCE_PATH)
    canonical = pd.read_csv(REPO / "data" / "included_study_order.csv")

    assert len(evidence) == 45
    assert evidence["Paper_ID"].tolist() == list(range(1, 46))
    assert evidence["Title"].tolist() == canonical["Title"].tolist()
    assert evidence["DOI"].str.casefold().tolist() == canonical["DOI"].str.casefold().tolist()
    assert evidence["Target_Field_Status"].value_counts().to_dict() == {
        "Explicitly reported": 20,
        "Not applicable": 14,
        "Not reported": 6,
        "Not available": 5,
    }
    assert "Evidence_Summary" in evidence.columns
    assert "Evidence_Quote" not in evidence.columns
    assert evidence["Evidence_Summary"].fillna("").str.split().str.len().max() <= 25
    assert not any(
        token in column.casefold()
        for column in evidence.columns
        for token in ("ai_", "_ai", "auto_", "provisional", "human", "manual")
    )


def test_dataset_characterization_uses_verified_target_field_evidence():
    """Verified full-text target fields must replace the 44 heuristic Unknown values."""
    table = build_analysis(load_data())["dataset_characterization"]

    assert table["Target_Field_Status"].value_counts().to_dict() == {
        "Explicitly reported": 20,
        "Not applicable": 14,
        "Not reported": 6,
        "Not available": 5,
    }
    assert "Unknown" not in set(table["Target_Field_Category"])
    assert table["Target_Field_Status"].value_counts().to_dict() == {
        "Explicitly reported": 20,
        "Not applicable": 14,
        "Not reported": 6,
        "Not available": 5,
    }


def test_analysis_manifest_pins_the_field_evidence_input(tmp_path):
    """A regenerated analysis must record the field-evidence file it consumed."""
    source = REPO / "data" / "data-clean.csv"
    manifest = write_analysis_outputs(build_analysis(load_data()), tmp_path, source)

    assert manifest["field_evidence"] == {
        "logical_path": "data/field_characterization_evidence.csv",
        "sha256": sha256_file(FIELD_EVIDENCE_PATH),
        "rows": 45,
    }


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

    assert len(table) == 45
    assert table["Paper_ID"].nunique() == 45
    canonical = pd.read_csv(REPO / "data" / "included_study_order.csv")
    assert table["DOI"].str.casefold().tolist() == canonical["DOI"].str.casefold().tolist()
    assert set(table["PSNR_SSIM_Comparison_Eligibility"]).issubset(
        {"Eligible", "Not eligible", "Not reported"}
    )
    metric_rows = table[table["PSNR_or_SSIM_Reported"] == "Yes"]
    assert (metric_rows["PSNR_SSIM_Comparison_Eligibility"] != "Eligible").any()


def test_unclear_field_pathway_cannot_make_psnr_ssim_comparison_eligible():
    """An unresolved field direction is not evidence for a comparable metric pair."""
    table = build_analysis(load_data())["metric_suitability"]
    unresolved = table[
        table["Field_Pathway"].isin(
            {"Unclear", "Not reported", "Not available", "Not applicable"}
        )
    ]

    assert not unresolved["PSNR_SSIM_Comparison_Eligibility"].eq("Eligible").any()


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
    row = load_data().loc[
        load_data()["Title"].eq("Deep learning for fast low-field MRI acquisitions")
    ].iloc[0]

    result = _hardware_awareness(row)

    assert result["TR_HardwareAwareness"] == 0
    assert result["TR_HardwareAwareness_Status"] == "No"
    assert "training hardware" in result["TR_HardwareAwareness_Reason"]


def test_deployment_pathway_without_inference_hardware_is_not_enough():
    row = load_data().loc[
        load_data()["Title"].eq("ShuffleUNet: Super resolution of diffusion-weighted MRIs using deep learning")
    ].iloc[0]

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

    assert len(table) == 45
    assert table["Paper_ID"].nunique() == 45
    assert required.issubset(table.columns)
    assert table["Decision"].eq("No").all()
    assert table["TR_HardwareAwareness"].eq(0).all()
    assert table["Evidence_Page"].fillna("").str.strip().ne("").all()
    assert table["Evidence_Section"].ne("").all()
    assert not any("human" in column.casefold() or "pending" in column.casefold() for column in table.columns)
