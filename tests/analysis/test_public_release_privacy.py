import json
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
PUBLIC_DATA = REPO / "data" / "data-clean.csv"
PUBLIC_MANIFEST = REPO / "data" / "public_release_manifest.json"


def test_tracked_corpus_is_anonymized_and_has_a_public_release_manifest():
    """The versioned corpus must retain study data without reviewer identities."""
    data = pd.read_csv(PUBLIC_DATA)
    assert len(data) == 48
    assert not {"Reviewer_Name", "Assigned_Reviewer", "Reviewer"}.intersection(data.columns)

    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["privacy"]["reviewer_identifiers_detected_after_scrub"] == []
    assert manifest["privacy"]["removed_columns_from_public_canonical"] == [
        "Assigned_Reviewer",
        "Reviewer_Name",
    ]


def test_private_internal_corpus_is_ignored_by_git_configuration():
    """The local reviewer-containing corpus cannot be staged accidentally."""
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "data/private/" in ignored
