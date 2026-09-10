from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]


def test_public_fleiss_kappa_outputs_are_aggregate_only():
    summary = pd.read_csv(REPO / "tables" / "analysis_fleiss_kappa_summary.csv")
    item_agreement = pd.read_csv(REPO / "tables" / "analysis_fleiss_kappa_item_agreement.csv")

    assert summary["Analysis"].tolist() == ["LMIC_Relevance_Score", "TR_Score"]
    assert (summary["Items"] == 48).all()
    assert (summary["Raters"] == 11).all()
    assert summary["Fleiss_kappa"].between(-1, 1).all()
    assert len(item_agreement) == 96
    assert set(item_agreement["Analysis"]) == {"LMIC_Relevance_Score", "TR_Score"}
    assert item_agreement["Paper_ID"].between(1, 48).all()
    assert "Title" in item_agreement.columns
    assert not any("Reviewer" in column or "Rating" in column for column in summary.columns)
    assert not any("Reviewer" in column or "Rating" in column for column in item_agreement.columns)
