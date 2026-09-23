from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))

from align_mri_scientometric_export import align_export, normalize_world_bank_group  # noqa: E402


def _source_with_original_form_extras() -> pd.DataFrame:
    contract = pd.read_csv(REPO / "data" / "included_study_order.csv", dtype=str)
    source = pd.read_csv(REPO / "data" / "data-clean.csv", dtype=str)
    source = source[["Paper_ID", "DOI", "Title", "Year"]].copy()
    preprint = source["DOI"].eq("10.3389/fneur.2024.1339223")
    source.loc[preprint, "DOI"] = "10.1101/2024.01.05.24300892"

    form = pd.read_csv(REPO / "data" / "reviewer_scoring_order.csv", dtype=str)
    excluded = form.loc[
        form["Include_In_Final_Corpus"].str.casefold().isin({"false", "0", "no"}),
        ["Form_Paper_ID", "DOI", "Title"],
    ].rename(columns={"Form_Paper_ID": "Paper_ID"})
    excluded["Year"] = "2023"
    return pd.concat([source, excluded], ignore_index=True)


def test_scientometric_rows_align_by_doi_and_resolve_published_preprint_alias(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "aligned.csv"
    manifest_path = tmp_path / "manifest.json"
    _source_with_original_form_extras().to_csv(source, index=False)

    manifest = align_export(
        source,
        output,
        REPO / "data" / "included_study_order.csv",
        manifest_path,
    )

    aligned = pd.read_csv(output, dtype=str)
    canonical = pd.read_csv(REPO / "data" / "included_study_order.csv", dtype=str)
    assert aligned["Paper_ID"].astype(int).tolist() == list(range(1, 46))
    assert aligned["DOI"].str.casefold().tolist() == canonical["DOI"].str.casefold().tolist()
    assert aligned["Title"].tolist() == canonical["Title"].tolist()
    assert manifest["source_rows"] == 48
    assert manifest["final_rows"] == 45
    assert manifest["excluded_from_final_export"] == 3
    assert manifest["doi_aliases_applied"][0]["source_doi"] == "10.1101/2024.01.05.24300892"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "PASS"

    rerun_manifest = align_export(
        output,
        output,
        REPO / "data" / "included_study_order.csv",
        manifest_path,
    )
    assert rerun_manifest["source_rows"] == 45
    assert rerun_manifest["source_acquisition_rows"] == 48
    assert rerun_manifest["excluded_from_final_export_total"] == 3


def test_scientometric_alignment_fails_if_final_doi_is_missing(tmp_path):
    source = _source_with_original_form_extras()
    last_final_doi = pd.read_csv(REPO / "data" / "included_study_order.csv").iloc[-1]["DOI"]
    source = source.loc[source["DOI"].str.casefold() != str(last_final_doi).casefold()]
    source_path = tmp_path / "incomplete.csv"
    source.to_csv(source_path, index=False)

    with pytest.raises(ValueError, match="missing .* final-corpus DOIs"):
        align_export(
            source_path,
            tmp_path / "should-not-exist.csv",
            REPO / "data" / "included_study_order.csv",
            tmp_path / "manifest.json",
        )
    assert not (tmp_path / "should-not-exist.csv").exists()


@pytest.mark.parametrize(
    ("legacy_code", "canonical_code"),
    [("LMIC", "LMC"), ("UMIC", "UMC"), ("HIC", "HIC"), ("UNKNOWN", "UNKNOWN")],
)
def test_world_bank_income_groups_use_official_abbreviations(legacy_code, canonical_code):
    assert normalize_world_bank_group(legacy_code) == canonical_code


def test_aligned_export_normalizes_income_group_labels_without_imputing_unknowns(tmp_path):
    output = tmp_path / "aligned.csv"
    align_export(
        REPO / "tables" / "mri_scientometric_results.csv",
        output,
        REPO / "data" / "included_study_order.csv",
        tmp_path / "manifest.json",
    )
    aligned = pd.read_csv(output, dtype=str)

    assert aligned["First_Author_WB_Group_Current"].value_counts().to_dict() == {
        "HIC": 26,
        "UMC": 8,
        "UNKNOWN": 6,
        "LMC": 5,
    }
    assert not aligned["First_Author_WB_Group_Current"].isin({"LMIC", "UMIC"}).any()
