"""Conservatively extract PSNR/SSIM ground-truth evidence from cached full text.

Only exact statements in the frozen extraction or Europe PMC full-text XML are
accepted. The script never infers field direction from a metric alone and
leaves a value as ``Not reported`` when the source lacks explicit evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd

from review_metrics import PROJECT_ROOT, build_analysis, load_data


RUN_DIR = PROJECT_ROOT / "analysis" / "scientometrics" / "multisource_20260803"
RAW_DIR = RUN_DIR / "raw" / "europepmc"
OUTPUT = PROJECT_ROOT / "analysis" / "review_20260803" / "ground_truth_auto_extraction_20260804"
PUBLIC_SCIENTOMETRIC_RESULTS = PROJECT_ROOT / "tables" / "mri_scientometric_results.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split())


def xml_text(path: Path) -> str:
    try:
        root = ElementTree.parse(path).getroot()
        return clean(" ".join(root.itertext()))
    except (ElementTree.ParseError, OSError):
        return ""


def evidence(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean(text[max(0, match.start() - 180): min(len(text), match.end() + 260)])
    return ""


def classify(text: str) -> dict[str, str]:
    lower = text.casefold()
    unpaired = evidence(text, [r"\bunpaired\b"])
    synthetic = evidence(text, [r"\bdownsampled\b", r"\bbicubic\b", r"\bsimulated degradation\b", r"\bsynthetically degraded\b", r"\bundersampl(?:ed|ing)\b"])
    paired = evidence(text, [r"\bpaired (?:images|data|samples|acquisition)\b", r"\bco-registered\b", r"\bregistered pairs?\b", r"\bsame[- ]subject\b"])
    reference = evidence(text, [r"\bground truth\b", r"\bfully[- ]sampled\b", r"\breference (?:image|scan)\b"])
    lf_hf = evidence(text, [r"(?:low[- ]field|0\.064\s*t|64\s*mt|50\s*mt).{0,180}(?:high[- ]field|3\s*t|1\.5\s*t)", r"(?:high[- ]field|3\s*t|1\.5\s*t).{0,180}(?:low[- ]field|0\.064\s*t|64\s*mt|50\s*mt)"])
    lf_to_hf = evidence(text, [r"(?:low[- ]field|0\.064\s*t|64\s*mt|50\s*mt).{0,100}(?:to|→|into).{0,100}(?:high[- ]field|3\s*t|1\.5\s*t)"])
    lf_to_lf = evidence(text, [r"(?:low[- ]field|0\.064\s*t|64\s*mt|50\s*mt).{0,100}(?:to|→|into).{0,100}(?:low[- ]field|0\.064\s*t|64\s*mt|50\s*mt)"])
    if unpaired:
        ground_truth, pairedness, gt_evidence = "Unpaired real-world reference", "Unpaired", unpaired
    elif synthetic:
        ground_truth, pairedness, gt_evidence = "Synthetic degradation/proxy", "Paired by construction", synthetic
    elif paired:
        ground_truth, pairedness, gt_evidence = "Paired measured/reference", "Paired", paired
    elif reference:
        ground_truth, pairedness, gt_evidence = "Measured/reference stated", "Not reported", reference
    else:
        ground_truth, pairedness, gt_evidence = "Not reported", "Not reported", ""
    if lf_to_hf:
        direction, direction_evidence = "LF-to-HF", lf_to_hf
    elif lf_to_lf:
        direction, direction_evidence = "LF-to-LF", lf_to_lf
    elif lf_hf:
        direction, direction_evidence = "LF/HF present; direction not explicit", lf_hf
    else:
        direction, direction_evidence = "Not reported", ""
    return {
        "Auto_Ground_Truth_Type": ground_truth,
        "Auto_Paired_Unpaired": pairedness,
        "Auto_Field_Direction": direction,
        "Ground_Truth_Evidence": gt_evidence,
        "Field_Direction_Evidence": direction_evidence,
        "Auto_Confidence": "High" if pairedness in {"Paired", "Unpaired", "Paired by construction"} or direction in {"LF-to-HF", "LF-to-LF"} else "Not available",
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = PROJECT_ROOT / "data" / "data-clean.csv"
    derived = build_analysis(load_data(source))["derived"].copy()
    public_results = pd.read_csv(PUBLIC_SCIENTOMETRIC_RESULTS, encoding="utf-8-sig")
    doi_by_id = public_results.set_index("Paper_ID")["DOI"].to_dict()
    rows = []
    for _, row in derived.iterrows():
        paper_id = int(row["Paper_ID"])
        fulltext_path = RAW_DIR / f"paper_{paper_id}_fulltext.xml"
        fulltext = xml_text(fulltext_path) if fulltext_path.exists() else ""
        canonical = clean(" | ".join(str(row.get(column, "")) for column in ["Training_Data_Source", "Dataset_Size", "Performance_Summary", "Clinical_Results", "Notes_Questions", "Limitations_Mentioned"]))
        source_text = clean(" | ".join(part for part in [canonical, fulltext] if part))
        result = classify(source_text)
        rows.append({
            "Paper_ID": paper_id,
            "DOI": doi_by_id.get(paper_id, "Not available"),
            "Title": row["Title"],
            "PSNR_Reported": "Yes" if pd.notna(row.get("PSNR_Numeric")) else "No",
            "SSIM_Reported": "Yes" if pd.notna(row.get("SSIM_Numeric")) else "No",
            "EuropePMC_FullText_Cached": "Yes" if fulltext else "No",
            "EuropePMC_FullText_SHA256": sha256(fulltext_path) if fulltext_path.exists() else "Not available",
            "Existing_Ground_Truth_Type": row.get("Ground_Truth_Type", "Not reported"),
            "Existing_Paired_Unpaired": row.get("Paired_Unpaired", "Not reported"),
            **result,
        })
    table = pd.DataFrame(rows)
    metric_subset = table[(table["PSNR_Reported"] == "Yes") | (table["SSIM_Reported"] == "Yes")].copy()
    table.to_csv(OUTPUT / "ground_truth_auto_extraction_all_studies.csv", index=False, encoding="utf-8")
    metric_subset.to_csv(OUTPUT / "ground_truth_auto_extraction_metric_studies.csv", index=False, encoding="utf-8")
    summary = pd.DataFrame([
        {"Measure": "All included studies", "N": len(table)},
        {"Measure": "PSNR or SSIM reported", "N": len(metric_subset)},
        {"Measure": "Cached Europe PMC full text", "N": int((table["EuropePMC_FullText_Cached"] == "Yes").sum())},
        {"Measure": "Automatic paired/unpaired resolved", "N": int(table["Auto_Paired_Unpaired"].isin(["Paired", "Unpaired", "Paired by construction"]).sum())},
        {"Measure": "Automatic LF-to-LF or LF-to-HF direction resolved", "N": int(table["Auto_Field_Direction"].isin(["LF-to-LF", "LF-to-HF"]).sum())},
    ])
    summary.to_csv(OUTPUT / "ground_truth_auto_extraction_summary.csv", index=False, encoding="utf-8")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Only explicit cached source text is accepted; unresolved values remain Not reported.",
        "source_data": str(source),
        "source_data_sha256": sha256(source),
        "cached_fulltext_root": str(RAW_DIR),
        "cached_fulltext_files": int(sum(1 for _ in RAW_DIR.glob("paper_*_fulltext.xml"))),
        "outputs": ["ground_truth_auto_extraction_all_studies.csv", "ground_truth_auto_extraction_metric_studies.csv", "ground_truth_auto_extraction_summary.csv"],
    }
    (OUTPUT / "ground_truth_auto_extraction_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
