"""Prevent baselines, ablations, and sampling labels becoming study results."""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "figures"))
from mapper import load_data  # noqa: E402
from scripts.metric_extraction import (  # noqa: E402
    apply_metric_evidence,
    load_metric_evidence,
    parse_metric_value,
)

CPRO_DOI = "10.1109/tmi.2020.2974858"
SMIR_DOI = "10.1109/icmipe53131.2021.9698880"


def study(frame, doi):
    return frame.loc[frame["DOI"].str.casefold().eq(doi)].iloc[0]


@pytest.mark.parametrize("metric,want", [("PSNR", 35.140), ("SSIM", 0.961)])
def test_cpro_uses_main_proposed_result_not_first_baseline(metric, want):
    row = study(load_data(), CPRO_DOI)
    assert row[f"{metric}_Numeric"] == pytest.approx(want)


def test_smir_20_percent_ssim_is_not_missing_or_highest_condition():
    row = study(load_data(), SMIR_DOI)
    assert row["SSIM_Numeric"] == pytest.approx(0.86)
    assert pd.isna(row["PSNR_Numeric"])


def test_sampling_percentage_does_not_replace_a_psnr_range(tmp_path):
    raw = pd.read_csv(REPO / "data" / "data-clean.csv")
    index = raw.index[raw["Paper_ID"].eq(40)][0]
    raw.loc[index, "PSNR_Value"] = "20% sampling: 26.53-29.25 dB (average across datasets)"
    path = tmp_path / "data.csv"
    raw.to_csv(path, index=False)
    assert load_data(path).loc[index, "PSNR_Numeric"] == pytest.approx(26.53)


def test_raw_master_metric_text_remains_available():
    raw = pd.read_csv(REPO / "data" / "data-clean.csv")
    result = load_data()
    for column in ("PSNR_Value", "SSIM_Value"):
        pd.testing.assert_series_equal(result[column], raw[column].str.strip())


def test_keyed_evidence_beats_reordered_prose_and_best_ablation(tmp_path):
    raw = pd.read_csv(REPO / "data" / "data-clean.csv")
    index = raw.index[raw["DOI"].eq(CPRO_DOI)][0]
    raw.loc[index, "DOI"] = "https://doi.org/10.1109/TMI.2020.2974858"
    raw.loc[index, "PSNR_Value"] = "Best loss ablation: 38.513; baseline: 27.151"
    raw.loc[index, "SSIM_Value"] = "Best loss ablation: 0.976; baseline: 0.793"
    path = tmp_path / "data.csv"
    raw.to_csv(path, index=False)
    row = load_data(path).loc[index]
    assert row["PSNR_Numeric"] == pytest.approx(35.140)
    assert row["SSIM_Numeric"] == pytest.approx(0.961)


def test_frozen_condition_series_retains_both_datasets_and_all_sampling_ratios():
    path = REPO / "data" / "performance_metric_evidence.csv"
    assert path.exists(), "Condition-specific source evidence must be checked in"
    evidence = pd.read_csv(path)
    cpro = evidence.loc[evidence["DOI"].eq(CPRO_DOI)]
    assert cpro.groupby("Dataset")["Metric"].apply(set).to_dict() == {
        "IXI": {"PSNR", "SSIM"}, "NAMIC": {"PSNR", "SSIM"}
    }
    assert cpro.loc[cpro["Dataset"].eq("NAMIC"), "Value"].tolist() == [30.942, 0.953]
    smir = evidence.loc[evidence["DOI"].eq(SMIR_DOI) & evidence["Metric"].eq("SSIM")]
    assert smir["Condition"].tolist() == [
        "10% radial k-space sampling", "20% radial k-space sampling",
        "30% radial k-space sampling", "40% radial k-space sampling",
        "50% radial k-space sampling",
    ]
    assert smir["Value"].tolist() == [0.72, 0.86, 0.87, 0.89, 0.91]
    assert smir.loc[smir["Is_Primary"], "Value"].tolist() == [0.86]


def test_selected_scalar_carries_condition_rule_and_range():
    row = study(load_data(), SMIR_DOI)
    assert "SSIM_Selection_Method" in row.index, "Selections need visible provenance"
    assert row["SSIM_Selection_Method"] == "doi_keyed_evidence"
    assert row["SSIM_Primary_Condition"] == "20% radial k-space sampling"
    assert row["SSIM_Evidence_Min"] == pytest.approx(0.72)
    assert row["SSIM_Evidence_Max"] == pytest.approx(0.91)
    assert "retrospective" in row["SSIM_Selection_Rule"].lower()


@pytest.mark.parametrize("text,metric,want", [
    ("Brain 3T (500 images): 0.9270. Cardiac (500 images): 0.9496.", "SSIM", 0.927),
    ("PSNR: 29.25.", "PSNR", 29.25),
    ("26.53-29.25 dB (average across datasets)", "PSNR", 26.53),
    ("20 percent sampling: 26.53-29.25 dB", "PSNR", 26.53),
    ("10%: .72; 20%: .86", "SSIM", 0.72),
    ("0.80-0.84 (average across datasets)", "SSIM", 0.80),
    ("SSIM=0", "SSIM", 0),
    ("SSIM=1.0", "SSIM", 1),
])
def test_fallback_is_metric_aware_but_does_not_maximize(text, metric, want):
    assert parse_metric_value(text, metric) == pytest.approx(want)


@pytest.mark.parametrize("text,metric", [
    (None, "SSIM"), ("Not reported. Paper uses MAE instead.", "PSNR"),
    ("10% sampling; SSIM not available", "SSIM"), ("SSIM=1.2", "SSIM"),
])
def test_missing_or_invalid_fallback_does_not_create_metrics(text, metric):
    assert pd.isna(parse_metric_value(text, metric))


def test_doi_not_paper_number_or_row_order_controls_override():
    raw = pd.read_csv(REPO / "data" / "data-clean.csv")
    inputs = raw.loc[raw["DOI"].isin([CPRO_DOI, SMIR_DOI])].iloc[::-1].copy()
    inputs["Paper_ID"] = [900, 901]
    inputs["SSIM_Value"] = "0.12 baseline"
    before = inputs.copy(deep=True)
    result = apply_metric_evidence(inputs)
    assert result["SSIM_Numeric"].tolist() == [0.86, 0.961]
    assert result["SSIM_Dataset"].tolist() == ["HCP T1", "IXI"]
    pd.testing.assert_frame_equal(inputs, before)


@pytest.mark.parametrize("mutation,message", [
    ("two_primaries", "exactly one primary"),
    ("no_primary", "exactly one primary"),
    ("duplicate", "duplicate condition"),
    ("bad_ssim", "SSIM must be"),
    ("baseline", "proposed_main"),
    ("missing_value", "reported status"),
    ("invented_psnr", "reported status"),
    ("missing_doi", "empty DOI"),
    ("missing_schema", "missing columns"),
])
def test_bad_evidence_fails_closed_instead_of_falling_back(tmp_path, mutation, message):
    evidence = pd.read_csv(REPO / "data" / "performance_metric_evidence.csv")
    if mutation == "two_primaries":
        evidence.loc[2, "Is_Primary"] = True
    elif mutation == "no_primary":
        evidence.loc[0, "Is_Primary"] = False
    elif mutation == "duplicate":
        evidence = pd.concat([evidence, evidence.iloc[[0]]], ignore_index=True)
    elif mutation == "bad_ssim":
        evidence.loc[1, "Value"] = 1.2
    elif mutation == "baseline":
        evidence.loc[0, "Result_Role"] = "baseline"
    elif mutation == "missing_value":
        evidence.loc[0, "Value"] = float("nan")
    elif mutation == "invented_psnr":
        evidence.loc[9, "Value"] = 20
    elif mutation == "missing_doi":
        evidence.loc[0, "DOI"] = ""
    elif mutation == "missing_schema":
        evidence = evidence.drop(columns="Condition")
    path = tmp_path / "evidence.csv"
    evidence.to_csv(path, index=False)
    with pytest.raises(ValueError, match=message):
        load_metric_evidence(path)


def test_missing_evidence_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_metric_evidence(tmp_path / "missing.csv")
