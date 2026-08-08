"""Run the local, corrected MRI-LMICs review analyses.

The default mode writes to ``analysis/review_20260803`` and never overwrites
the historical tables.  Use ``--promote`` only after reviewing the generated
CSV files; promoted files are backed up first.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from review_metrics import PROJECT_ROOT, build_analysis, load_data, write_analysis_outputs


def _architecture_application_summary(derived: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group_type, column in [("Architecture", "Architecture_Norm_Corrected"), ("Application", "Application_Norm")]:
        grouped = (
            derived.groupby(column, dropna=False)["TR_Score"]
            .agg(["count", "mean", "median", "min", "max"])
            .rename(columns={"count": "N"})
            .reset_index()
            .rename(columns={column: "Group"})
        )
        grouped.insert(0, "Group_Type", group_type)
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True)


def _promote_outputs(analysis: dict, repo: Path, run_date: str) -> dict[str, str]:
    tables = repo / "tables"
    provenance = repo / "analysis" / "reproducibility" / "provenance" / f"promoted_before_{run_date}"
    provenance.mkdir(parents=True, exist_ok=True)

    derived = analysis["derived"]
    quality_cols = [
        "Paper_ID", "Title", "Year",
        "QA_PSNR", "QA_SSIM", "QA_OtherMetrics", "Reporting_Quality",
        "QA_ClinVal", "QA_MultiReader", "QA_ClinicalDataset", "Validation_Quality",
        "QA_Code", "QA_PublicData", "QA_ArchDescribed", "Reproducibility",
        "Quality_Total",
    ]
    promoted_frames = {
        "analysis_translational_readiness.csv": analysis["tr"],
        "analysis_tr_by_architecture.csv": _architecture_application_summary(derived),
        "analysis_quality_assessment.csv": analysis["quality"][quality_cols],
        "analysis_quality_summary.csv": analysis["quality_summary"],
        "analysis_sensitivity_primary_sr.csv": analysis["sensitivity"],
        "analysis_lmic_tr_correlation.csv": analysis["correlation"],
        "table_dataset_characterization.csv": analysis["dataset_characterization"],
        "analysis_psnr_ssim_metric_suitability.csv": analysis["metric_suitability"],
        "analysis_dataset_manual_review_queue.csv": analysis["dataset_manual_review_queue"],
        "analysis_field_pair_ground_truth.csv": analysis["field_ground_truth"],
        "analysis_unknown_audit.csv": analysis["unknown_audit"],
    }
    promoted = {}
    for filename, frame in promoted_frames.items():
        target = tables / filename
        if target.exists():
            shutil.copy2(target, provenance / filename)
        frame.to_csv(target, index=False, encoding="utf-8")
        promoted[filename] = str(target)
    return promoted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "review_20260803",
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "data-clean.csv",
    )
    parser.add_argument("--promote", action="store_true", help="Back up and update selected top-level tables")
    parser.add_argument("--run-date", default="20260803")
    args = parser.parse_args()

    data_path = args.data_path.resolve()
    output_dir = args.output_dir.resolve()
    raw = load_data(data_path)
    analysis = build_analysis(raw)
    manifest = write_analysis_outputs(analysis, output_dir, data_path)

    if args.promote:
        manifest["promoted_outputs"] = _promote_outputs(analysis, PROJECT_ROOT, args.run_date)
        manifest["promoted_at_utc"] = datetime.now(timezone.utc).isoformat()
        (output_dir / "analysis_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    quality_summary = analysis["quality_summary"]
    total_quality = quality_summary[quality_summary["Domain"] == "Total Quality"].iloc[0]
    print("=== Reproducible MRI-LMICs review analysis ===")
    print(f"Included studies: {len(raw)}")
    print(
        "Quality total: "
        f"mean={total_quality['Mean']:.4f}, SD={total_quality['Std']:.4f}, "
        f"median={total_quality['Median']:.1f}"
    )
    print(
        "TR: "
        f"mean={analysis['derived']['TR_Score'].mean():.4f}, "
        f"median={analysis['derived']['TR_Score'].median():.1f}"
    )
    print(
        "Code: "
        f"public={(analysis['derived']['Code_Available_Norm'] == 'Yes').sum()}, "
        f"upon_request={(analysis['derived']['Code_Available_Norm'] == 'Upon request').sum()}"
    )
    print(
        "Resource constraints: "
        f"yes={(analysis['derived']['Resource_Constraints_Norm'] == 'Yes').sum()}, "
        f"unknown={(analysis['derived']['Resource_Constraints_Norm'] == 'Unknown').sum()}"
    )
    print(f"Outputs: {output_dir}")
    print(f"Fleiss kappa: {manifest['fleiss_kappa']['status']}")


if __name__ == "__main__":
    main()
