import json
import hashlib
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
PUBLIC_DATA = REPO / "data" / "data-clean.csv"
PUBLIC_MANIFEST = REPO / "data" / "public_release_manifest.json"
FIELD_EVIDENCE = REPO / "data" / "field_characterization_evidence.csv"


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


def test_public_manifest_tracks_field_characterization_evidence():
    """The scientific evidence input must be pinned with a platform-neutral hash."""
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    entry = manifest["tracked_public_evidence"]["field_characterization"]
    normalized = FIELD_EVIDENCE.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

    assert entry["logical_path"] == "data/field_characterization_evidence.csv"
    assert entry["rows"] == 48
    assert entry["sha256_normalization"] == "utf8_lf"
    assert entry["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()
