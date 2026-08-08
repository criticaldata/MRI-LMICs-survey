"""Reproducible review metrics for the MRI-LMICs survey.

The functions in this module are intentionally conservative.  They keep the
source text alongside every derived flag, use the five translational-readiness
criteria defined in the revised manuscript, and expose unresolved values
instead of converting them to affirmative evidence.

This module does not calculate Fleiss' kappa.  The existing provisional
10-paper/2-reviewer calculation is kept separate until independent ratings
from all 11 reviewers are available.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGURES_DIR = PROJECT_ROOT / "scripts" / "figures"
if str(FIGURES_DIR) not in sys.path:
    sys.path.insert(0, str(FIGURES_DIR))

from mapper import load_data  # noqa: E402


TEXT_FIELDS = [
    "Title",
    "Field_Strength_Type",
    "Primary_Focus",
    "Training_Data_Source",
    "Dataset_Type",
    "Dataset_Size",
    "Performance_Summary",
    "Clinical_Validation_Type",
    "Clinical_Results",
    "Low_Field_Mentioned",
    "Resource_Constraints_Addressed",
    "Notes_Questions",
    "Limitations_Mentioned",
    "Main_Finding_1",
    "Main_Finding_2",
    "Main_Finding_3",
    "Architecture_Specifics",
]


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).replace("\u00a0", " ").split())


def _lower(value: object) -> str:
    return _text(value).casefold()


def row_text(row: pd.Series, fields: Iterable[str] = TEXT_FIELDS) -> str:
    return " | ".join(value for value in (_text(row.get(field)) for field in fields) if value)


def _has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _first_evidence(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 120)
            return text[start:end]
    return ""


def normalize_field_category(value: object) -> str:
    """Apply one aggregate field-strength taxonomy to the raw field label."""
    text = _lower(value)
    if not text or text in {"not reported", "not_specified", "nan"}:
        return "Not specified"
    if text == "mixed":
        return "Mixed"
    has_low = bool(re.search(r"low[ -]?field|ultra[ -]?low|\b\d+\s*m?t\b|\b0\.\d+\s*t\b", text))
    has_standard = bool(re.search(r"standard|1\.5\s*t|3\s*t|high[ -]?field", text))
    if has_low and has_standard:
        return "Mixed"
    if has_low:
        return "Low-field"
    if "high-field" in text or re.search(r"\b7\s*t\b|\b9\.4\s*t\b", text):
        return "High-field"
    if has_standard:
        return "Standard-field"
    return "Unknown"


def normalize_primary_focus(value: object) -> str:
    text = _lower(value)
    if not text:
        return "Unknown"
    if text in {"pure_sr", "pure sr"}:
        return "Pure SR"
    if "review" in text or "survey" in text:
        return "Review/Survey"
    if "segmentation" in text and "classification" in text and "sr" not in text and "super-resolution" not in text:
        return "Other"
    if "segmentation" in text and "super-resolution" not in text and "sr" not in text:
        return "Other"
    if "denois" in text and ("sr" in text or "super-resolution" in text or "low" in text and "field" in text):
        return "SR + Denoising"
    if "classification" in text or "classif" in text:
        return "SR + Classification"
    if "diagnos" in text:
        return "SR + Diagnosis"
    if "segment" in text:
        return "SR + Segmentation"
    if "super-resolution" in text or "super resolution" in text or re.search(r"\bsr\b", text):
        return "Pure SR" if text in {"pure_sr", "pure sr"} else "SR + Other"
    if "high resolution" in text and "low resolution" in text:
        return "Pure SR"
    if "transfer learning" in text or "reconstruction" in text:
        return "SR + Other"
    return "Unknown"


def normalize_dataset_category(value: object) -> str:
    text = _lower(value)
    if not text or text in {"not reported", "nan"}:
        return "Not reported"
    if "mixed" in text or "clinical and public" in text or "cardiac, brain" in text or "human brain and cardiac" in text:
        return "Mixed"
    if "synthetic" in text or "simulat" in text:
        if "clinical" in text or "patient" in text or "in-vivo" in text:
            return "Mixed"
        return "Synthetic"
    if "clinical" in text or "patient" in text or "volunteer" in text or "prospective" in text or "community sample" in text:
        return "Clinical"
    if "public" in text or "benchmark" in text or "repository of images" in text or "prostatex" in text:
        return "Public benchmark"
    if "private" in text or "proprietary" in text:
        return "Private"
    return "Unknown"


def normalize_architecture(value: object) -> str:
    text = _lower(value)
    if not text:
        return "Unknown"
    if "diffusion" in text:
        return "Diffusion"
    if "hybrid" in text:
        return "Hybrid"
    if "transformer" in text or "swin" in text:
        return "Transformer"
    if "gan" in text:
        return "GAN"
    if "u-net" in text or "unet" in text:
        return "U-Net"
    if "fourier" in text or "non-ai" in text:
        return "Non-AI"
    if "cnn" in text or "convolution" in text or "dense" in text:
        return "CNN"
    return "Unknown"


def _threshold_low_field(text: str) -> bool:
    return _has(
        text,
        r"(?:≤|<=|less than or equal to)\s*64[- ]?\s*m?t|\b64[- ]?\s*m?t\b|0\.064[- ]?\s*t|0,064[- ]?\s*t|\b50[- ]?\s*m?t\b|0\.05[- ]?\s*t",
    )


def _low_field_any(text: str) -> bool:
    return _has(text, r"low[ -]?field|ultra[ -]?low|\b0\.1\s*t\b|\b0\.35\s*t\b|\b0\.4\s*t\b")


def _field_pair(row: pd.Series) -> dict[str, str]:
    field = _lower(row.get("Field_Strength_Type"))
    training = _lower(row.get("Training_Data_Source"))
    notes = _lower(row.get("Notes_Questions"))
    title = _lower(row.get("Title"))
    field_text = " | ".join(value for value in [field, training, notes, title] if value)
    low64 = _threshold_low_field(field_text)
    low_any = _low_field_any(field_text)
    standard = bool(re.search(r"standard|1\.5\s*t|3\s*t|high[ -]?field|7\s*t", field_text))

    input_category = "Unknown"
    if _threshold_low_field(training) and _has(training, r"train|fine[- ]?tun|paired|model"):
        input_category = "≤64 mT"
    elif _has(training, r"low[ -]?field") and not _threshold_low_field(training):
        input_category = "Low-field (threshold unresolved)"
    elif re.search(r"1\.5\s*t|3\s*t|high[ -]?field|standard", training):
        input_category = ">64 mT"
    elif _has(training, r"synthetic|simulat|downsampl") and standard:
        input_category = "Synthetic/derived (field unresolved)"

    target_category = "Unknown"
    if _threshold_low_field(notes) or _threshold_low_field(title):
        target_category = "≤64 mT"
    elif _has(field_text, r"0\.1\s*t|0\.35\s*t|0\.4\s*t"):
        target_category = ">64 mT low-field"
    elif _has(field_text, r"evaluation.*(?:3\s*t|high)|applied to.*(?:3\s*t|high)"):
        target_category = ">64 mT"

    pair_category = "Unknown"
    paired_low_high = low_any and standard
    if _has(field_text, r"high[ -]?field.{0,100}low[ -]?field|3\s*t.{0,100}0\.4\s*t"):
        pair_category = "standard/high-field→low-field"
    elif _has(field_text, r"low[ -]?field.{0,100}(?:high[ -]?field|3\s*t|1\.5\s*t|standard)"):
        pair_category = "low-field→standard/high-field"
    elif _has(field_text, r"paired.*64\s*m?t.*3\s*t|64\s*m?t.*paired.*3\s*t"):
        pair_category = "low-field↔standard/high-field (paired)"
    elif paired_low_high:
        pair_category = "low-field↔standard/high-field (direction unresolved)"
    elif low_any:
        pair_category = "low-field (direction unresolved)"
    elif standard:
        pair_category = "standard/high-field only"

    return {
        "Input_Field_Category": input_category,
        "Target_Field_Category": target_category,
        "Field_Pair_Category": pair_category,
        "Field_Manual_Review": "Yes" if "Unknown" in {input_category, target_category} or "unresolved" in pair_category else "No",
        "Field_Evidence": _first_evidence(
            field_text,
            [r"64\s*m?t", r"0\.064\s*t", r"50\s*m?t", r"low[ -]?field", r"3\s*t", r"1\.5\s*t"],
        ),
    }


def _ground_truth(row: pd.Series) -> dict[str, str]:
    text = row_text(row).casefold()
    if _has(text, r"unpaired"):
        return {"Ground_Truth_Type": "Unpaired real-world reference", "Paired_Unpaired": "Unpaired"}
    if _has(text, r"paired|matched|same subject|co-registered|co registered"):
        return {"Ground_Truth_Type": "Paired measured/reference", "Paired_Unpaired": "Paired"}
    if _has(text, r"synthetic|simulat|downsampl|bicubic|fsl under-sampl|xcat"):
        return {"Ground_Truth_Type": "Synthetic degradation/proxy", "Paired_Unpaired": "Paired by construction"}
    if _has(text, r"ground truth|fully[- ]sampled|reference image"):
        return {"Ground_Truth_Type": "Measured/reference stated", "Paired_Unpaired": "Not reported"}
    return {"Ground_Truth_Type": "Not reported", "Paired_Unpaired": "Not reported"}


def _dataset_real_simulated(row: pd.Series) -> str:
    text = row_text(row).casefold()
    synthetic = _has(text, r"synthetic|simulat|downsampl|bicubic|xcat|fsl under-sampl")
    real = _has(text, r"clinical|patient|volunteer|in-vivo|prospective|acquired|hospital")
    if synthetic and real:
        return "Mixed"
    if synthetic:
        return "Synthetic/derived"
    if real:
        return "Real"
    return "Not reported"


SEQUENCE_PATTERNS = [
    ("T1-weighted", r"\bt1(?:[- ]?weighted|w)\b"),
    ("T2-weighted", r"\bt2(?:[- ]?weighted|w)\b"),
    ("FLAIR", r"\bflair\b"),
    ("DWI/DTI", r"diffusion|\bdwi\b|\bdti\b"),
    ("Proton density", r"proton density|\bpd\b"),
    ("GRE", r"gradient echo|\bgre\b"),
    ("FSE", r"\bfse\b"),
    ("DCE", r"dynamic contrast|\bdce\b"),
    ("Cine", r"\bcine\b"),
    ("4D-flow", r"4d[- ]flow"),
    ("SWI", r"\bswi\b"),
]


def _sequence_summary(row: pd.Series) -> str:
    text = row_text(row).casefold()
    found = [label for label, pattern in SEQUENCE_PATTERNS if _has(text, pattern)]
    return "; ".join(found) if found else "Not reported"


def _contrast_summary(row: pd.Series) -> str:
    text = row_text(row).casefold()
    found = []
    if _has(text, r"contrast[- ]enhanced|dynamic contrast|\bdce\b"):
        found.append("Contrast-enhanced/DCE")
    if _has(text, r"fat[- ]suppressed|fat suppression"):
        found.append("Fat-suppressed")
    if _has(text, r"multi[- ]contrast|multicontrast|multi[- ]modal"):
        found.append("Multi-contrast")
    if _has(text, r"phase|velocity"):
        found.append("Phase/velocity")
    return "; ".join(dict.fromkeys(found)) if found else "Not reported"


def _dataset_resolution_and_availability(row: pd.Series) -> dict[str, str]:
    """Extract only explicit spatial-resolution pairs and public-access statements."""
    text = row_text(row)
    resolution_pair = re.search(
        r"(?P<input>\d+(?:\.\d+)?\s*(?:mm|µm|um))\s*(?:x|×|to|→|->)\s*(?P<target>\d+(?:\.\d+)?\s*(?:mm|µm|um))",
        text,
        flags=re.IGNORECASE,
    )
    if resolution_pair:
        input_resolution = _text(resolution_pair.group("input"))
        target_resolution = _text(resolution_pair.group("target"))
        resolution_evidence = _text(resolution_pair.group(0))
    else:
        input_resolution = "Not reported"
        target_resolution = "Not reported"
        resolution_evidence = "Not reported"

    availability_text = row_text(
        row,
        ["Dataset_Type", "Training_Data_Source", "Notes_Questions", "Limitations_Mentioned"],
    )
    availability_evidence = _first_evidence(
        availability_text,
        [
            r"publicly available",
            r"public (?:dataset|benchmark|repository)",
            r"open (?:dataset|repository|access)",
            r"not publicly available",
            r"private dataset",
            r"proprietary dataset",
            r"internal dataset",
        ],
    )
    if _has(availability_text, r"not publicly available|private dataset|proprietary dataset|internal dataset"):
        availability = "Not publicly available"
    elif row.get("Dataset_Type_Norm_Corrected") == "Public benchmark" or _has(
        availability_text,
        r"publicly available|public (?:dataset|benchmark|repository)|open (?:dataset|repository|access)",
    ):
        availability = "Publicly available"
    else:
        availability = "Not reported"

    return {
        "Input_Resolution": input_resolution,
        "Target_Resolution": target_resolution,
        "Resolution_Evidence": resolution_evidence,
        "Dataset_Public_Availability": availability,
        "Dataset_Availability_Evidence": availability_evidence or "Not reported",
    }


def _metric_suitability_table(derived: pd.DataFrame) -> pd.DataFrame:
    """Describe whether reported PSNR/SSIM values have explicit comparison context."""
    rows = []
    for _, row in derived.iterrows():
        psnr_reported = pd.notna(row.get("PSNR_Numeric"))
        ssim_reported = pd.notna(row.get("SSIM_Numeric"))
        metric_reported = psnr_reported or ssim_reported
        field_pathway = _text(row.get("Field_Pair_Category"))
        if not field_pathway or field_pathway == "Unknown" or "unresolved" in field_pathway.casefold():
            field_pathway = "Not reported"
        pairedness = _text(row.get("Paired_Unpaired")) or "Not reported"
        ground_truth = _text(row.get("Ground_Truth_Type")) or "Not reported"
        if not metric_reported:
            eligibility = "Not reported"
            reason = "Neither PSNR nor SSIM was reported."
        elif (
            pairedness in {"Paired", "Paired by construction"}
            and ground_truth != "Not reported"
            and field_pathway != "Not reported"
        ):
            eligibility = "Eligible"
            reason = "Reported metric has explicit paired/reference and field-pathway evidence."
        else:
            eligibility = "Not eligible"
            reason = "Reported metric lacks explicit paired/reference or field-pathway evidence."
        rows.append(
            {
                "Paper_ID": int(row["Paper_ID"]),
                "Title": _text(row["Title"]),
                "PSNR_Reported": "Yes" if psnr_reported else "No",
                "SSIM_Reported": "Yes" if ssim_reported else "No",
                "PSNR_or_SSIM_Reported": "Yes" if metric_reported else "No",
                "Paired_Unpaired": pairedness,
                "Ground_Truth_Type": ground_truth,
                "Field_Pathway": field_pathway,
                "PSNR_SSIM_Comparison_Eligibility": eligibility,
                "PSNR_SSIM_Eligibility_Reason": reason,
                "Field_Evidence": _text(row.get("Field_Evidence")) or "Not reported",
            }
        )
    return pd.DataFrame(rows)


def _low_field_domain(row: pd.Series) -> dict[str, object]:
    training = _lower(row.get("Training_Data_Source"))
    title = _lower(row.get("Title"))
    field = _lower(row.get("Field_Strength_Type"))
    all_text = row_text(row).casefold()
    evidence = _first_evidence(all_text, [r"64\s*m?t", r"0\.064\s*t", r"50\s*m?t", r"low[ -]?field", r"hyperfine"])
    strong = _threshold_low_field(training) and _has(training, r"train|fine[- ]?tun|paired|model")
    paired_explicit = _has(training, r"paired.{0,40}(?:64\s*m?t|0\.064\s*t)")
    positive_training_relation = _has(
        all_text,
        r"(?:low[ -]?field|64\s*m?t|0\.064\s*t).{0,120}(?:for training|training|fine[- ]?tun|paired)|(?:for training|training|fine[- ]?tun|paired).{0,120}(?:low[ -]?field|64\s*m?t|0\.064\s*t)",
    )
    explicit_high_field_training = _has(all_text, r"trained on high[ -]?field|training.*(?:1\.5\s*t|3\s*t|high[ -]?field)")
    strong_from_review = _threshold_low_field(title + " " + field + " " + all_text) and positive_training_relation
    proxy = _has(training + " " + title, r"hyperfine") and _has(field + " " + title, r"low[ -]?field|64\s*m?t")
    non_ai = _has(row.get("AI_Architecture"), r"non[- ]?ai|fourier")
    if non_ai:
        status = "No"
        reason = "study is explicitly non-AI; no model training/fine-tuning criterion applies"
    elif explicit_high_field_training and not strong:
        status = "No"
        reason = "source explicitly states high-field training rather than ≤64 mT training"
    elif strong or paired_explicit or strong_from_review:
        status = "Yes"
        reason = "explicit ≤64 mT training/fine-tuning or paired training evidence"
    elif proxy:
        status = "Unclear"
        reason = "≤64 mT proxy term present; training/fine-tuning relationship requires review"
    elif _threshold_low_field(training) or _threshold_low_field(title + " " + field):
        status = "Unclear"
        reason = "≤64 mT appears in the source description but the training role is not explicit"
    elif _low_field_any(training + " " + field + " " + title):
        status = "No"
        reason = "low-field is mentioned, but ≤64 mT training evidence is absent"
    else:
        status = "No"
        reason = "no explicit ≤64 mT training/fine-tuning evidence"
    return {
        "TR_LowFieldDomain": int(status == "Yes"),
        "TR_LowFieldDomain_Status": status,
        "TR_LowFieldDomain_Evidence": evidence,
        "TR_LowFieldDomain_Reason": reason,
    }


def _clinical_evaluation(row: pd.Series) -> dict[str, object]:
    validation = _lower(row.get("Clinical_Validation_Type"))
    clinical_results = _lower(row.get("Clinical_Results"))
    text = validation + " " + clinical_results
    positive = _has(text, r"radiologist|neurologist|multi[- ]reader|diagnostic|pi-rads|segmentation|clinical task|patholog|in-vivo|lesion")
    if positive and validation not in {"", "no", "none"}:
        status = 1
        reason = "radiologist/clinical reader or downstream clinical-task evidence"
    else:
        status = 0
        reason = "no qualifying clinical-reader or downstream-task evidence"
    return {
        "TR_ClinicalEvaluation": status,
        "TR_ClinicalEvaluation_Evidence": _first_evidence(text, [r"radiologist", r"diagnostic", r"segmentation", r"clinical", r"in-vivo"]),
        "TR_ClinicalEvaluation_Reason": reason,
    }


def _hardware_awareness(row: pd.Series) -> dict[str, object]:
    text = row_text(
        row,
        [
            "Architecture_Specifics",
            "Performance_Summary",
            "Clinical_Results",
            "Notes_Questions",
            "Limitations_Mentioned",
            "Main_Finding_1",
            "Main_Finding_2",
            "Main_Finding_3",
        ],
    ).casefold()
    positive = _has(text, r"gpu|cpu|nvidia|cuda|a100|v100|rtx|ram|memory|fps|inference time|runtime|computational efficiency|model size|processing time")
    return {
        "TR_HardwareAwareness": int(positive),
        "TR_HardwareAwareness_Evidence": _first_evidence(text, [r"gpu", r"cpu", r"nvidia", r"inference", r"fps", r"runtime", r"memory", r"model size"]),
        "TR_HardwareAwareness_Reason": "hardware or inference-resource specification present" if positive else "no hardware/inference-resource specification found",
    }


def _data_diversity(row: pd.Series) -> dict[str, object]:
    text = row_text(
        row,
        [
            "Training_Data_Source",
            "Dataset_Type",
            "Performance_Summary",
            "Clinical_Results",
            "Notes_Questions",
            "Limitations_Mentioned",
            "Main_Finding_1",
            "Main_Finding_2",
            "Main_Finding_3",
        ],
    ).casefold()
    positive = _has(text, r"motion artifact|motion artefact|portable|multi[- ]?center|multicenter|scanner variability|heterogene|generaliz|vendor|low[- ]resource|community|noise|artifact variability|prospective")
    return {
        "TR_DataDiversity": int(positive),
        "TR_DataDiversity_Evidence": _first_evidence(text, [r"motion", r"portable", r"multi[- ]?center", r"heterogene", r"scanner", r"low[- ]resource", r"generaliz"]),
        "TR_DataDiversity_Reason": "real-world scanner, motion, portability, heterogeneity, or generalization issue addressed" if positive else "no qualifying real-world data-diversity evidence found",
    }


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add all corrected review fields to a loaded extraction frame."""
    result = df.copy()
    result["Field_Strength_Norm"] = result["Field_Strength_Type"].apply(normalize_field_category)
    result["Primary_Focus_Norm_Corrected"] = result["Primary_Focus"].apply(normalize_primary_focus)
    result["Dataset_Type_Norm_Corrected"] = result["Dataset_Type"].apply(normalize_dataset_category)
    result["Architecture_Norm_Corrected"] = result["AI_Architecture"].apply(normalize_architecture)

    field_rows = result.apply(_field_pair, axis=1, result_type="expand")
    ground_truth_rows = result.apply(_ground_truth, axis=1, result_type="expand")
    result = pd.concat([result, field_rows, ground_truth_rows], axis=1)
    result["Dataset_Real_Simulated"] = result.apply(_dataset_real_simulated, axis=1)
    result["Sequence_Summary"] = result.apply(_sequence_summary, axis=1)
    result["Contrast_Summary"] = result.apply(_contrast_summary, axis=1)
    dataset_evidence_rows = result.apply(_dataset_resolution_and_availability, axis=1, result_type="expand")
    result = pd.concat([result, dataset_evidence_rows], axis=1)

    tr_rows = result.apply(
        lambda row: {
            **_low_field_domain(row),
            "TR_OpenScience": int(row.get("Code_Available_Norm") == "Yes"),
            "TR_OpenScience_Evidence": _text(row.get("Code_Available")),
            "TR_OpenScience_Reason": "persistent public code/model URL recorded" if row.get("Code_Available_Norm") == "Yes" else "no persistent public code/model URL recorded",
            **_clinical_evaluation(row),
            **_hardware_awareness(row),
            **_data_diversity(row),
        },
        axis=1,
        result_type="expand",
    )
    result = pd.concat([result, tr_rows], axis=1)
    tr_cols = [
        "TR_LowFieldDomain",
        "TR_OpenScience",
        "TR_ClinicalEvaluation",
        "TR_HardwareAwareness",
        "TR_DataDiversity",
    ]
    result["TR_Score"] = result[tr_cols].sum(axis=1).astype(int)
    result["TR_Manual_Review"] = np.where(
        (result["TR_LowFieldDomain_Status"] == "Unclear")
        | (result["Field_Manual_Review"] == "Yes"),
        "Yes",
        "No",
    )
    result["SR_Primary_Strict"] = result["Primary_Focus_Norm_Corrected"].isin(
        ["Pure SR", "SR + Denoising", "SR + Other"]
    )
    result["SR_Primary_Pure_or_Denoising"] = result["Primary_Focus_Norm_Corrected"].isin(
        ["Pure SR", "SR + Denoising"]
    )
    return result


def quality_scores(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recompute the 0--9 quality score from the frozen source."""
    result = df.copy()
    result["QA_PSNR"] = result["PSNR_Numeric"].notna().astype(int)
    result["QA_SSIM"] = result["SSIM_Numeric"].notna().astype(int)
    other = result["Other_Metrics"].fillna("").astype(str).str.strip().str.casefold()
    result["QA_OtherMetrics"] = (~other.isin({"", "n/a", "na", "not reported", "none"})).astype(int)
    result["Reporting_Quality"] = result[["QA_PSNR", "QA_SSIM", "QA_OtherMetrics"]].sum(axis=1)
    result["QA_ClinVal"] = (result["Clinical_Validation_Norm"] != "None").astype(int)
    result["QA_MultiReader"] = result["Clinical_Validation_Norm"].isin(
        ["Multi-reader", "Prospective validation"]
    ).astype(int)
    result["QA_ClinicalDataset"] = result["Dataset_Type_Norm_Corrected"].isin(
        ["Clinical", "Mixed"]
    ).astype(int)
    result["Validation_Quality"] = result[["QA_ClinVal", "QA_MultiReader", "QA_ClinicalDataset"]].sum(axis=1)
    result["QA_Code"] = (result["Code_Available_Norm"] == "Yes").astype(int)
    result["QA_PublicData"] = (result["Dataset_Type_Norm_Corrected"] == "Public benchmark").astype(int)
    architecture = result["Architecture_Specifics"].fillna("").astype(str).str.strip().str.casefold()
    result["QA_ArchDescribed"] = (~architecture.isin({"", "n/a", "na", "not reported", "none"})).astype(int)
    result["Reproducibility"] = result[["QA_Code", "QA_PublicData", "QA_ArchDescribed"]].sum(axis=1)
    result["Quality_Total"] = result[["Reporting_Quality", "Validation_Quality", "Reproducibility"]].sum(axis=1)

    summary_rows = []
    for domain, column, maximum in [
        ("Reporting Quality", "Reporting_Quality", 3),
        ("Validation Quality", "Validation_Quality", 3),
        ("Reproducibility", "Reproducibility", 3),
        ("Total Quality", "Quality_Total", 9),
    ]:
        summary_rows.append(
            {
                "Domain": domain,
                "Max_Possible": maximum,
                "Mean": float(result[column].mean()),
                "Median": float(result[column].median()),
                "Std": float(result[column].std()),
                "Min": int(result[column].min()),
                "Max": int(result[column].max()),
                "N": int(result[column].notna().sum()),
            }
        )
    return result, pd.DataFrame(summary_rows)


def _rank_corr(x: pd.Series, y: pd.Series) -> float | None:
    valid = pd.concat([x, y], axis=1).dropna()
    if len(valid) < 3:
        return None
    return float(valid.iloc[:, 0].rank(method="average").corr(valid.iloc[:, 1].rank(method="average")))


def spearman_permutation(x: pd.Series, y: pd.Series, permutations: int = 10000, seed: int = 42) -> dict[str, object]:
    valid = pd.concat([x, y], axis=1).dropna()
    if len(valid) < 3:
        return {"n": int(len(valid)), "rho": None, "p_permutation": None, "permutations": 0}
    observed = _rank_corr(valid.iloc[:, 0], valid.iloc[:, 1])
    rng = np.random.default_rng(seed)
    x_rank = valid.iloc[:, 0].rank(method="average").to_numpy(dtype=float)
    y_rank = valid.iloc[:, 1].rank(method="average").to_numpy(dtype=float)
    y_centered = y_rank - y_rank.mean()
    x_centered = x_rank - x_rank.mean()
    denom = math.sqrt(float((x_centered**2).sum() * (y_centered**2).sum()))
    if denom == 0:
        return {"n": int(len(valid)), "rho": observed, "p_permutation": 1.0, "permutations": 0}
    null_extreme = 0
    for _ in range(permutations):
        shuffled = rng.permutation(y_centered)
        null_rho = float(np.dot(x_centered, shuffled) / denom)
        if abs(null_rho) >= abs(observed) - 1e-12:
            null_extreme += 1
    return {
        "n": int(len(valid)),
        "rho": observed,
        "p_permutation": float((null_extreme + 1) / (permutations + 1)),
        "permutations": int(permutations),
        "seed": seed,
    }


def unknown_audit(df: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("Field_Strength_Type", "Field_Strength_Norm", normalize_field_category),
        ("Primary_Focus", "Primary_Focus_Norm_Corrected", normalize_primary_focus),
        ("Dataset_Type", "Dataset_Type_Norm_Corrected", normalize_dataset_category),
        ("AI_Architecture", "Architecture_Norm_Corrected", normalize_architecture),
        ("Resource_Constraints_Addressed", "Resource_Constraints_Norm", lambda value: _text(value)),
        ("Code_Available", "Code_Available_Norm", lambda value: _text(value)),
    ]
    rows = []
    for raw_col, norm_col, _ in specs:
        for raw_value, count in df[raw_col].fillna("").astype(str).value_counts(dropna=False).items():
            if not raw_value.strip():
                status = "Missing"
            elif norm_col in {"Resource_Constraints_Norm", "Code_Available_Norm"}:
                status = "Recognized" if df.loc[df[raw_col].fillna("").astype(str) == raw_value, norm_col].notna().all() else "Unknown"
            else:
                normalized = df.loc[df[raw_col].fillna("").astype(str) == raw_value, norm_col].iloc[0]
                status = "Unknown" if normalized == "Unknown" else "Recognized"
            rows.append(
                {
                    "Field": raw_col,
                    "Raw_Value": raw_value,
                    "Normalized_Value": df.loc[df[raw_col].fillna("").astype(str) == raw_value, norm_col].iloc[0] if len(df.loc[df[raw_col].fillna("").astype(str) == raw_value]) else "",
                    "N": int(count),
                    "Status": status,
                }
            )
    return pd.DataFrame(rows).sort_values(["Status", "Field", "N"], ascending=[True, True, False])


def _metric_summary(subset: pd.DataFrame, column: str, prefix: str) -> dict[str, object]:
    """Return descriptive per-study metric summaries for one sensitivity cohort.

    ``PSNR_Numeric`` and ``SSIM_Numeric`` are the first parseable values from
    each paper's extraction field.  These summaries are therefore descriptive
    sensitivity results, not a pooled meta-analysis across heterogeneous
    datasets, scales, sequences, or test protocols.
    """
    values = pd.to_numeric(subset[column], errors="coerce").dropna()
    if values.empty:
        return {
            f"{prefix}_N": 0,
            f"{prefix}_Mean": None,
            f"{prefix}_SD": None,
            f"{prefix}_Median": None,
            f"{prefix}_Min": None,
            f"{prefix}_Max": None,
        }
    return {
        f"{prefix}_N": int(len(values)),
        f"{prefix}_Mean": float(values.mean()),
        f"{prefix}_SD": float(values.std()),
        f"{prefix}_Median": float(values.median()),
        f"{prefix}_Min": float(values.min()),
        f"{prefix}_Max": float(values.max()),
    }


def _manual_review_reason(row: pd.Series) -> str:
    reasons = []
    if row.get("Input_Field_Category") in {"Unknown", "Not specified"}:
        reasons.append("input field unresolved")
    if row.get("Target_Field_Category") in {"Unknown", "Not specified"}:
        reasons.append("target field unresolved")
    if "unresolved" in _lower(row.get("Field_Pair_Category")):
        reasons.append("field direction unresolved")
    if row.get("Ground_Truth_Type") == "Not reported":
        reasons.append("ground truth not reported")
    if row.get("Paired_Unpaired") == "Not reported":
        reasons.append("paired/unpaired status not reported")
    return "; ".join(reasons) if reasons else "manual confirmation required"


def build_analysis(df: pd.DataFrame) -> dict[str, pd.DataFrame | dict]:
    derived = add_derived_fields(df)
    quality, quality_summary = quality_scores(derived)
    tr_columns = [
        "Paper_ID",
        "Title",
        "Year",
        "Architecture_Norm_Corrected",
        "Application_Norm",
        "LMIC_Score",
        "TR_LowFieldDomain",
        "TR_OpenScience",
        "TR_ClinicalEvaluation",
        "TR_HardwareAwareness",
        "TR_DataDiversity",
        "TR_Score",
        "TR_LowFieldDomain_Status",
        "TR_Manual_Review",
        "TR_LowFieldDomain_Evidence",
        "TR_ClinicalEvaluation_Evidence",
        "TR_HardwareAwareness_Evidence",
        "TR_DataDiversity_Evidence",
    ]
    tr = derived[[column for column in tr_columns if column in derived.columns]].copy()
    tr_summary = pd.DataFrame(
        [
            {"Criterion": column, "N_Yes": int(derived[column].sum()), "Percent": float(derived[column].mean() * 100)}
            for column in [
                "TR_LowFieldDomain",
                "TR_OpenScience",
                "TR_ClinicalEvaluation",
                "TR_HardwareAwareness",
                "TR_DataDiversity",
            ]
        ]
        + [
            {
                "Criterion": "TR_Score",
                "N_Yes": int(derived["TR_Score"].sum()),
                "Percent": float(derived["TR_Score"].mean()),
            }
        ]
    )
    sensitivity_rows = []
    for label, mask in [
        ("All included studies", pd.Series(True, index=derived.index)),
        ("SR primary strict (Pure SR, SR + Denoising, SR + Other)", derived["SR_Primary_Strict"]),
        ("SR primary pure/denoising", derived["SR_Primary_Pure_or_Denoising"]),
    ]:
        subset = derived.loc[mask]
        sensitivity_rows.append(
            {
                "Cohort": label,
                "N": int(len(subset)),
                "Mean_LMIC": float(subset["LMIC_Score"].mean()),
                "Mean_TR": float(subset["TR_Score"].mean()),
                "Median_TR": float(subset["TR_Score"].median()),
                "LowFieldDomain_Pct": float(subset["TR_LowFieldDomain"].mean() * 100),
                "OpenScience_Pct": float(subset["TR_OpenScience"].mean() * 100),
                "ClinicalEvaluation_Pct": float(subset["TR_ClinicalEvaluation"].mean() * 100),
                "HardwareAwareness_Pct": float(subset["TR_HardwareAwareness"].mean() * 100),
                "DataDiversity_Pct": float(subset["TR_DataDiversity"].mean() * 100),
                **_metric_summary(subset, "PSNR_Numeric", "PSNR"),
                **_metric_summary(subset, "SSIM_Numeric", "SSIM"),
            }
        )
    correlation_rows = []
    for label, mask in [
        ("All included studies", pd.Series(True, index=derived.index)),
        ("SR primary strict (Pure SR, SR + Denoising, SR + Other)", derived["SR_Primary_Strict"]),
        ("SR primary pure/denoising", derived["SR_Primary_Pure_or_Denoising"]),
    ]:
        stats = spearman_permutation(derived.loc[mask, "LMIC_Score"], derived.loc[mask, "TR_Score"])
        correlation_rows.append({"Cohort": label, **stats})

    dataset_columns = [
        "Paper_ID",
        "Title",
        "Year",
        "Dataset_Size",
        "Dataset_Type",
        "Dataset_Type_Norm_Corrected",
        "Dataset_Real_Simulated",
        "Input_Resolution",
        "Target_Resolution",
        "Resolution_Evidence",
        "Sequence_Summary",
        "Contrast_Summary",
        "Dataset_Public_Availability",
        "Dataset_Availability_Evidence",
        "Input_Field_Category",
        "Target_Field_Category",
        "Field_Pair_Category",
        "Ground_Truth_Type",
        "Paired_Unpaired",
        "Field_Evidence",
        "Field_Manual_Review",
        "Training_Data_Source",
    ]
    dataset_characterization = derived[[column for column in dataset_columns if column in derived.columns]].copy()
    metric_suitability = _metric_suitability_table(derived)
    dataset_manual_review_queue = dataset_characterization.loc[
        dataset_characterization["Field_Manual_Review"] == "Yes"
    ].copy()
    dataset_manual_review_queue.insert(
        1,
        "Manual_Review_Reason",
        dataset_manual_review_queue.apply(_manual_review_reason, axis=1),
    )
    field_ground_truth = derived[
        [
            "Paper_ID",
            "Title",
            "Field_Strength_Type",
            "Input_Field_Category",
            "Target_Field_Category",
            "Field_Pair_Category",
            "Ground_Truth_Type",
            "Paired_Unpaired",
            "Field_Evidence",
            "Field_Manual_Review",
        ]
    ].copy()
    return {
        "derived": derived,
        "tr": tr,
        "tr_summary": tr_summary,
        "quality": quality,
        "quality_summary": quality_summary,
        "sensitivity": pd.DataFrame(sensitivity_rows),
        "correlation": pd.DataFrame(correlation_rows),
        "dataset_characterization": dataset_characterization,
        "metric_suitability": metric_suitability,
        "dataset_manual_review_queue": dataset_manual_review_queue,
        "field_ground_truth": field_ground_truth,
        "unknown_audit": unknown_audit(derived),
    }


def dataframe_sha256(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_analysis_outputs(analysis: dict, output_dir: Path, source_path: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_map = {
        "tr": "analysis_translational_readiness_corrected.csv",
        "tr_summary": "analysis_tr_summary_corrected.csv",
        "quality": "analysis_quality_assessment_rerun.csv",
        "quality_summary": "analysis_quality_summary_rerun.csv",
        "sensitivity": "analysis_sensitivity_primary_sr.csv",
        "correlation": "analysis_lmic_tr_correlation.csv",
        "dataset_characterization": "table_dataset_characterization.csv",
        "metric_suitability": "analysis_psnr_ssim_metric_suitability.csv",
        "dataset_manual_review_queue": "analysis_dataset_manual_review_queue.csv",
        "field_ground_truth": "analysis_field_pair_ground_truth.csv",
        "unknown_audit": "analysis_unknown_audit.csv",
    }
    output_files = {}
    for key, filename in file_map.items():
        frame = analysis[key]
        path = output_dir / filename
        frame.to_csv(path, index=False, encoding="utf-8")
        output_files[key] = str(path)

    derived = analysis["derived"]
    manifest = {
        "source": str(source_path),
        "source_sha256": sha256_file(source_path),
        "derived_data_sha256": dataframe_sha256(derived),
        "n_included": int(len(derived)),
        "fleiss_kappa": {
            "status": "pending",
            "calculation_performed": False,
            "reason": "independent ratings from all 11 reviewers are not yet available",
        },
        "tr_definition": [
            "low-field domain: explicit training/fine-tuning evidence at or below 64 mT",
            "open science: persistent public code or model URL; upon-request is reported separately",
            "clinical evaluation: clinical reader or downstream clinical-task evidence beyond PSNR/SSIM",
            "hardware awareness: hardware or inference-resource specification recorded",
            "data diversity: real-world scanner, motion, portability, heterogeneity, or generalization evidence",
        ],
        "code_counts": {
            "public": int((derived["Code_Available_Norm"] == "Yes").sum()),
            "upon_request": int((derived["Code_Available_Norm"] == "Upon request").sum()),
            "public_or_upon_request": int(derived["Code_Available_Norm"].isin(["Yes", "Upon request"]).sum()),
        },
        "resource_constraint_counts": {
            "yes": int((derived["Resource_Constraints_Norm"] == "Yes").sum()),
            "no": int((derived["Resource_Constraints_Norm"] == "No").sum()),
            "unknown": int((derived["Resource_Constraints_Norm"] == "Unknown").sum()),
        },
        "performance_sensitivity": {
            "source_columns": ["PSNR_Numeric", "SSIM_Numeric"],
            "metric_extraction": "first parseable value recorded per paper",
            "interpretation": "descriptive sensitivity summaries; not a pooled meta-analysis",
            "metric_suitability_table": output_files["metric_suitability"],
        },
        "manual_dataset_review": {
            "queue_rows": int(len(analysis["dataset_manual_review_queue"])),
            "purpose": "manual confirmation of field direction, ground truth, and paired/unpaired status",
            "unknowns_imputed": False,
        },
        "output_files": output_files,
    }
    manifest_path = output_dir / "analysis_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_files["manifest"] = str(manifest_path)
    return manifest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
