"""Offline verification of the local MRI-LMICs reproducibility package."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalize_title(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = text.casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def require_canonical_identity(
    frame: pd.DataFrame, label: str, title_by_id: dict[int, str]
) -> None:
    require(
        {"Paper_ID", "Title"}.issubset(frame.columns),
        f"{label} lacks canonical identity columns",
    )
    ids = pd.to_numeric(frame["Paper_ID"], errors="raise").astype(int)
    require(set(ids).issubset(set(title_by_id)), f"{label} contains unknown Paper_ID values")
    if len(frame) == 48:
        require(
            sorted(ids.tolist()) == list(range(1, 49)),
            f"{label} is not a complete contiguous 1-48 table",
        )
    for paper_id, title in zip(ids, frame["Title"]):
        require(
            normalize_title(title) == title_by_id[int(paper_id)],
            f"{label} title does not match canonical Paper_ID={paper_id}",
        )


def main() -> None:
    repro = REPO / "analysis" / "reproducibility"
    analysis = REPO / "analysis" / "review_20260803"

    data = pd.read_csv(REPO / "data" / "data-clean.csv")
    contract = pd.read_csv(REPO / "data" / "included_study_order.csv")
    screening = pd.read_csv(repro / "screening_log_183.csv")
    assignments = pd.read_csv(repro / "included_studies_assignments_48.csv")
    manifest = json.loads((repro / "source_manifest.json").read_text(encoding="utf-8"))
    public_manifest = json.loads((REPO / "data" / "public_release_manifest.json").read_text(encoding="utf-8"))
    analysis_manifest = json.loads((analysis / "analysis_manifest.json").read_text(encoding="utf-8"))
    quality = pd.read_csv(analysis / "analysis_quality_summary_rerun.csv")
    sensitivity = pd.read_csv(analysis / "analysis_sensitivity_primary_sr.csv")
    dataset_characterization = pd.read_csv(analysis / "table_dataset_characterization.csv")
    metric_suitability = pd.read_csv(analysis / "analysis_psnr_ssim_metric_suitability.csv")
    temporal_primary = pd.read_csv(REPO / "tables" / "analysis_temporal_trends.csv")
    temporal_preliminary = pd.read_csv(REPO / "tables" / "analysis_temporal_trends_2025_preliminary.csv")
    fleiss_summary = pd.read_csv(REPO / "tables" / "analysis_fleiss_kappa_summary.csv")
    fleiss_item_agreement = pd.read_csv(REPO / "tables" / "analysis_fleiss_kappa_item_agreement.csv")
    weighted_summary = pd.read_csv(REPO / "tables" / "analysis_weighted_kappa_summary.csv")
    weighted_item_agreement = pd.read_csv(REPO / "tables" / "analysis_weighted_kappa_item_agreement.csv")
    icc_summary = pd.read_csv(REPO / "tables" / "analysis_icc_summary.csv")
    tr_weighting = pd.read_csv(analysis / "tr_weighting_sensitivity_20260804" / "analysis_tr_weighting_sensitivity.csv")
    tr_primary_leave_one_out = pd.read_csv(analysis / "tr_weighting_sensitivity_20260804" / "analysis_tr_primary_leave_one_out.csv")
    ground_truth_summary = pd.read_csv(analysis / "ground_truth_metric_audit_20260804" / "ground_truth_metric_audit_summary.csv")
    rf_robustness = pd.read_csv(analysis / "random_forest_robustness_20260804" / "rf_repeated_cv_summary.csv")

    require(
        len(contract) == 48
        and contract["Paper_ID"].tolist() == list(range(1, 49))
        and contract["Title"].notna().all()
        and contract["DOI"].notna().all(),
        "canonical study-order contract is not a complete 1-48 title/DOI mapping",
    )
    title_by_id = dict(zip(contract["Paper_ID"].astype(int), contract["Title"].map(normalize_title)))
    require(len(data) == 48, f"data-clean.csv has {len(data)} rows, expected 48")
    require_canonical_identity(data, "data/data-clean.csv", title_by_id)
    require(
        data.loc[data["Paper_ID"] == 24, "Title"].iloc[0]
        == "Pushing the limits of low-cost ultra-low-field MRI by dual-acquisition deep learning 3D superresolution",
        "Paper_ID=24 is not the canonical Pushing the limits study",
    )
    require(len(screening) == 183, f"screening log has {len(screening)} rows, expected 183")
    require((screening["Status"].str.casefold() == "included").sum() == 48, "included screening count is not 48")
    require((screening["Status"].str.casefold() == "excluded").sum() == 135, "excluded screening count is not 135")
    require(len(assignments) == 48 and assignments["Paper_ID"].nunique() == 48, "assignment mapping is not one-to-one")
    require(set(assignments["Paper_ID"].astype(int)) == set(range(1, 49)), "assignment mapping is not keyed 1-48")
    require(public_manifest["fleiss_kappa_status"] == "aggregate_summary_published_private_input", "Fleiss kappa release status is not current")
    require(analysis_manifest["fleiss_kappa"]["status"] == "not_run_without_private_input", "public core analysis must not require private ratings")
    require(analysis_manifest["fleiss_kappa"]["calculation_performed"] is False, "public core analysis must not calculate Fleiss kappa")
    require(fleiss_summary["Analysis"].tolist() == ["LMIC_Relevance_Score", "TR_Score"], "Fleiss summary analyses are incomplete")
    require((fleiss_summary["Items"] == 48).all() and (fleiss_summary["Raters"] == 11).all(), "Fleiss summary dimensions are invalid")
    require(fleiss_summary["Fleiss_kappa"].between(-1, 1).all(), "Fleiss kappa values are invalid")
    require(len(fleiss_item_agreement) == 96, "Fleiss item agreement output should contain 96 rows")
    require_canonical_identity(fleiss_item_agreement, "Fleiss item agreement", title_by_id)
    require(
        set(weighted_summary["Analysis"]) == {"LMIC_Relevance_Score", "TR_Score"}
        and set(weighted_summary["Weighting"]) == {"linear", "quadratic"},
        "weighted kappa summary analyses are incomplete",
    )
    require(
        (weighted_summary["Items"] == 48).all()
        and (weighted_summary["Raters"] == 11).all()
        and weighted_summary["Weighted_Fleiss_kappa"].between(-1, 1).all(),
        "weighted kappa summary dimensions or values are invalid",
    )
    require(len(weighted_item_agreement) == 192, "weighted item agreement output should contain 192 rows")
    require_canonical_identity(weighted_item_agreement, "weighted item agreement", title_by_id)
    require(
        not any("Reviewer" in column or "Rating" in column for column in weighted_summary.columns)
        and not any("Reviewer" in column or "Rating" in column for column in weighted_item_agreement.columns),
        "weighted kappa outputs expose reviewer-level fields",
    )
    require(
        icc_summary["Analysis"].tolist() == ["LMIC_Relevance_Score", "TR_Score"]
        and (icc_summary["Items"] == 48).all()
        and (icc_summary["Raters"] == 11).all(),
        "ICC summary dimensions are invalid",
    )
    require(
        icc_summary["ICC_2_1_absolute_agreement"].between(-1, 1).all()
        and icc_summary["ICC_2_k_absolute_agreement"].between(-1, 1).all()
        and not any("Reviewer" in column or "Rating" in column for column in icc_summary.columns),
        "ICC output is invalid or exposes reviewer-level fields",
    )

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
    require_canonical_identity(dataset_characterization, "dataset characterization", title_by_id)
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
    require_canonical_identity(metric_suitability, "metric suitability", title_by_id)
    require(metric_suitability["Paper_ID"].nunique() == 48, "metric suitability Paper_ID values are not unique")
    require(
        set(metric_suitability["PSNR_SSIM_Comparison_Eligibility"]).issubset(
            {"Eligible", "Not eligible", "Not reported"}
        ),
        "metric suitability uses an unexpected eligibility value",
    )
    require("Field_Manual_Review" not in dataset_characterization.columns, "retired manual-review label remains in dataset characterization")
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
        analysis / "analysis_field_pair_ground_truth.csv",
        analysis / "analysis_unknown_audit.csv",
        analysis / "tr_weighting_sensitivity_20260804" / "tr_weighting_study_scores.csv",
        analysis / "tr_weighting_sensitivity_20260804" / "analysis_tr_primary_leave_one_out.csv",
        analysis / "ground_truth_metric_audit_20260804" / "ground_truth_metric_audit_metric_studies.csv",
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
        "fleiss_kappa": {
            "LMIC_Relevance_Score": float(fleiss_summary.loc[fleiss_summary["Analysis"] == "LMIC_Relevance_Score", "Fleiss_kappa"].iloc[0]),
            "TR_Score": float(fleiss_summary.loc[fleiss_summary["Analysis"] == "TR_Score", "Fleiss_kappa"].iloc[0]),
            "raw_ratings_included": False,
        },
        "weighted_kappa": {
            "LMIC_Relevance_Score_linear": float(weighted_summary.loc[(weighted_summary["Analysis"] == "LMIC_Relevance_Score") & (weighted_summary["Weighting"] == "linear"), "Weighted_Fleiss_kappa"].iloc[0]),
            "LMIC_Relevance_Score_quadratic": float(weighted_summary.loc[(weighted_summary["Analysis"] == "LMIC_Relevance_Score") & (weighted_summary["Weighting"] == "quadratic"), "Weighted_Fleiss_kappa"].iloc[0]),
            "TR_Score_linear": float(weighted_summary.loc[(weighted_summary["Analysis"] == "TR_Score") & (weighted_summary["Weighting"] == "linear"), "Weighted_Fleiss_kappa"].iloc[0]),
            "TR_Score_quadratic": float(weighted_summary.loc[(weighted_summary["Analysis"] == "TR_Score") & (weighted_summary["Weighting"] == "quadratic"), "Weighted_Fleiss_kappa"].iloc[0]),
            "raw_ratings_included": False,
        },
        "icc": {
            "LMIC_Relevance_Score_ICC_2_1": float(icc_summary.loc[icc_summary["Analysis"] == "LMIC_Relevance_Score", "ICC_2_1_absolute_agreement"].iloc[0]),
            "LMIC_Relevance_Score_ICC_2_k": float(icc_summary.loc[icc_summary["Analysis"] == "LMIC_Relevance_Score", "ICC_2_k_absolute_agreement"].iloc[0]),
            "TR_Score_ICC_2_1": float(icc_summary.loc[icc_summary["Analysis"] == "TR_Score", "ICC_2_1_absolute_agreement"].iloc[0]),
            "TR_Score_ICC_2_k": float(icc_summary.loc[icc_summary["Analysis"] == "TR_Score", "ICC_2_k_absolute_agreement"].iloc[0]),
            "raw_ratings_included": False,
        },
        "status": "PASS",
    }
    output = repro / "verification_20260803.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
