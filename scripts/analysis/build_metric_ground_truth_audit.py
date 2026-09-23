"""Build the PSNR/SSIM ground-truth audit from the frozen evidence layer."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from review_metrics import PROJECT_ROOT, build_analysis, load_data


OUTPUT = PROJECT_ROOT / "analysis" / "review_20260803" / "ground_truth_metric_audit_20260804"
EVIDENCE = PROJECT_ROOT / "data" / "dataset_characterization_evidence.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = PROJECT_ROOT / "data" / "data-clean.csv"
    analysis = build_analysis(load_data(source))
    dataset = analysis["dataset_characterization"].copy()
    metrics = analysis["metric_suitability"].copy()
    audit = dataset.merge(
        metrics[
            [
                "Paper_ID",
                "PSNR_Reported",
                "SSIM_Reported",
                "PSNR_or_SSIM_Reported",
                "PSNR_SSIM_Comparison_Eligibility",
                "PSNR_SSIM_Eligibility_Reason",
            ]
        ],
        on="Paper_ID",
        how="left",
        validate="one_to_one",
    )
    metric_subset = audit[audit["PSNR_or_SSIM_Reported"].eq("Yes")].copy()
    low_field_pathways = {"low-field → low-field", "low-field → standard/high-field"}

    audit.to_csv(OUTPUT / "ground_truth_metric_audit_all_studies.csv", index=False, encoding="utf-8")
    metric_subset.to_csv(OUTPUT / "ground_truth_metric_audit_metric_studies.csv", index=False, encoding="utf-8")
    summary = pd.DataFrame(
        [
            {"Measure": "All included studies", "N": len(audit)},
            {"Measure": "PSNR or SSIM reported", "N": len(metric_subset)},
            {
                "Measure": "Paired or paired-by-construction evidence (all studies)",
                "N": int(audit["Paired_Unpaired"].isin(["Paired", "Paired by construction"]).sum()),
            },
            {
                "Measure": "Metric studies eligible for within-study paired interpretation",
                "N": int(metric_subset["PSNR_SSIM_Comparison_Eligibility"].eq("Eligible").sum()),
            },
            {
                "Measure": "Metric studies with explicit low-field pathway",
                "N": int(metric_subset["Field_Pair_Category"].isin(low_field_pathways).sum()),
            },
        ]
    )
    summary.to_csv(OUTPUT / "ground_truth_metric_audit_summary.csv", index=False, encoding="utf-8")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Only the frozen full-text evidence layer is used; missing fields are never inferred from PSNR or SSIM.",
        "source_data": "data/data-clean.csv",
        "source_data_sha256": sha256(source),
        "dataset_evidence": "data/dataset_characterization_evidence.csv",
        "dataset_evidence_sha256": sha256(EVIDENCE),
        "outputs": [
            "ground_truth_metric_audit_all_studies.csv",
            "ground_truth_metric_audit_metric_studies.csv",
            "ground_truth_metric_audit_summary.csv",
        ],
    }
    (OUTPUT / "ground_truth_metric_audit_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
