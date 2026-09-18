"""Regression tests for the public 48-study identity contract."""

import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
sys.path.insert(0, str(REPO / "scripts" / "analysis" / "statistical"))

from canonical_study_ids import normalize_doi, normalize_title, read_git_csv  # noqa: E402
from run_fleiss_kappa_from_private_xlsx import _read_matrix  # noqa: E402


EXPECTED_IDS = list(range(1, 49))
EXPECTED_PAPER_24_TITLE = (
    "Pushing the limits of low-cost ultra-low-field MRI by dual-acquisition "
    "deep learning 3D superresolution"
)


def test_canonical_order_is_contiguous_and_paper_24_is_stable():
    data = pd.read_csv(REPO / "data" / "data-clean.csv")
    contract = pd.read_csv(REPO / "data" / "included_study_order.csv")

    assert data["Paper_ID"].tolist() == EXPECTED_IDS
    assert contract["Paper_ID"].tolist() == EXPECTED_IDS
    assert data.loc[data["Paper_ID"].eq(24), "Title"].iloc[0] == EXPECTED_PAPER_24_TITLE
    assert contract.loc[contract["Paper_ID"].eq(24), "Title"].iloc[0] == EXPECTED_PAPER_24_TITLE
    assert [normalize_title(value) for value in data["Title"]] == [
        normalize_title(value) for value in contract["Title"]
    ]


def test_canonical_contract_matches_origin_titles_and_evidence_dois():
    origin = read_git_csv(REPO, "origin/main:data/data-clean.csv")
    contract = pd.read_csv(REPO / "data" / "included_study_order.csv")
    evidence = pd.read_csv(REPO / "data" / "tr_criteria_evidence.csv")

    assert origin["Paper_ID"].tolist() == EXPECTED_IDS
    assert [normalize_title(value) for value in origin["Title"]] == [
        normalize_title(value) for value in contract["Title"]
    ]
    contract_dois = [normalize_doi(value) for value in contract["DOI"]]
    assert all(contract_dois)
    assert len(set(contract_dois)) == 48
    evidence_dois = [normalize_doi(value) for value in evidence["DOI"]]
    assert evidence["Paper_ID"].tolist() == EXPECTED_IDS
    assert evidence_dois == contract_dois


def test_active_per_study_tables_use_canonical_ids_and_titles():
    contract = pd.read_csv(REPO / "data" / "included_study_order.csv")
    title_by_id = dict(zip(contract["Paper_ID"], contract["Title"].map(normalize_title)))
    roots = [REPO / "data", REPO / "tables", REPO / "analysis" / "review_20260803", REPO / "analysis" / "scientometrics"]

    checked = 0
    for root in roots:
        for path in root.rglob("*.csv"):
            if "provenance" in path.parts or path.name.casefold().startswith("screening_log_"):
                continue
            frame = pd.read_csv(path)
            if "Paper_ID" not in frame.columns:
                continue
            ids = pd.to_numeric(frame["Paper_ID"], errors="raise").astype(int)
            assert set(ids).issubset(set(EXPECTED_IDS)), path
            if len(frame) == 48:
                assert sorted(ids.tolist()) == EXPECTED_IDS, path
            if "Title" in frame.columns:
                for paper_id, title in zip(ids, frame["Title"]):
                    assert normalize_title(title) == title_by_id[paper_id], path
            checked += 1

    assert checked > 10


def _make_reviewer_workbook(path: Path, titles: list[str]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    header_one = [None, None, None]
    header_two = ["PAPER", "TITLE", "URL"]
    for index in range(11):
        header_one.extend([f"Reviewer_{index + 1}", None])
        header_two.extend(["LMIC RELEVANCE SCORE (1-5)", "TR SCORE (0-5)"])
    sheet.append(header_one)
    sheet.append(header_two)
    for paper_id, title in enumerate(titles, start=1):
        row = [paper_id, title, ""]
        for _ in range(11):
            row.extend([3, 1])
        sheet.append(row)
    workbook.save(path)


def test_reviewer_workbook_title_order_is_checked(tmp_path):
    titles = pd.read_csv(REPO / "data" / "data-clean.csv")["Title"].tolist()
    workbook_path = tmp_path / "scores.xlsx"
    _make_reviewer_workbook(workbook_path, titles)

    lmic, tr = _read_matrix(workbook_path)
    assert lmic.shape == (48, 11)
    assert tr.shape == (48, 11)

    broken_titles = list(titles)
    broken_titles[23], broken_titles[24] = broken_titles[24], broken_titles[23]
    broken_path = tmp_path / "broken_scores.xlsx"
    _make_reviewer_workbook(broken_path, broken_titles)
    with pytest.raises(ValueError, match="Paper 24 title"):
        _read_matrix(broken_path)
