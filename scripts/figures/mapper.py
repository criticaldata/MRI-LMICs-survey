"""
Centralized mappings and utilities for MRI-LMICs survey figure generation.

All normalization maps, color schemes, and shared data-loading logic live here
to ensure cross-figure consistency.
"""

import re
import sys
import pandas as pd
import numpy as np
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
from scripts.field_taxonomy import (  # noqa: E402
    FIELD_CATEGORY_ORDER,
    normalize_field_category,
)


# ---------------------------------------------------------------------------
# Color schemes
# ---------------------------------------------------------------------------

APPLICATION_COLORS = {
    "Brain": "#3498db",
    "Cardiac": "#e74c3c",
    "Musculoskeletal": "#2ecc71",
    "Flow": "#9b59b6",
    "Abdominal": "#e67e22",
    "Prostate": "#1abc9c",
    "Pediatric": "#f39c12",
    "General": "#95a5a6",
    "Non-MRI": "#bdc3c7",
    "Other": "#7f8c8d",
}

ARCHITECTURE_COLORS = {
    "CNN": "#3498db",
    "U-Net": "#2ecc71",
    "GAN": "#e74c3c",
    "Hybrid": "#9b59b6",
    "Transformer": "#f39c12",
    "Diffusion": "#1abc9c",
    "Non-AI": "#95a5a6",
    "Other": "#7f8c8d",
}

FIELD_STRENGTH_COLORS = {
    "Ultra-low-field (<0.05 T)": "#8e44ad",
    "Low-field (0.05-0.5 T)": "#e74c3c",
    "Intermediate-field (>0.5-<1.5 T)": "#f39c12",
    "Standard-field (1.5-3 T)": "#3498db",
    "High-field (>3 T)": "#2ecc71",
    "Ultra-low-field (strength unspecified)": "#af7ac5",
    "Low-field (threshold unspecified)": "#f1948a",
    "Standard-field (strength unspecified)": "#85c1e9",
    "High-field (threshold unspecified)": "#82e0aa",
    "Mixed": "#9b59b6",
    "Not specified": "#bdc3c7",
    "Not reported": "#85929e",
    "Unknown": "#566573",
}

LMIC_SCORE_COLORS = {
    1: "#d35400",
    2: "#e67e22",
    3: "#f39c12",
    4: "#27ae60",
    5: "#16a085",
}

PRIMARY_FOCUS_COLORS = {
    "Pure SR": "#3498db",
    "SR + Denoising": "#2ecc71",
    "SR + Segmentation": "#e74c3c",
    "SR + Classification": "#9b59b6",
    "SR + Diagnosis": "#f39c12",
    "SR + Other": "#1abc9c",
    "Review/Survey": "#95a5a6",
    "Other": "#7f8c8d",
}

# ---------------------------------------------------------------------------
# Normalization maps
# ---------------------------------------------------------------------------

APPLICATION_MAP = {
    "Brain": "Brain",
    "Brain MRI": "Brain",
    "Brain gliomas diagnosis and grading": "Brain",
    "Neuroradiology / Multiple Sclerosis (MS)": "Brain",
    "Improve MRI white-matter microstructure": "Brain",
    "Cerebrovascular hemodynamics": "Brain",
    "Pediatric Neuroimaging / Youth Mental Health": "Pediatric",
    "Cardiac": "Cardiac",
    "myocardium infarction": "Cardiac",
    "Cardiac, brain, knee, multimodal whole heart": "General",
    "Musculoskeletal": "Musculoskeletal",
    "Musculoskeletal (knee)": "Musculoskeletal",
    "Musculoskeletal (wrist/hand)": "Musculoskeletal",
    "knee": "Musculoskeletal",
    "Flow": "Flow",
    "Abdominal": "Abdominal",
    "Prostate MRI": "Prostate",
    "General": "General",
    "Digital Image Enhancement using conventional neural network": "General",
    "Image Enhancement in Low-Field MRI": "General",
    "General(Non MRI modality-ultrasound": "Non-MRI",
    "Not MRI (Hyperspectral Imaging)": "Non-MRI",
    "Not MRI (Remote Sensing)": "Non-MRI",
}

PRIMARY_FOCUS_MAP = {
    "Pure_SR": "Pure SR",
    "Denoising+SR": "SR + Denoising",
    "Denoising + SR": "SR + Denoising",
    "denoising and distortion correction in low\u2011field MRI": "SR + Denoising",
    "SR+Segmentation": "SR + Segmentation",
    "SR + segmentation": "SR + Segmentation",
    "Segmentation + Classification": "SR + Segmentation",
    "Multi-class semantic segmentation of myocardial infarction and microvascular obstruction": "SR + Segmentation",
    "SR+Classification": "SR + Classification",
    "SR +Classification": "SR + Classification",
    "SR+Diagnosis": "SR + Diagnosis",
    "Narrative review of Computer-Aided Diagnosis (CAD) systems for glioma brain tumors on MRI": "Review/Survey",
    "Is a review": "Review/Survey",
    "Is a survey": "Review/Survey",
    "SR + Image generation/contrast enhancement": "SR + Other",
    "SR + acceleration": "SR + Other",
    "Reconstruction of undersampled MRI (accelerated acquisition)": "SR + Other",
    "2 step super-resolution framework for 4D MRI Flow": "Pure SR",
    "Assessing generalization and applying Transfer Learning": "SR + Other",
}


def normalize_primary_focus(value):
    """Classify study focus without treating generic reconstruction as SR.

    Strict SR sensitivity cohorts require an explicit SR label or a stated
    low-to-high spatial-resolution task. Transfer learning, undersampled
    reconstruction, denoising, and image enhancement alone are not sufficient.
    """
    if value is None or pd.isna(value):
        return "Other"
    text = " ".join(str(value).replace("\u00a0", " ").split()).casefold()
    if not text:
        return "Other"
    if "review" in text or "survey" in text:
        return "Review/Survey"

    explicit_sr = (
        text in {"pure_sr", "pure sr"}
        or re.search(r"\bsr\b|super[ -]?resolution", text) is not None
    )
    explicit_resolution_gain = (
        re.search(r"low[ -]?resolution", text) is not None
        and re.search(r"high[ -]?resolution", text) is not None
    )
    if not explicit_sr and not explicit_resolution_gain:
        return "Other"

    if "denois" in text:
        return "SR + Denoising"
    if "classif" in text:
        return "SR + Classification"
    if "diagnos" in text:
        return "SR + Diagnosis"
    if "segment" in text:
        return "SR + Segmentation"
    if text in {"pure_sr", "pure sr"} or explicit_resolution_gain:
        return "Pure SR"
    if "acceleration" in text or "accelerated" in text or "image generation" in text:
        return "SR + Other"
    return "Pure SR"

ARCHITECTURE_MAP = {
    "CNN": "CNN",
    "Deep Learning (Convolutional Neural Network)": "CNN",
    "deep residual cnn": "CNN",
    "SRCNN": "CNN",
    "SRDenseNet": "CNN",
    "DNN + CNN": "CNN",
    "Deep Learning (DL) framework integrating compressed sensing with convolutional neural networks": "CNN",
    "U-Net": "U-Net",
    "ShuffleUNet": "U-Net",
    "unet, u-net-vgg15, segnet, resunet": "U-Net",
    "CNN (U-Net + RED-Net)": "U-Net",
    "U-Net + CNN": "U-Net",
    "CNN, U-Net": "U-Net",
    "GAN": "GAN",
    "Fusion attention based GAN": "GAN",
    "Hybrid": "Hybrid",
    "CNN, Hybrid": "Hybrid",
    "CNN, U-Net, Hybrid": "Hybrid",
    "CNN, GAN, Hybrid": "Hybrid",
    "CNN, GAN, Transformer": "Hybrid",
    "Transformer": "Transformer",
    "Diffusion, U-Net": "Diffusion",
    "Non-AI / Fourier-based (Specifically stated as NOT relying on deep learning)": "Non-AI",
}

DATASET_TYPE_MAP = {
    "Public_benchmark": "Public benchmark",
    "public miccai benchmark": "Public benchmark",
    "Public IXI diffusion-weighted MRI of healthy subjects": "Public benchmark",
    "Repository of Images of the centra nervous system": "Public benchmark",
    "PROSTATEx, Prostate-3T, Prostate Fused-MRI-Pathology, Prostate-diagnosis and Prostate MRI.": "Public benchmark",
    "Clinical": "Clinical",
    "Clinical (Single center)": "Clinical",
    "Prospective study of adult male patients with suspected prostate cancer": "Clinical",
    "Patients with MS or suspected MS": "Clinical",
    "Community sample of young people (Ages 9\u201326 years)": "Clinical",
    "Mixed": "Mixed",
    "mixed": "Mixed",
    "Mixed (Clinical and Public-benchmark (HCP, Leipzig))": "Mixed",
    "4d flow MRI of intracranial arteries": "Mixed",
    "Cardiac, brain, knee, multimodal whole heart": "Mixed",
    "Human brain and cardiac images": "Mixed",
    "Synthetic": "Synthetic",
    "Private_proprietary": "Private",
    "Not reported": "Not reported",
}

LMIC_SCORE_MAP = {
    "1.0": 1, "2.0": 2, "3.0": 3, "4.0": 4, "5.0": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "High": 4, "Medium": 3, "Moderate": 3, "medium": 3,
}

YES_NO_MAP = {
    "Yes": "Yes", "yes": "Yes", "No": "No", "no": "No",
    "Yes (1.5T)": "Yes", "Yes (0.4T)": "Yes",
    "Yes (Primary focus is 0.064 T / 64 mT)": "Yes",
    "Yes (64 mT / 0.064 Tesla)": "Yes",
    "Yes (explicit focus on low-field as cost-effective)": "Yes",
    "Not reported": "No", "No (not stated)": "No",
    "No (data available on request; no code repository mentioned)": "No",
}

CODE_AVAILABLE_MAP = {
    "Yes": "Yes", "yes": "Yes",
    "Yes ( https://github.com/hongxiangharry/Stochastic-IQT )": "Yes",
    "https://github.com/EdwardFerdian/4DFlowNet": "Yes",
    "No": "No", "no": "No",
    "No (not stated)": "No",
    "No (data available on request; no code repository mentioned)": "No",
    "Upon_request": "Upon request",
    "Not reported": "No",
}


def normalize_resource_constraints(value):
    """Normalize resource-constraint evidence without treating unknown as Yes.

    The extraction sheet contains both binary entries and narrative evidence.
    A narrative entry is affirmative only when it explicitly describes a
    resource, portability, acquisition-time, or computational constraint.
    Unrecognized or blank values remain ``Unknown`` so they cannot inflate the
    deployment counts by default.
    """
    if pd.isna(value):
        return "Unknown"
    text = " ".join(str(value).strip().split())
    if not text:
        return "Unknown"
    lower = text.casefold()
    if lower in {"yes", "y", "true"} or lower.startswith("yes ("):
        return "Yes"
    if lower in {"no", "n", "false"} or lower.startswith("no ("):
        return "No"
    affirmative_markers = (
        "addressed",
        "computational efficiency",
        "model size",
        "scan time",
        "motion artefact",
        "motion artifact",
        "cost-effective",
        "cost-effectiveness",
        "low-resource",
        "low resource",
        "portability",
        "portable",
        "reduced power",
    )
    if any(marker in lower for marker in affirmative_markers):
        return "Yes"
    return "Unknown"


def normalize_code_available(value):
    """Separate public code from upon-request availability."""
    if pd.isna(value):
        return "Unknown"
    text = " ".join(str(value).strip().split())
    if not text:
        return "Unknown"
    lower = text.casefold()
    if "upon_request" in lower or "upon request" in lower:
        return "Upon request"
    if lower in {"yes", "y", "true"} or "github.com/" in lower or "gitlab.com/" in lower:
        return "Yes"
    if lower in {"no", "n", "false"} or lower.startswith("no ("):
        return "No"
    if "not reported" in lower:
        return "Not reported"
    return "Unknown"


def normalize_field_strength(value):
    """Use the shared field taxonomy; input and target are classified separately."""
    return normalize_field_category(value)

CLINICAL_VALIDATION_MAP = {
    "None": "None",
    "No": "None",
    "Multi-reader": "Multi-reader",
    "Multi-reader (7 radiologists)": "Multi-reader",
    "Multi-reader (2 board-certified radiologists), with statistical testing": "Multi-reader",
    "Multi-reader quantitative + subjective evaluation": "Multi-reader",
    "Diagnostic comparison": "Diagnostic comparison",
    "Diagnostic_comparison": "Diagnostic comparison",
    "Radiologist_visual": "Radiologist visual",
    "Blinded qualitative assessment by three experienced MS neurologists using a defined Likert scale": "Radiologist visual",
    "PI-RADS score agreement assessment by two board-certified radiologists with intra- and interreader reproducibility testing": "Multi-reader",
    "Prospective validation on acquired undersampled data": "Prospective validation",
    "Retrospective validation on expert-annotated dataset; qualitative visual validation on unlabeled cases": "Retrospective validation",
    "Retrospective imaging only": "Retrospective validation",
    "External challenge evaluation": "External challenge",
    "In-silico validation against CFD ground truth + retrospective in-vivo feasibility study in healthy volunteers.": "In-silico + in-vivo",
    "Quantitative and qualitative comparison (image artifacts) against fully-sampled reference images.": "Quantitative comparison",
    "Quantitative comparison of automated brain segmentation (FreeSurfer) measures between low-field and high-field scans": "Quantitative comparison",
}


# ---------------------------------------------------------------------------
# Data loading and cleaning
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_INCLUDED_STUDIES = 45  # eligible MRI enhancement/SR studies after screening reconciliation
N_ALL = 183              # records identified in the database search


def get_project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


def apply_primary_sr_scope_evidence(df):
    """Attach the evidence-reviewed focus labels to canonical study rows.

    The extraction's normalized focus field remains available for traceability,
    while summary tables and figures use the reconciled scope classification.
    Matching is validated against Paper_ID, DOI, and title so reordered or
    mismatched evidence cannot silently relabel a study.
    """
    evidence_path = get_project_root() / "data" / "primary_sr_scope_evidence.csv"
    if not evidence_path.exists():
        raise FileNotFoundError(
            "Missing data/primary_sr_scope_evidence.csv; run the reproducibility "
            "pipeline before generating study-focus summaries."
        )

    evidence = pd.read_csv(evidence_path)
    required = {"Paper_ID", "DOI", "Title", "Primary_Focus_Corrected"}
    missing = required.difference(evidence.columns)
    if missing:
        raise ValueError(
            "Primary SR scope evidence is missing required columns: "
            + ", ".join(sorted(missing))
        )

    if evidence["Paper_ID"].duplicated().any() or evidence["DOI"].duplicated().any():
        raise ValueError("Primary SR scope evidence contains duplicate study keys")

    if len(evidence) != len(df):
        raise ValueError(
            "Primary SR scope evidence must contain exactly one row per canonical study"
        )

    data_ids = pd.to_numeric(df["Paper_ID"], errors="raise").astype(int).tolist()
    evidence_ids = pd.to_numeric(evidence["Paper_ID"], errors="raise").astype(int).tolist()
    if data_ids != evidence_ids:
        raise ValueError("Primary SR scope evidence Paper_ID order does not match canonical data")

    def normalized_title(values):
        return (
            values.astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.casefold()
            .tolist()
        )

    data_dois = df["DOI"].astype(str).str.strip().str.casefold().tolist()
    evidence_dois = evidence["DOI"].astype(str).str.strip().str.casefold().tolist()
    if data_dois != evidence_dois:
        raise ValueError("Primary SR scope evidence DOI order does not match canonical data")
    if normalized_title(df["Title"]) != normalized_title(evidence["Title"]):
        raise ValueError("Primary SR scope evidence titles do not match canonical data")

    focus = evidence["Primary_Focus_Corrected"].astype("string").str.strip()
    if focus.isna().any() or focus.eq("").any():
        raise ValueError("Primary SR scope evidence contains an empty corrected focus")

    result = df.copy()
    result["Primary_Focus_Corrected"] = focus.tolist()
    return result


def load_data(data_path=None):
    """Load and clean the MRI SR extraction CSV.

    Returns a DataFrame with normalized categorical columns and parsed
    numeric metrics (PSNR, SSIM).
    """
    if data_path is None:
        data_path = get_project_root() / "data" / "data-clean.csv"

    df = pd.read_csv(data_path)

    if "Paper_ID" not in df.columns:
        raise ValueError("Canonical MRI data must contain Paper_ID")
    df["Paper_ID"] = pd.to_numeric(df["Paper_ID"], errors="raise").astype(int)
    if "Title" not in df.columns or df["Title"].astype(str).str.strip().eq("").any():
        raise ValueError("Canonical MRI data must contain a non-empty Title for every study")
    contract_path = get_project_root() / "data" / "included_study_order.csv"
    if contract_path.exists():
        contract = pd.read_csv(contract_path)
        expected_ids = list(range(1, len(contract) + 1))
        if contract.empty or contract["Paper_ID"].tolist() != expected_ids:
            raise ValueError("included_study_order.csv must use contiguous IDs starting at 1")
        if len(df) != len(contract) or df["Paper_ID"].tolist() != expected_ids:
            raise ValueError("Canonical MRI data must match the contiguous included-study contract")
        data_titles = df["Title"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.casefold()
        contract_titles = contract["Title"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.casefold()
        if data_titles.tolist() != contract_titles.tolist():
            raise ValueError("Canonical data titles do not match included_study_order.csv")
    else:
        expected_ids = list(range(1, len(df) + 1))
        if not len(df) or df["Paper_ID"].tolist() != expected_ids:
            raise ValueError("Canonical MRI data must use contiguous Paper_ID values starting at 1")

    # Strip whitespace from string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    # Parse Year to int
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

    # Normalize categorical columns
    df["Application_Norm"] = df["MRI_Application_Area"].map(APPLICATION_MAP).fillna("Other")
    df["Field_Strength_Norm"] = df["Field_Strength_Type"].apply(normalize_field_strength)
    df["Primary_Focus_Norm"] = df["Primary_Focus"].apply(normalize_primary_focus)
    df["Architecture_Norm"] = df["AI_Architecture"].map(ARCHITECTURE_MAP).fillna("Other")
    df["Dataset_Type_Norm"] = df["Dataset_Type"].map(DATASET_TYPE_MAP).fillna("Other")
    df["LMIC_Score"] = df["LMIC_Relevance_Score"].astype(str).map(LMIC_SCORE_MAP)
    df["LMIC_Relevance_Score"] = pd.to_numeric(df["LMIC_Score"], errors='coerce')
    df["Low_Field_Norm"] = df["Low_Field_Mentioned"].map(YES_NO_MAP).fillna("Unknown")
    df["Resource_Constraints_Norm"] = df["Resource_Constraints_Addressed"].apply(
        normalize_resource_constraints
    )
    df["Code_Available_Norm"] = df["Code_Available"].apply(normalize_code_available)
    df["Clinical_Validation_Norm"] = df["Clinical_Validation_Type"].map(CLINICAL_VALIDATION_MAP).fillna("None")

    # Parse PSNR — extract first numeric value (dB)
    df["PSNR_Numeric"] = df["PSNR_Value"].apply(_parse_first_numeric)

    # Parse SSIM — extract first numeric value in [0, 1]
    df["SSIM_Numeric"] = df["SSIM_Value"].apply(_parse_first_numeric)
    # Filter out values > 1 (likely errors or dB-format values)
    df.loc[df["SSIM_Numeric"] > 1, "SSIM_Numeric"] = np.nan

    return df


def _parse_first_numeric(value):
    """Extract the first plausible numeric value from a free-text metric string."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    # Skip obvious non-numeric entries
    skip_patterns = ("not reported", "n/a", "reported", "not explicitly reported",
                     "not reported.", "uses", "paper uses")
    if s.lower().startswith(skip_patterns):
        return np.nan
    # Find first float-like pattern (at least two digits to avoid matching
    # single-digit counts or IDs like "3D", "4D", "2×", etc.)
    matches = re.findall(r"(\d+\.\d+|\d{2,}\.?\d*)", s)
    for m in matches:
        num = float(m)
        # PSNR typically 15-60 dB, SSIM typically 0.4-1.0
        # Reject values that are clearly not image quality metrics
        if 10.0 <= num <= 80.0 or (0.4 <= num <= 1.0):
            return num
    return np.nan


# ---------------------------------------------------------------------------
# Figure saving utilities
# ---------------------------------------------------------------------------

def panel_title(ax, title, subtitle="", fontsize=12):
    """Set a panel title with an optional gray italic subtitle below it.

    Renders as a single two-line ax.set_title so that bbox_inches='tight'
    properly accounts for the vertical space.
    """
    if subtitle:
        combined = f"$\\bf{{{_escape_latex(title)}}}$\n{subtitle}"
        ax.set_title(combined, fontsize=fontsize, loc="left", pad=12,
                     linespacing=2.2, color="#1B2631",
                     fontdict={"fontsize": fontsize})
        # Override: make subtitle line smaller + gray
        # Since matplotlib doesn't support per-line styling easily,
        # use the simpler approach: bold title via set_title, subtitle via annotation
        ax.set_title(title, fontsize=fontsize, fontweight="bold", loc="left", pad=28)
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 16), textcoords="offset points",
                    fontsize=max(fontsize - 3, 7), color="#7f8c8d",
                    style="italic", va="bottom", annotation_clip=False)
    else:
        ax.set_title(title, fontsize=fontsize, fontweight="bold", loc="left", pad=12)


def _escape_latex(s):
    """Escape characters for matplotlib mathtext."""
    return s.replace("_", r"\_").replace("&", r"\&")


def save_figure(fig, filename, output_dir=None, dpi=300):
    """Save a matplotlib figure as PNG and PDF."""
    if output_dir is None:
        output_dir = get_project_root() / "figures" / "main"
    output_dir = Path(output_dir)

    png_dir = output_dir / "png"
    pdf_dir = output_dir / "pdf"
    png_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    fig.savefig(png_dir / f"{filename}.png", dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    fig.savefig(
        pdf_dir / f"{filename}.pdf",
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
        metadata={"CreationDate": None, "ModDate": None},
    )
    print(f"  Saved: {png_dir / filename}.png")
    print(f"  Saved: {pdf_dir / filename}.pdf")


def configure_matplotlib():
    """Set publication-quality matplotlib defaults."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.dpi": 150,
        "savefig.dpi": 300,
    })
