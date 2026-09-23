"""Offline validation of the final MRI-LMICs reproducibility package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalize_identity(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.casefold())).strip()


def normalized_doi(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        text = text.removeprefix(prefix)
    return text.split("?", 1)[0].rstrip("/ ")


def verify_identity(frame: pd.DataFrame, contract: pd.DataFrame, label: str) -> None:
    require({"Paper_ID", "Title", "DOI"}.issubset(frame.columns), f"{label} lacks identity columns")
    require(frame["Paper_ID"].is_unique, f"{label} has duplicate Paper_ID values")
    expected_ids = contract["Paper_ID"].astype(int).tolist()
    actual_ids = pd.to_numeric(frame["Paper_ID"], errors="raise").astype(int).tolist()
    require(actual_ids == expected_ids, f"{label} does not match canonical 1-{len(contract)} order")
    require(
        frame["Title"].map(normalize_identity).tolist()
        == contract["Title"].map(normalize_identity).tolist(),
        f"{label} titles do not align with the canonical contract",
    )
    require(
        frame["DOI"].map(normalized_doi).tolist()
        == contract["DOI"].map(normalized_doi).tolist(),
        f"{label} DOIs do not align with the canonical contract",
    )


def sha256_utf8_lf(path: Path) -> str:
    value = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    from review_metrics import build_analysis, load_data

    data_dir = REPO / "data"
    tables_dir = REPO / "tables"
    analysis_dir = REPO / "analysis" / "review_20260803"
    repro_dir = REPO / "analysis" / "reproducibility"

    form = pd.read_csv(data_dir / "reviewer_scoring_order.csv")
    contract = pd.read_csv(data_dir / "included_study_order.csv")
    data = pd.read_csv(data_dir / "data-clean.csv")
    exclusions = pd.read_csv(data_dir / "post_extraction_exclusions.csv")
    require(len(form) == 48, "the reviewer scoring form must retain all 48 scored records")
    require(form["Form_Paper_ID"].astype(int).tolist() == list(range(1, 49)), "form IDs must remain 1-48")
    include = form["Include_In_Final_Corpus"].astype(str).str.casefold().isin({"true", "1", "yes"})
    eligible = form.loc[include].sort_values("Final_Paper_ID").reset_index(drop=True)
    require(len(contract) == 45 and contract["Paper_ID"].astype(int).tolist() == list(range(1, 46)), "final canonical contract must be contiguous 1-45")
    require(len(data) == len(contract), "canonical data and study-order contract row counts differ")
    verify_identity(data, contract, "data/data-clean.csv")
    verify_identity(eligible.rename(columns={"Final_Paper_ID": "Paper_ID"}), contract, "eligible scoring-form mapping")
    require(
        data["DOI"].map(normalized_doi).tolist() == eligible["DOI"].map(normalized_doi).tolist(),
        "canonical data are not aligned to the eligible scoring-form records",
    )
    require(len(exclusions) == 11, "expected 11 documented post-extraction exclusions")
    require(
        exclusions["Exclusion_Category"].value_counts().to_dict()
        == {"Not MRI modality": 4, "Review/survey only": 3, "Duplicate": 3, "No AI/DL method": 1},
        "post-extraction exclusion categories do not match the documented evidence",
    )
    require(int(include.sum()) == 45, "scoring order must identify exactly 45 eligible studies")
    form_source_ids = pd.to_numeric(exclusions["Source_Form_Paper_ID"], errors="coerce")
    pre_scoring_exclusions = exclusions.loc[form_source_ids.isna()]
    post_scoring_exclusions = exclusions.loc[form_source_ids.notna()]
    require(len(pre_scoring_exclusions) == 8, "eight extraction records should be excluded before the 48-study scoring form")
    require(len(post_scoring_exclusions) == 3, "three records should be excluded during final post-scoring eligibility reconciliation")
    require(len(data) + len(exclusions) == 56, "structured-extraction count does not reconcile to the eligible corpus plus exclusions")
    require(len(form) == len(data) + len(post_scoring_exclusions), "the 48-study scoring form does not reconcile with final eligibility")

    field = pd.read_csv(data_dir / "field_characterization_evidence.csv")
    dataset_evidence = pd.read_csv(data_dir / "dataset_characterization_evidence.csv")
    tr_evidence = pd.read_csv(data_dir / "tr_criteria_evidence.csv")
    scope_evidence = pd.read_csv(data_dir / "primary_sr_scope_evidence.csv")
    for name, frame in (
        ("field evidence", field),
        ("dataset evidence", dataset_evidence),
        ("TR evidence", tr_evidence),
        ("primary SR scope evidence", scope_evidence),
    ):
        verify_identity(frame, contract, name)

    analysis = build_analysis(load_data(data_dir / "data-clean.csv"))
    promoted = {
        "analysis_sensitivity_primary_sr.csv": analysis["sensitivity"],
        "analysis_lmic_tr_correlation.csv": analysis["correlation"],
        "table_dataset_characterization.csv": analysis["dataset_characterization"],
        "analysis_psnr_ssim_metric_suitability.csv": analysis["metric_suitability"],
        "analysis_translational_readiness.csv": analysis["tr"],
        "analysis_tr_hardware_verification.csv": analysis["hardware_verification"],
    }
    for filename, expected in promoted.items():
        current = pd.read_csv(tables_dir / filename)
        # The sensitivity and correlation outputs are cohort-level summaries,
        # not one-row-per-study tables. The verifier checks their cohort
        # sizes below and their schemas against the regenerated analyses.
        if filename not in {
            "analysis_sensitivity_primary_sr.csv",
            "analysis_lmic_tr_correlation.csv",
        }:
            verify_identity(current, contract, filename)
        require(list(current.columns) == list(expected.columns), f"{filename} schema differs from regenerated analysis")
        require(len(current) == len(expected), f"{filename} row count differs from regenerated analysis")

    sensitivity = pd.read_csv(tables_dir / "analysis_sensitivity_primary_sr.csv")
    correlation = pd.read_csv(tables_dir / "analysis_lmic_tr_correlation.csv")
    require(sensitivity["N"].astype(int).tolist() == [45, 24, 22], "SR sensitivity cohort sizes are not 45/24/22")
    require(correlation["n"].astype(int).tolist() == [45, 24, 22], "Spearman cohort sizes are not 45/24/22")
    for col in ("permutations", "bootstrap_replicates"):
        require((correlation[col] == 10_000).all(), f"Spearman {col} must be 10,000 for every cohort")
    require((correlation["rank_method"] == "average").all(), "Spearman ties must use average ranks")

    consensus = pd.read_csv(tables_dir / "analysis_lmic_tr_correlation_reviewer_consensus.csv")
    require(len(consensus) == 1 and int(consensus.loc[0, "n"]) == 45, "reviewer-median sensitivity must use 45 eligible studies")
    require(int(consensus.loc[0, "n_raters"]) == 11, "reviewer-median sensitivity must summarize 11 raters")
    require(not any("Reviewer" in col or "Rating" in col for col in consensus.columns), "reviewer-level data leaked to consensus summary")

    agreement_expectations = {
        "analysis_fleiss_kappa_summary.csv": (2, 48),
        "analysis_weighted_kappa_summary.csv": (4, 48),
        "analysis_icc_summary.csv": (2, 48),
    }
    for filename, (rows, items) in agreement_expectations.items():
        frame = pd.read_csv(tables_dir / filename)
        require(len(frame) == rows and (frame["Items"] == items).all(), f"{filename} dimensions are invalid")
        require((frame["Raters"] == 11).all(), f"{filename} must represent 11 raters")
        require(not any("Reviewer" in col or "Rating" in col for col in frame.columns), f"{filename} contains individual-rater fields")
    for filename, expected_rows in (
        ("analysis_fleiss_kappa_item_agreement.csv", 96),
        ("analysis_weighted_kappa_item_agreement.csv", 192),
    ):
        frame = pd.read_csv(tables_dir / filename)
        require(len(frame) == expected_rows, f"{filename} has an invalid number of aggregate item rows")
        require({"Scoring_Form_ID", "Title"}.issubset(frame.columns), f"{filename} lacks public scoring-form identity")
        require(frame["Scoring_Form_ID"].between(1, 48).all(), f"{filename} has out-of-range scoring-form IDs")
        require(not any("Reviewer" in col or "Rating" in col for col in frame.columns), f"{filename} exposes individual ratings")

    for filename in (
        "table_dataset_characterization.csv",
        "analysis_psnr_ssim_metric_suitability.csv",
        "analysis_translational_readiness.csv",
        "analysis_tr_hardware_verification.csv",
    ):
        verify_identity(pd.read_csv(tables_dir / filename), contract, filename)

    temporal = pd.read_csv(tables_dir / "analysis_temporal_trends.csv")
    temporal_2025 = pd.read_csv(tables_dir / "analysis_temporal_trends_2025_preliminary.csv")
    require(temporal["Year"].astype(int).tolist() == [2020, 2021, 2022, 2023, 2024], "primary trend must cover 2020-2024 only")
    require(temporal_2025["Year"].astype(int).tolist() == [2025], "2025 must be reported separately")
    require(temporal_2025["Status"].tolist() == ["Preliminary and incomplete"], "2025 scope must be marked preliminary")

    tr_weights = pd.read_csv(analysis_dir / "tr_weighting_sensitivity_20260804" / "analysis_tr_weighting_sensitivity.csv")
    tr_loo = pd.read_csv(analysis_dir / "tr_weighting_sensitivity_20260804" / "analysis_tr_primary_leave_one_out.csv")
    require(len(tr_weights) == 4, "four prespecified TR weighting schemes are required")
    require(len(tr_loo) == 45, "TR leave-one-out output must cover all 45 eligible studies")
    ground_truth_summary = pd.read_csv(analysis_dir / "ground_truth_metric_audit_20260804" / "ground_truth_metric_audit_summary.csv")
    require(not ground_truth_summary.empty, "ground-truth/metric audit summary is missing")
    rf = pd.read_csv(
        analysis_dir / "random_forest_robustness_20260804" / "rf_repeated_cv_summary.csv"
    )
    require((rf["Splits"] == 50).all(), "RF robustness must preserve 50 repeated held-out splits")
    public_rf = pd.read_csv(tables_dir / "analysis_random_forest_robustness_summary.csv")
    require((public_rf["N_Studies"] == 45).all(), "public RF summary must cover all 45 eligible studies")
    require((public_rf["Resampling_Splits"] == 50).all(), "public RF summary must cover all 50 held-out splits")
    require((public_rf["Seed"] == 42).all(), "public RF summary must retain seed 42")
    for _, row in rf.iterrows():
        public_row = public_rf.loc[public_rf["Model"] == row["Model"]]
        require(len(public_row) == 1, f"public RF summary is missing model {row['Model']}")
        public_row = public_row.iloc[0]
        for column in ("MAE_Mean", "MAE_SD", "R2_Mean", "R2_SD"):
            require(abs(float(public_row[column]) - float(row[column])) < 1e-12,
                    f"public RF summary disagrees with reproducibility output for {row['Model']} {column}")

    public_manifest = json.loads((data_dir / "public_release_manifest.json").read_text(encoding="utf-8"))
    corpus_entry = public_manifest["tracked_public_corpus"]
    require(corpus_entry["rows"] == 45 and corpus_entry["logical_path"] == "data/data-clean.csv", "public corpus manifest has stale size or path")
    require(corpus_entry["sha256"] == sha256_utf8_lf(data_dir / "data-clean.csv"), "public corpus hash does not match")
    evidence_manifest = public_manifest["tracked_public_evidence"]
    for key, path, frame in (
        ("field_characterization", data_dir / "field_characterization_evidence.csv", field),
        ("dataset_characterization", data_dir / "dataset_characterization_evidence.csv", dataset_evidence),
        ("primary_sr_scope", data_dir / "primary_sr_scope_evidence.csv", scope_evidence),
    ):
        entry = evidence_manifest[key]
        require(entry["rows"] == len(frame), f"manifest row count is stale for {key}")
        require(entry["sha256"] == sha256_utf8_lf(path), f"manifest hash is stale for {key}")

    identity_manifest = public_manifest["study_identity_contracts"]
    for key, relative_path, expected_rows in (
        ("included_study_order", "included_study_order.csv", 45),
        ("reviewer_scoring_order", "reviewer_scoring_order.csv", 48),
        ("post_extraction_exclusions", "post_extraction_exclusions.csv", 11),
    ):
        path = data_dir / relative_path
        entry = identity_manifest[key]
        frame = pd.read_csv(path)
        require(entry["logical_path"] == f"data/{relative_path}",
                f"manifest path is stale for {key}")
        require(entry["rows"] == expected_rows == len(frame),
                f"manifest row count is stale for {key}")
        require(entry["sha256"] == sha256_utf8_lf(path),
                f"manifest hash is stale for {key}")

    output_paths = [
        REPO / "figures" / "main" / "png" / f"fig{i}_{name}.png"
        for i, name in ((1, "year_distribution"), (2, "architecture_distribution"),
                        (3, "performance_comparison"), (4, "lmic_translational_gap"),
                        (5, "field_strength_application"), (6, "translational_roadmap"))
    ] + [
        REPO / "figures" / "supplementary" / "png" / f"figS{i}_{name}.png"
        for i, name in ((1, "temporal_trends"), (2, "prisma_flow"), (3, "reviewer_score_distributions"))
    ]
    require(all(path.exists() for path in output_paths), "one or more current figure outputs are missing")

    quality = pd.read_csv(analysis_dir / "analysis_quality_summary_rerun.csv")
    total_quality = quality.loc[quality["Domain"] == "Total Quality"].iloc[0]
    canonical_all = correlation.loc[correlation["Cohort"] == "All included studies"].iloc[0]
    consensus_all = consensus.iloc[0]
    result = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "network_calls_made": False,
        "github_modified": False,
        "screening_flow": {
            "identified": 183,
            "entered_structured_extraction": int(len(data) + len(exclusions)),
            "not_entered_structured_extraction": int(183 - len(data) - len(exclusions)),
            "excluded_before_all_author_scoring": int(len(pre_scoring_exclusions)),
            "all_author_scoring_form_records": int(len(form)),
            "excluded_after_scoring_eligibility_reconciliation": int(len(post_scoring_exclusions)),
            "post_extraction_exclusions": 11,
            "included": 45,
            "stage_specific_pre_extraction_counts_reconstructed": False,
        },
        "scored_form_records": 48,
        "included_studies": 45,
        "sr_primary_sensitivity_n": 24,
        "sr_pure_or_denoising_sensitivity_n": 22,
        "quality_mean": float(total_quality["Mean"]),
        "quality_sample_sd": float(total_quality["Std"]),
        "lmic_tr_spearman": {
            "canonical": float(canonical_all["rho"]),
            "reviewer_median_sensitivity": float(consensus_all["rho"]),
            "raw_ratings_included": False,
        },
        "fleiss_kappa": dict(zip(
            pd.read_csv(tables_dir / "analysis_fleiss_kappa_summary.csv")["Analysis"],
            pd.read_csv(tables_dir / "analysis_fleiss_kappa_summary.csv")["Fleiss_kappa"].astype(float),
        )),
        "reviewer_individual_scores_included": False,
        "raw_ratings_included": False,
    }
    output = repro_dir / "verification_20260922.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
