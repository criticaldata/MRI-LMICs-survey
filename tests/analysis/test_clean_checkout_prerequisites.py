"""Public checkout regressions; no local analysis cache or private ratings."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
import pytest


REPO = Path(__file__).resolve().parents[2]
RF_RELATIVE = Path("analysis/review_20260803/random_forest_robustness_20260804")


@pytest.fixture
def public_checkout(tmp_path):
    """Copy only versioned public inputs, never a developer's ignored cache."""
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", "scripts", "data", "tables", "figures"],
        cwd=REPO, check=True, capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    for relative in filter(None, tracked):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, target)
    assert not (tmp_path / "analysis").exists()
    return tmp_path


@pytest.fixture
def table5(public_checkout, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "clean_checkout_table5", REPO / "scripts/tables/table5_statistical_insights.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PROJECT_ROOT", public_checkout)
    return module


def run_verifier(public_checkout):
    return subprocess.run(
        [sys.executable, str(public_checkout / "scripts/analysis/verify_reproducibility.py")],
        cwd=public_checkout, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"}, timeout=180,
    )


def test_verifier_accepts_only_tracked_public_artifacts(public_checkout):
    result = run_verifier(public_checkout)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["included_studies"] == 45
    assert report["quality_mean"] == pytest.approx(4.133333333333334)
    assert report["lmic_tr_spearman"]["canonical"] == pytest.approx(-0.25773836252564347)
    assert report["raw_ratings_included"] is False
    assert report["verification_scope"] == "public artifacts and available local details"
    assert report["local_detail_outputs_checked"] == []
    assert not (public_checkout / "analysis/review_20260803").exists()


@pytest.mark.parametrize("stale_rf", [False, True])
def test_verifier_cross_checks_available_details(public_checkout, stale_rf):
    root = public_checkout / "analysis/review_20260803"
    for public, relative in (
        ("analysis_tr_weighting_sensitivity.csv", "tr_weighting_sensitivity_20260804/analysis_tr_weighting_sensitivity.csv"),
        ("analysis_quality_summary.csv", "analysis_quality_summary_rerun.csv"),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(public_checkout / "tables" / public, target)
    rf = pd.read_csv(public_checkout / "tables/analysis_random_forest_robustness_summary.csv")
    rf = rf[["Model", "MAE_Mean", "MAE_SD", "R2_Mean", "R2_SD", "Resampling_Splits"]]
    rf = rf.rename(columns={"Resampling_Splits": "Splits"})
    if stale_rf:
        rf.loc[0, "MAE_Mean"] += 0.1
    target = public_checkout / RF_RELATIVE / "rf_repeated_cv_summary.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    rf.to_csv(target, index=False)
    result = run_verifier(public_checkout)
    if stale_rf:
        assert result.returncode != 0
        assert "public RF summary disagrees" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert set(report["local_detail_outputs_checked"]) == {
            "analysis/review_20260803/tr_weighting_sensitivity_20260804/analysis_tr_weighting_sensitivity.csv",
            "analysis/review_20260803/random_forest_robustness_20260804/rf_repeated_cv_summary.csv",
            "analysis/review_20260803/analysis_quality_summary_rerun.csv",
        }


def test_table5_uses_real_public_heldout_permutations_without_cache(table5, public_checkout):
    path = public_checkout / "tables/table5a_random_forest_features.csv"
    expected = pd.read_csv(path)
    table5.create_table5()
    pd.testing.assert_frame_equal(pd.read_csv(path), expected)
    assert expected.loc[0, "Feature"] == "Has_Clinical_Validation"
    assert expected.loc[0, "Permutation_MAE_Increase_Mean"] == pytest.approx(0.0418592946673459)
    assert (expected["Splits"] == 50).all()
    assert not (public_checkout / RF_RELATIVE).exists()
    agreement = pd.read_csv(public_checkout / "tables/table5c_reviewer_agreement_aggregate.csv")
    assert len(agreement) == 2
    assert agreement["Items"].tolist() == [48, 48]
    assert agreement["Raters"].tolist() == [11, 11]


def test_table5_prefers_newly_generated_details(table5, public_checkout):
    # A real analysis fixture in reversed row order must still be sorted.
    expected = pd.read_csv(REPO / "tables/table5a_random_forest_features.csv")
    details = public_checkout / RF_RELATIVE / "rf_heldout_permutation_summary.csv"
    details.parent.mkdir(parents=True)
    expected.iloc[::-1].to_csv(details, index=False)
    # The stale promoted copy must not be used when fresh details exist.
    (public_checkout / "tables/table5a_random_forest_features.csv").unlink()
    table5.create_table5()
    pd.testing.assert_frame_equal(
        pd.read_csv(public_checkout / "tables/table5a_random_forest_features.csv")
        .sort_values("Feature").reset_index(drop=True),
        expected.sort_values("Feature").reset_index(drop=True),
    )


@pytest.mark.parametrize("problem", ["missing", "impurity", "incomplete", "wrong_splits", "nonfinite"])
def test_table5_does_not_invent_missing_permutation_results(table5, public_checkout, problem):
    path = public_checkout / "tables/table5a_random_forest_features.csv"
    frame = pd.read_csv(path)
    if problem == "missing":
        path.unlink()
    else:
        if problem == "impurity":
            frame = frame.rename(columns={"Permutation_MAE_Increase_Mean": "Importance"})
        elif problem == "incomplete":
            frame = frame.iloc[:-1]
        elif problem == "wrong_splits":
            frame.loc[0, "Splits"] = 49
        else:
            frame.loc[0, "Permutation_MAE_Increase_Mean"] = float("inf")
        frame.to_csv(path, index=False)
    before = path.read_bytes() if path.exists() else None
    with pytest.raises((FileNotFoundError, ValueError), match="run_random_forest_robustness_20260804.py"):
        table5.create_table5()
    assert (path.read_bytes() if path.exists() else None) == before


def test_table5_rejects_bad_details_instead_of_silently_using_public_copy(table5, public_checkout):
    details = public_checkout / RF_RELATIVE / "rf_heldout_permutation_summary.csv"
    details.parent.mkdir(parents=True)
    frame = pd.read_csv(REPO / "tables/table5a_random_forest_features.csv")
    frame.loc[0, "Splits"] = 1
    frame.to_csv(details, index=False)
    with pytest.raises(ValueError, match="run_random_forest_robustness_20260804.py"):
        table5.create_table5()
