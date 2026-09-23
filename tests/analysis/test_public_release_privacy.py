import json
import hashlib
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
PUBLIC_DATA = REPO / "data" / "data-clean.csv"
PUBLIC_MANIFEST = REPO / "data" / "public_release_manifest.json"
FIELD_EVIDENCE = REPO / "data" / "field_characterization_evidence.csv"
DATASET_EVIDENCE = REPO / "data" / "dataset_characterization_evidence.csv"
PRIMARY_SR_SCOPE = REPO / "data" / "primary_sr_scope_evidence.csv"


def test_tracked_corpus_is_anonymized_and_has_a_public_release_manifest():
    """The versioned corpus must retain study data without reviewer identities."""
    data = pd.read_csv(PUBLIC_DATA)
    assert len(data) == 45
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
    assert entry["rows"] == 45
    assert entry["sha256_normalization"] == "utf8_lf"
    assert entry["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_public_manifest_tracks_dataset_characterization_evidence():
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    entry = manifest["tracked_public_evidence"]["dataset_characterization"]
    normalized = DATASET_EVIDENCE.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

    assert entry["logical_path"] == "data/dataset_characterization_evidence.csv"
    assert entry["rows"] == 45
    assert entry["sha256_normalization"] == "utf8_lf"
    assert entry["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_public_manifest_tracks_primary_sr_scope_evidence():
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    entry = manifest["tracked_public_evidence"]["primary_sr_scope"]
    normalized = PRIMARY_SR_SCOPE.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

    assert entry["logical_path"] == "data/primary_sr_scope_evidence.csv"
    assert entry["rows"] == 45
    assert entry["sha256_normalization"] == "utf8_lf"
    assert entry["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_public_manifest_pins_public_corpus_and_scoring_form_contracts():
    """Form-to-corpus mapping and exclusions must be auditable in a fresh clone."""
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    contracts = manifest["study_identity_contracts"]
    expected = {
        "included_study_order": ("data/included_study_order.csv", 45),
        "reviewer_scoring_order": ("data/reviewer_scoring_order.csv", 48),
        "post_extraction_exclusions": ("data/post_extraction_exclusions.csv", 11),
    }

    for key, (relative_path, rows) in expected.items():
        path = REPO / relative_path
        entry = contracts[key]
        normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        assert entry["logical_path"] == relative_path
        assert entry["rows"] == rows
        assert entry["sha256_normalization"] == "utf8_lf"
        assert entry["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_public_manifest_tracks_aggregate_random_forest_summary():
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    entry = manifest["analysis_outputs"]["analysis_random_forest_robustness_summary.csv"]
    summary_path = REPO / "tables" / "analysis_random_forest_robustness_summary.csv"
    normalized = summary_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

    assert entry["logical_path"] == "tables/analysis_random_forest_robustness_summary.csv"
    assert entry["rows"] == 4
    assert entry["sha256_normalization"] == "utf8_lf"
    assert entry["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()
