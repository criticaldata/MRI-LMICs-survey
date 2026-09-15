"""Behavioral tests for canonical and reviewer-consensus LMIC--TR inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))

from review_metrics import build_analysis, load_data  # noqa: E402


CANONICAL_DATA = REPO / "data" / "data-clean.csv"
CANONICAL_CORRELATION = REPO / "tables" / "analysis_lmic_tr_correlation.csv"
CONSENSUS_CORRELATION = (
    REPO / "tables" / "analysis_lmic_tr_correlation_reviewer_consensus.csv"
)
CONSENSUS_RUNNER = (
    REPO
    / "scripts"
    / "analysis"
    / "statistical"
    / "run_lmic_tr_correlation_from_private_xlsx.py"
)
PUBLIC_MANIFEST = REPO / "data" / "public_release_manifest.json"

EXPECTED_ALL = {
    "n": 48,
    "rho": 0.40592288472740023,
    "p_permutation": 0.0032996700329967,
    "bootstrap_ci_2_5": 0.16392078177387287,
    "bootstrap_ci_97_5": 0.606534930261319,
}
EXPECTED_CONSENSUS = {
    "n": 48,
    "rho": -0.25769998006564165,
    "p_permutation": 0.0786921307869213,
    "bootstrap_ci_2_5": -0.5397196933433509,
    "bootstrap_ci_97_5": 0.03972313668026812,
}
INFERENCE_COLUMNS = {
    "n",
    "rho",
    "p_permutation",
    "permutations",
    "seed",
    "bootstrap_ci_2_5",
    "bootstrap_ci_97_5",
    "bootstrap_replicates",
    "bootstrap_seed",
    "rank_method",
}


def _canonical_titles() -> list[str]:
    return pd.read_csv(CANONICAL_DATA)["Title"].tolist()


def _write_workbook(
    path: Path,
    *,
    titles: list[str] | None = None,
    raters: int = 11,
    missing_score: tuple[int, int, str] | None = None,
    out_of_range: tuple[int, int, str] | None = None,
) -> None:
    titles = list(titles if titles is not None else _canonical_titles())
    workbook = Workbook()
    sheet = workbook.active
    header_one = [None, None, None]
    header_two = ["PAPER", "TITLE", "URL"]
    for index in range(raters):
        header_one.extend([f"Sensitive Reviewer {index + 1}", None])
        header_two.extend(["LMIC RELEVANCE SCORE (1-5)", "TR SCORE (0-5)"])
    sheet.append(header_one)
    sheet.append(header_two)

    for paper_id, title in enumerate(titles, start=1):
        row = [paper_id, title, ""]
        for reviewer in range(1, raters + 1):
            lmic = (paper_id - 1) % 5 + 1
            tr = (paper_id - 1) % 6
            if missing_score == (paper_id, reviewer, "LMIC"):
                lmic = None
            if missing_score == (paper_id, reviewer, "TR"):
                tr = None
            if out_of_range == (paper_id, reviewer, "LMIC"):
                lmic = 6
            if out_of_range == (paper_id, reviewer, "TR"):
                tr = -1
            row.extend([lmic, tr])
        sheet.append(row)
    workbook.save(path)


def _run_consensus(workbook: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CONSENSUS_RUNNER),
            "--input-xlsx",
            str(workbook),
            "--output-dir",
            str(output_dir),
            "--canonical-data",
            str(CANONICAL_DATA),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_canonical_correlation_has_expected_deterministic_inference():
    correlation = pd.read_csv(CANONICAL_CORRELATION)
    regenerated = build_analysis(load_data(CANONICAL_DATA))["correlation"]

    assert correlation["Cohort"].tolist() == [
        "All included studies",
        "SR primary strict (Pure SR, SR + Denoising, SR + Other)",
        "SR primary pure/denoising",
    ]
    assert INFERENCE_COLUMNS.issubset(correlation.columns)
    assert correlation["n"].tolist() == [48, 30, 23]
    assert (correlation["permutations"] == 10_000).all()
    assert (correlation["bootstrap_replicates"] == 10_000).all()
    assert (correlation["seed"] == 42).all()
    assert (correlation["bootstrap_seed"] == 42).all()
    assert (correlation["rank_method"] == "average").all()
    pd.testing.assert_frame_equal(
        regenerated, correlation, check_exact=False, rtol=0, atol=1e-15
    )

    all_studies = correlation.iloc[0]
    for column, expected in EXPECTED_ALL.items():
        assert all_studies[column] == pytest.approx(expected, abs=1e-15)


def test_reviewer_consensus_output_matches_approved_current_result():
    consensus = pd.read_csv(CONSENSUS_CORRELATION)

    assert len(consensus) == 1
    assert consensus.loc[0, "Cohort"] == "All included studies: reviewer median"
    assert INFERENCE_COLUMNS.issubset(consensus.columns)
    assert consensus.loc[0, "aggregation"] == "per-paper median of 11 complete raters"
    for column, expected in EXPECTED_CONSENSUS.items():
        assert consensus.loc[0, column] == pytest.approx(expected, abs=1e-15)
    assert consensus.loc[0, "permutations"] == 10_000
    assert consensus.loc[0, "bootstrap_replicates"] == 10_000
    assert consensus.loc[0, "seed"] == 42
    assert consensus.loc[0, "bootstrap_seed"] == 42
    assert consensus.loc[0, "rank_method"] == "average"


def test_public_manifest_hashes_are_platform_independent_utf8_lf():
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    entries = [manifest["tracked_public_corpus"], *manifest["analysis_outputs"].values()]

    for entry in entries:
        path = REPO / entry["logical_path"]
        normalized = (
            path.read_bytes()
            .decode("utf-8")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .encode("utf-8")
        )
        assert entry["sha256_normalization"] == "utf8_lf"
        assert entry["rows"] == len(pd.read_csv(path))
        assert entry["sha256"] == hashlib.sha256(normalized).hexdigest()


def test_general_reproducibility_verifier_reports_both_spearman_results():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "analysis" / "verify_reproducibility.py")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["lmic_tr_spearman"]["canonical"] == pytest.approx(
        EXPECTED_ALL["rho"], abs=1e-15
    )
    assert report["lmic_tr_spearman"]["reviewer_median_sensitivity"] == pytest.approx(
        EXPECTED_CONSENSUS["rho"], abs=1e-15
    )
    assert report["lmic_tr_spearman"]["raw_ratings_included"] is False


def test_private_runner_accepts_exact_48_title_order_and_writes_only_summary(tmp_path):
    private_input = tmp_path / "do-not-leak-private-ratings.xlsx"
    output_dir = tmp_path / "public-summary"
    _write_workbook(private_input)

    result = _run_consensus(private_input, output_dir)

    assert result.returncode == 0, result.stderr
    output = output_dir / CONSENSUS_CORRELATION.name
    summary = pd.read_csv(output)
    assert len(summary) == 1
    assert summary.loc[0, "n"] == 48
    assert summary.loc[0, "rho"] == pytest.approx(-0.023814705373955962, abs=1e-15)
    assert summary.loc[0, "aggregation"] == "per-paper median of 11 complete raters"
    assert INFERENCE_COLUMNS.issubset(summary.columns)

    public_text = output.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "sensitive reviewer",
        "do-not-leak",
        "input-xlsx",
        "private-ratings",
        "reviewer_1",
        "individual rating",
    ):
        assert forbidden not in public_text
    assert str(private_input) not in result.stdout


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("reordered", "Paper 24 title does not match canonical study order"),
        ("missing_title", "Paper 18 title does not match canonical study order"),
        ("missing_row", "Expected 48 papers plus two header rows"),
        ("ten_raters", "Expected 11 reviewer pairs"),
        ("missing_lmic", "Missing or non-numeric LMIC score"),
        ("missing_tr", "Missing or non-numeric TR score"),
        ("lmic_range", "LMIC scores must be integers from 1 to 5"),
        ("tr_range", "TR scores must be integers from 0 to 5"),
    ],
)
def test_private_runner_rejects_invalid_workbook_before_output(
    tmp_path, mutation, expected_error
):
    titles = _canonical_titles()
    raters = 11
    missing_score = None
    out_of_range = None
    if mutation == "reordered":
        titles[23], titles[24] = titles[24], titles[23]
    elif mutation == "missing_title":
        titles[17] = ""
    elif mutation == "missing_row":
        titles.pop()
    elif mutation == "ten_raters":
        raters = 10
    elif mutation == "missing_lmic":
        missing_score = (7, 4, "LMIC")
    elif mutation == "missing_tr":
        missing_score = (7, 4, "TR")
    elif mutation == "lmic_range":
        out_of_range = (7, 4, "LMIC")
    elif mutation == "tr_range":
        out_of_range = (7, 4, "TR")

    private_input = tmp_path / "invalid-private-ratings.xlsx"
    output_dir = tmp_path / "must-remain-empty"
    _write_workbook(
        private_input,
        titles=titles,
        raters=raters,
        missing_score=missing_score,
        out_of_range=out_of_range,
    )

    result = _run_consensus(private_input, output_dir)

    assert result.returncode != 0
    assert expected_error in result.stderr
    assert not (output_dir / CONSENSUS_CORRELATION.name).exists()


def _write_python_shim(path: Path) -> Path:
    shim = path / "record-python-invocations.cmd"
    shim.write_text(
        '@echo %*>> "%~dp0invocations.txt"\n@exit /b 0\n', encoding="utf-8"
    )
    return shim


def _run_pipeline(shim: Path, private_workbook: Path | None = None):
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REPO / "scripts" / "analysis" / "run_full_reproducibility_pipeline.ps1"),
        "-PythonPath",
        str(shim),
        "-RunDate",
        "20990101",
    ]
    if private_workbook is not None:
        command.extend(["-PrivateRatingsXlsx", str(private_workbook)])
    return subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=False
    )


def test_pipeline_keeps_public_only_mode_and_groups_all_private_analyses(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    public_shim = _write_python_shim(public_dir)

    public_result = _run_pipeline(public_shim)

    assert public_result.returncode == 0, public_result.stderr
    public_calls = (public_shim.parent / "invocations.txt").read_text(encoding="utf-8")
    assert "run_reproducible_review_analysis.py" in public_calls
    assert "run_lmic_tr_correlation_from_private_xlsx.py" not in public_calls

    private_dir = tmp_path / "private"
    private_dir.mkdir()
    private_shim = _write_python_shim(private_dir)
    private_workbook = private_dir / "do-not-print-private-workbook.xlsx"
    private_workbook.touch()

    private_result = _run_pipeline(private_shim, private_workbook)

    assert private_result.returncode == 0, private_result.stderr
    private_calls = (private_dir / "invocations.txt").read_text(encoding="utf-8")
    for script in (
        "run_fleiss_kappa_from_private_xlsx.py",
        "run_weighted_kappa_from_private_xlsx.py",
        "run_icc_from_private_xlsx.py",
        "run_lmic_tr_correlation_from_private_xlsx.py",
    ):
        assert script in private_calls
    assert str(private_workbook) not in private_result.stdout
