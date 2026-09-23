"""Regression tests for final-corpus screening reconciliation."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from scripts.analysis.finalize_corpus import (
    _load_or_create_form_contract,
    _update_exclusion_register,
    remap_study_table,
)
from scripts.analysis.statistical.run_fleiss_kappa_from_private_xlsx import _read_matrix


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "figures"))


def _write_rating_workbook(path: Path, scoring_order: pd.DataFrame) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([None, None, None, *[name for reviewer in range(1, 12) for name in (f"Reviewer {reviewer}", None)]])
    sheet.append(["PAPER", "TITLE", "URL", *[name for _ in range(11) for name in ("LMIC", "TR")]])
    for row in scoring_order.itertuples(index=False):
        form_id = int(row.Form_Paper_ID)
        scores = [score for _ in range(11) for score in (1 + ((form_id - 1) % 5), form_id % 6)]
        sheet.append([form_id, row.Title, f"https://doi.org/{row.DOI}", *scores])
    workbook.save(path)


def _contracts(tmp_path: Path) -> tuple[Path, Path, pd.DataFrame]:
    source = pd.read_csv(REPO / "data" / "reviewer_scoring_order.csv")
    order = source.copy()
    order_path = tmp_path / "reviewer_scoring_order.csv"
    order.to_csv(order_path, index=False)

    active = order.loc[order["Include_In_Final_Corpus"]].copy()
    active["Paper_ID"] = active["Final_Paper_ID"].astype(int)
    active_path = tmp_path / "data-clean.csv"
    active[["Paper_ID", "Title", "DOI"]].to_csv(active_path, index=False)
    return active_path, order_path, order


def test_full_48_row_form_is_validated_then_exclusions_are_filtered(tmp_path):
    active_path, scoring_order_path, order = _contracts(tmp_path)
    workbook_path = tmp_path / "private_scores.xlsx"
    _write_rating_workbook(workbook_path, order)

    lmic, tr, titles = _read_matrix(
        workbook_path,
        active_path,
        include_titles=True,
        scoring_order_path=scoring_order_path,
    )

    assert lmic.shape == (45, 11)
    assert tr.shape == (45, 11)
    assert titles == pd.read_csv(active_path)["Title"].tolist()
    assert lmic[10, 0] == 2  # Form Paper 12 becomes final Paper_ID 11.
    assert lmic[21, 0] == 4  # Form Paper 24 becomes final Paper_ID 22.


def test_reordered_form_title_fails_before_any_analysis_output(tmp_path):
    active_path, scoring_order_path, order = _contracts(tmp_path)
    workbook_path = tmp_path / "private_scores_reordered.xlsx"
    _write_rating_workbook(workbook_path, order)
    # Rewrite the input with the titles at form rows 11 and 12 swapped.
    workbook = load_workbook(workbook_path)
    sheet = workbook.active
    left = [sheet.cell(12, column).value for column in range(1, sheet.max_column + 1)]
    right = [sheet.cell(13, column).value for column in range(1, sheet.max_column + 1)]
    for column, value in enumerate(right, start=1):
        sheet.cell(12, column).value = value
    for column, value in enumerate(left, start=1):
        sheet.cell(13, column).value = value
    workbook.save(workbook_path)

    with pytest.raises(ValueError, match="form order|rows must be ordered"):
        _read_matrix(
            workbook_path,
            active_path,
            scoring_order_path=scoring_order_path,
        )


def test_study_table_is_filtered_and_reindexed_by_title_not_numeric_shift(tmp_path):
    source = pd.read_csv(REPO / "data" / "data-clean.csv")
    active_path, _, order = _contracts(tmp_path)
    contract = order.copy()
    remapped = remap_study_table(source.sample(frac=1, random_state=19), contract)

    assert len(remapped) == 45
    assert remapped["Paper_ID"].tolist() == list(range(1, 46))
    assert remapped["Title"].tolist() == pd.read_csv(active_path)["Title"].tolist()


def test_scoring_contract_records_all_exclusions_and_stable_identities():
    contract = pd.read_csv(REPO / "data" / "reviewer_scoring_order.csv")
    assert contract["Form_Paper_ID"].tolist() == list(range(1, 49))
    excluded = contract.loc[~contract["Include_In_Final_Corpus"]]
    assert excluded["DOI"].str.casefold().tolist() == [
        "10.1101/2023.12.28.23300409",
        "10.1109/inocon57975.2023.10100995",
        "10.3389/fneur.2024.1330203",
    ]
    no_ai = excluded.loc[excluded["DOI"].str.casefold() == "10.3389/fneur.2024.1330203"].iloc[0]
    assert int(no_ai["Form_Paper_ID"]) == 37
    assert no_ai["Exclusion_Category"] == "No AI/DL method"
    assert "does not rely on deep learning" in no_ai["Exclusion_Reason"].casefold()
    assert contract.loc[contract["Include_In_Final_Corpus"], "Final_Paper_ID"].astype(int).tolist() == list(range(1, 46))


def test_same_doi_with_a_different_title_is_rejected():
    contract = pd.read_csv(REPO / "data" / "reviewer_scoring_order.csv")
    source = pd.read_csv(REPO / "data" / "data-clean.csv")
    source.loc[0, "Title"] = "A mismatched title"
    with pytest.raises(ValueError, match="title.*DOI|DOI.*title"):
        remap_study_table(source, contract)


def test_exclusion_register_normalizes_duplicate_category_labels():
    exclusions = _update_exclusion_register(_load_or_create_form_contract())

    assert exclusions["Exclusion_Category"].value_counts().to_dict() == {
        "Not MRI modality": 4,
        "Review/survey only": 3,
        "Duplicate": 3,
        "No AI/DL method": 1,
    }


def test_prisma_flow_reconciles_extraction_scoring_and_final_corpus_counts():
    from scripts.figures.figS2_prisma_flow import build_selection_flow

    nodes, edges, footnote = build_selection_flow(REPO)
    labels = [node["label"] for node in nodes]
    flat_labels = [" ".join(label.split()) for label in labels]

    assert len(nodes) == 7
    assert "n = 183" in flat_labels[0]
    assert "no recoverable screening disposition" in flat_labels[1].casefold()
    assert "n = 127" in flat_labels[1]
    assert "n = 56" in flat_labels[2]
    assert "8 pre-scoring exclusions + 48 scored" in flat_labels[2].casefold()
    assert (0, 1) in edges and (0, 2) in edges
    assert (1, 2) not in edges
    assert "not inferred" in flat_labels[1].casefold()
    assert "n = 8" in flat_labels[3] and "3 non-MRI; 3 reviews/surveys; 2 duplicates" in flat_labels[3]
    assert "n = 48" in flat_labels[4]
    assert "n = 3" in flat_labels[5]
    assert "duplicate preprint" in flat_labels[5]
    assert "method without AI/deep learning" in flat_labels[5]
    assert "n = 45" in flat_labels[6]
    assert "no reliable stage label for 127" in footnote
    assert "stage is not inferred" in footnote
