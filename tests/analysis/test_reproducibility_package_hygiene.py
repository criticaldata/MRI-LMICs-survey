from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_active_package_excludes_retired_template_and_calibration_artifacts():
    """Only the current reviewer template and pending-IRR workflow stay active."""
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
        "extract_ground_truth_from_cached_fulltext.py",
        "run_random_forest_robustness_20260804.py",
        "analysis_temporal_trends.py",
        "fig4_performance_comparison.py",
        "figS1_temporal_trends.py",
        "verify_reproducibility.py",
        "verify_mri_scientometric_reproducibility.py",
        "-m pytest -q",
    ]:
        assert command in text
    assert '"--promote"' in text

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "run_full_reproducibility_pipeline.ps1" in readme
    assert "34 tests successfully" in readme
    assert "29 tests" not in readme


def test_public_scientometric_release_contains_only_results_and_coverage():
    """Public scientometrics are flat results plus source coverage, not raw caches."""
    public_results = REPO / "tables" / "mri_scientometric_results.csv"
    public_coverage = REPO / "tables" / "mri_scientometric_source_coverage.csv"
    assert public_results.exists()
    assert public_coverage.exists()


def test_ground_truth_extraction_uses_versioned_doi_results_not_private_role_audit():
    """A fresh public clone must not require local scientometric role-audit data."""
    script = REPO / "scripts" / "analysis" / "extract_ground_truth_from_cached_fulltext.py"
    text = script.read_text(encoding="utf-8")
    assert "mri_scientometric_results.csv" in text
    assert "PUBLIC_SCIENTOMETRIC_RESULTS" in text
    assert "multisource_role_audit.csv" not in text
