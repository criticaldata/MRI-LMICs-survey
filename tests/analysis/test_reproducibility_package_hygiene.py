from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[2]


def test_public_data_contract_files_are_not_ignored():
    """A fresh public clone must receive every source contract used by the pipeline."""
    required_public_data = [
        "data/data-clean.csv",
        "data/dataset_characterization_evidence.csv",
        "data/field_characterization_evidence.csv",
        "data/included_study_order.csv",
        "data/post_extraction_exclusions.csv",
        "data/primary_sr_scope_evidence.csv",
        "data/public_release_manifest.json",
        "data/reviewer_scoring_order.csv",
        "data/tr_criteria_evidence.csv",
    ]

    for relative_path in required_public_data:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", relative_path],
            cwd=REPO,
            check=False,
        )
        assert result.returncode == 1, f"Public pipeline input is ignored: {relative_path}"


def test_processing_logs_and_temporary_outputs_are_not_versioned():
    """Timestamped logs belong to the local run, not the public analysis package."""
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "06_processing_outputs/" in ignored
    tracked = subprocess.run(
        ["git", "ls-files", "06_processing_outputs/"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert not tracked.stdout.strip()


def test_active_package_excludes_retired_template_and_calibration_artifacts():
    """The public package excludes raw ratings and historical calibration."""
    retired_paths = [
        REPO / "analysis" / "reproducibility" / "build_reviewer_scoring_workbook.mjs",
        REPO / "tables" / "module3_fleiss_kappa_results.csv",
        REPO / "tables" / "analysis_calibration_set.csv",
        REPO / "scripts" / "tables" / "analysis_reviewer_bias.py",
        REPO / "tables" / "analysis_reviewer_bias_summary.csv",
        REPO / "tables" / "analysis_lmic_bias_corrected.csv",
        REPO / "data" / "fleiss_kappa_matrix.csv",
    ]
    assert all(not path.exists() for path in retired_paths)

    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "analysis/reproducibility/reviewer_scoring/TR_Criteria.png" in ignored

    # Historical calibration is private provenance.  It is deliberately not a
    # public-repository dependency and must not be required by a fresh clone.


def test_documented_master_runner_regenerates_and_verifies_complete_package():
    """The documented entry point includes promotion, figures, verification, and tests."""
    runner = REPO / "scripts" / "analysis" / "run_full_reproducibility_pipeline.ps1"
    assert runner.exists()
    text = runner.read_text(encoding="utf-8")
    for command in [
        "run_reproducible_review_analysis.py",
        "run_tr_weighting_sensitivity.py",
        "build_metric_ground_truth_audit.py",
        "run_random_forest_robustness_20260804.py",
        "analysis_temporal_trends.py",
        "generate_all_figures.py",
        "figS3_reviewer_score_distributions.py",
        "verify_reproducibility.py",
        "verify_mri_scientometric_reproducibility.py",
        "-m pytest -q",
    ]:
        assert command in text
    assert '"--promote"' in text

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "run_full_reproducibility_pipeline.ps1" in readme
    assert "Fleiss' kappa" in readme
    assert "weighted multi-rater kappa" in readme
    assert "ICC" in readme
    assert "aggregate-only" in readme


def test_public_scientometric_release_contains_only_results_and_coverage():
    """Public scientometrics are flat results plus source coverage, not raw caches."""
    public_results = REPO / "tables" / "mri_scientometric_results.csv"
    public_coverage = REPO / "tables" / "mri_scientometric_source_coverage.csv"
    assert public_results.exists()
    assert public_coverage.exists()


def test_ground_truth_extraction_uses_the_public_full_text_evidence_layer():
    """A fresh public clone must not require local caches or role-audit data."""
    script = REPO / "scripts" / "analysis" / "build_metric_ground_truth_audit.py"
    text = script.read_text(encoding="utf-8")
    assert "dataset_characterization_evidence.csv" in text
    assert "multisource_role_audit.csv" not in text
    assert "europepmc" not in text.casefold()
