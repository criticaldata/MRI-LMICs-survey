"""Offline verification of the local MRI-LMICs reproducibility package."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    repro = REPO / "analysis" / "reproducibility"
    analysis = REPO / "analysis" / "review_20260803"

    data = pd.read_csv(REPO / "data" / "data-clean.csv")
    screening = pd.read_csv(repro / "screening_log_183.csv")
    assignments = pd.read_csv(repro / "included_studies_assignments_48.csv")
    manifest = json.loads((repro / "source_manifest.json").read_text(encoding="utf-8"))
    analysis_manifest = json.loads((analysis / "analysis_manifest.json").read_text(encoding="utf-8"))
    quality = pd.read_csv(analysis / "analysis_quality_summary_rerun.csv")
    sensitivity = pd.read_csv(analysis / "analysis_sensitivity_primary_sr.csv")
    dataset_characterization = pd.read_csv(analysis / "table_dataset_characterization.csv")
    metric_suitability = pd.read_csv(analysis / "analysis_psnr_ssim_metric_suitability.csv")
    manual_review_queue = pd.read_csv(analysis / "analysis_dataset_manual_review_queue.csv")
    temporal_primary = pd.read_csv(REPO / "tables" / "analysis_temporal_trends.csv")
    temporal_preliminary = pd.read_csv(REPO / "tables" / "analysis_temporal_trends_2025_preliminary.csv")
    tr_weighting = pd.read_csv(analysis / "tr_weighting_sensitivity_20260804" / "analysis_tr_weighting_sensitivity.csv")
    tr_primary_leave_one_out = pd.read_csv(analysis / "tr_weighting_sensitivity_20260804" / "analysis_tr_primary_leave_one_out.csv")
    ground_truth_summary = pd.read_csv(analysis / "ground_truth_auto_extraction_20260804" / "ground_truth_auto_extraction_summary.csv")
    rf_robustness = pd.read_csv(analysis / "random_forest_robustness_20260804" / "rf_repeated_cv_summary.csv")

    require(len(data) == 48, f"data-clean.csv has {len(data)} rows, expected 48")
    require(len(screening) == 183, f"screening log has {len(screening)} rows, expected 183")
    require((screening["Status"].str.casefold() == "included").sum() == 48, "included screening count is not 48")
    require((screening["Status"].str.casefold() == "excluded").sum() == 135, "excluded screening count is not 135")
    require(len(assignments) == 48 and assignments["Paper_ID"].nunique() == 48, "assignment mapping is not one-to-one")
    require(manifest["reviewer_ratings"]["fleiss_kappa_status"] == "pending_until_complete_independent_ratings", "Fleiss kappa status changed unexpectedly")
    require(analysis_manifest["fleiss_kappa"]["calculation_performed"] is False, "corrected run must not calculate Fleiss kappa")

    total_quality = quality.loc[quality["Domain"] == "Total Quality"].iloc[0]
    require(abs(float(total_quality["Mean"]) - 4.1458333333) < 1e-6, "quality rerun mean changed unexpectedly")
    require(abs(float(total_quality["Std"]) - 1.1848257495) < 1e-6, "quality rerun SD changed unexpectedly")
    require(analysis_manifest["code_counts"]["public"] == 6, "public code count is not 6")
    require(analysis_manifest["code_counts"]["upon_request"] == 2, "upon-request code count is not 2")
    require(analysis_manifest["resource_constraint_counts"]["yes"] == 33, "resource-constraint count is not 33")
    require(
        list(sensitivity["N"]) == [48, 30, 23],
        "sensitivity cohort sizes changed unexpectedly",
    )
    require(
        {
            "PSNR_N",
            "PSNR_Mean",
            "PSNR_SD",
            "PSNR_Median",
            "PSNR_Min",
            "PSNR_Max",
            "SSIM_N",
            "SSIM_Mean",
            "SSIM_SD",
            "SSIM_Median",
            "SSIM_Min",
            "SSIM_Max",
        }.issubset(sensitivity.columns),
        "PSNR/SSIM sensitivity columns are incomplete",
    )
    require(len(dataset_characterization) == 48, "dataset characterization should contain 48 studies")
    require(
        {
            "Input_Resolution",
            "Target_Resolution",
            "Dataset_Public_Availability",
            "Resolution_Evidence",
            "Dataset_Availability_Evidence",
        }.issubset(dataset_characterization.columns),
        "dataset characterization lacks reviewer-requested evidence columns",
    )
    require(len(metric_suitability) == 48, "metric suitability table should contain 48 studies")
    require(metric_suitability["Paper_ID"].nunique() == 48, "metric suitability Paper_ID values are not unique")
    require(
        set(metric_suitability["PSNR_SSIM_Comparison_Eligibility"]).issubset(
            {"Eligible", "Not eligible", "Not reported"}
        ),
        "metric suitability uses an unexpected eligibility value",
    )
    require(len(manual_review_queue) == 47, "manual dataset-review queue should contain 47 studies")
    require(temporal_primary["Year"].tolist() == [2020, 2021, 2022, 2023, 2024], "primary temporal scope is not 2020-2024")
    require(
        temporal_preliminary["Year"].tolist() == [2025]
        and temporal_preliminary["Status"].tolist() == ["Preliminary and incomplete"],
        "2025 data are not isolated as preliminary",
    )
    require(len(tr_weighting) == 4, "TR weighting sensitivity should have four prespecified schemes")
    require((tr_weighting["Rank_Spearman_vs_Primary_Equal"] >= 0.94).all(), "TR ranking is not stable across weighting schemes")
    require(len(tr_primary_leave_one_out) == 48, "TR primary leave-one-out analysis should contain all 48 studies")
    require((tr_primary_leave_one_out["LMIC_TR_Spearman_Rho"] > 0).all(), "TR primary association is not directionally stable in leave-one-out analysis")
    metric_row = ground_truth_summary.loc[ground_truth_summary["Measure"] == "PSNR or SSIM reported", "N"].iloc[0]
    require(int(metric_row) == 20, "ground-truth metric-study subset should contain 20 studies")
    require(set(rf_robustness["Model"]) == {"Constrained Random Forest", "Regularized ridge benchmark", "Regularized ordinal logistic", "Mean baseline"}, "RF robustness comparison is incomplete")
    require((rf_robustness["Splits"] == 50).all(), "RF robustness should use 50 repeated held-out splits")

    for path in [
        analysis / "analysis_translational_readiness_corrected.csv",
        analysis / "analysis_sensitivity_primary_sr.csv",
        analysis / "analysis_lmic_tr_correlation.csv",
        analysis / "table_dataset_characterization.csv",
        analysis / "analysis_psnr_ssim_metric_suitability.csv",
        analysis / "analysis_dataset_manual_review_queue.csv",
        analysis / "analysis_field_pair_ground_truth.csv",
        analysis / "analysis_unknown_audit.csv",
        analysis / "tr_weighting_sensitivity_20260804" / "tr_weighting_study_scores.csv",
        analysis / "tr_weighting_sensitivity_20260804" / "analysis_tr_primary_leave_one_out.csv",
        analysis / "ground_truth_auto_extraction_20260804" / "ground_truth_auto_extraction_metric_studies.csv",
        analysis / "random_forest_robustness_20260804" / "rf_heldout_permutation_summary.csv",
        REPO / "figures" / "main" / "png" / "fig4_performance_comparison.png",
        REPO / "figures" / "main" / "pdf" / "fig4_performance_comparison.pdf",
        REPO / "figures" / "supplementary" / "png" / "figS1_temporal_trends.png",
        REPO / "figures" / "supplementary" / "pdf" / "figS1_temporal_trends.pdf",
        repro / "reviewer_scoring" / "Reviewer_Scoring_Template.xlsx",
    ]:
        require(path.exists(), f"missing output: {path}")

    result = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_calls_made": False,
        "github_modified": False,
        "screening": {"total": 183, "included": 48, "excluded": 135},
        "quality_mean": float(total_quality["Mean"]),
        "quality_sample_sd": float(total_quality["Std"]),
        "public_code": 6,
        "upon_request_code": 2,
        "resource_constraints_yes": 33,
        "tr_weighting_schemes": int(len(tr_weighting)),
        "ground_truth_metric_studies": int(metric_row),
        "rf_robustness_splits_per_model": 50,
        "fleiss_kappa": "pending",
        "status": "PASS",
    }
    output = repro / "verification_20260803.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
