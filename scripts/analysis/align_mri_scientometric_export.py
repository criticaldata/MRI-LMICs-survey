"""Align the cached flat scientometric export to the final eligible DOI set.

Provider calls and raw API caches are deliberately not required here. The source
coverage table remains an audit of the earlier 48-DOI acquisition run; this
step filters the result rows to the final corpus and assigns Paper_ID by DOI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO / "tables" / "mri_scientometric_results.csv"
DEFAULT_OUTPUT = DEFAULT_INPUT
DEFAULT_MANIFEST = REPO / "tables" / "mri_scientometric_export_manifest.json"
DEFAULT_COVERAGE = REPO / "tables" / "mri_scientometric_source_coverage.csv"
PUBLISHED_DOI_ALIASES = {
    "10.1101/2024.01.05.24300892": "10.3389/fneur.2024.1339223",
}


def normalize_doi(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        text = text.removeprefix(prefix)
    return text.split("?", 1)[0].rstrip("/ ")


def normalize_title(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.casefold())).strip()


def normalize_world_bank_group(value: object) -> str:
    """Normalize legacy income-group labels to World Bank's official codes."""
    text = "" if pd.isna(value) else str(value).strip()
    return {"LMIC": "LMC", "UMIC": "UMC"}.get(text.upper(), text)


def sha256_utf8_lf(path: Path) -> str:
    value = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def align_export(
    input_path: Path,
    output_path: Path,
    contract_path: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, object]:
    previous_manifest = {}
    if manifest_path.exists():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_manifest = {}
    source = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    contract = pd.read_csv(contract_path)
    scoring_form_path = REPO / "data" / "reviewer_scoring_order.csv"
    scoring_form_rows = (
        len(pd.read_csv(scoring_form_path, dtype=str))
        if scoring_form_path.exists()
        else len(source)
    )
    required = {"Paper_ID", "DOI", "Title"}
    if not required.issubset(source.columns) or not required.issubset(contract.columns):
        raise ValueError("Scientometric export and canonical corpus must contain Paper_ID, DOI, and Title")

    source["_doi"] = source["DOI"].map(normalize_doi)
    contract["_doi"] = contract["DOI"].map(normalize_doi)
    if source["_doi"].eq("").any() or source["_doi"].duplicated().any():
        raise ValueError("Source scientometric export must contain unique, non-empty DOIs")
    if contract["_doi"].eq("").any() or contract["_doi"].duplicated().any():
        raise ValueError("Final corpus must contain unique, non-empty DOIs")

    alias_rows = []
    for source_doi, canonical_doi in PUBLISHED_DOI_ALIASES.items():
        matching = source.index[source["_doi"].eq(source_doi)].tolist()
        if not matching:
            continue
        canonical_rows = contract.index[contract["_doi"].eq(canonical_doi)].tolist()
        if len(canonical_rows) != 1:
            raise ValueError(f"Published DOI alias target is not unique in the canonical corpus: {canonical_doi}")
        source_title = normalize_title(source.loc[matching[0], "Title"])
        canonical_title = normalize_title(contract.loc[canonical_rows[0], "Title"])
        if source_title != canonical_title:
            raise ValueError(f"Preprint DOI alias title does not match the published article: {source_doi}")
        source.loc[matching[0], "_doi"] = canonical_doi
        alias_rows.append({
            "source_doi": source_doi,
            "canonical_doi": canonical_doi,
            "relationship": "preprint record mapped to its published article",
            "title": str(contract.loc[canonical_rows[0], "Title"]),
        })

    if source["_doi"].duplicated().any():
        raise ValueError("Source DOI aliases created a duplicate DOI mapping")
    source_by_doi = source.set_index("_doi", drop=False)
    missing = sorted(set(contract["_doi"]) - set(source_by_doi.index))
    if missing:
        raise ValueError(f"Scientometric source export is missing {len(missing)} final-corpus DOIs")

    aligned = source_by_doi.loc[contract["_doi"].tolist()].copy()
    aligned["Paper_ID"] = contract["Paper_ID"].astype(int).tolist()
    source_titles = aligned["Title"].map(normalize_title).tolist()
    canonical_titles = contract["Title"].map(normalize_title).tolist()
    if source_titles != canonical_titles:
        bad = next(index for index, (left, right) in enumerate(zip(source_titles, canonical_titles), start=1) if left != right)
        raise ValueError(f"Scientometric title does not match canonical DOI at final Paper_ID={bad}")
    aligned["Title"] = contract["Title"].astype(str).tolist()
    aligned["DOI"] = contract["DOI"].astype(str).tolist()
    if "First_Author_WB_Group_Current" in aligned.columns:
        aligned["First_Author_WB_Group_Current"] = aligned[
            "First_Author_WB_Group_Current"
        ].map(normalize_world_bank_group)
    aligned = aligned.drop(columns=["_doi"]).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(output_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    excluded = int(len(source) - len(aligned))
    # The flat export is promoted in place, so after the first run it contains
    # only the final corpus. Preserve the original acquisition denominator from
    # the 48-row scored form instead of silently shrinking it to 45 on reruns.
    acquisition_rows = max(
        int(previous_manifest.get("source_acquisition_rows", 0)),
        int(scoring_form_rows),
    )
    if acquisition_rows < len(aligned):
        raise ValueError("Scored-form acquisition rows cannot be smaller than the final export")
    acquisition_exclusions = acquisition_rows - len(aligned)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "alignment_key": "normalized DOI; Paper_ID assigned from final canonical corpus",
        "source_rows": int(len(source)),
        "source_acquisition_rows": acquisition_rows,
        "source_acquisition_reference": "data/reviewer_scoring_order.csv",
        "source_acquisition_reference_rows": int(scoring_form_rows),
        "final_rows": int(len(aligned)),
        "excluded_from_final_export": excluded,
        "excluded_from_final_export_total": acquisition_exclusions,
        "doi_aliases_applied": alias_rows,
        "canonical_contract": "data/included_study_order.csv",
        "public_result": "tables/mri_scientometric_results.csv",
        "source_coverage_reference": {
            "path": "tables/mri_scientometric_source_coverage.csv",
            "meaning": "coverage counts refer to the prior API acquisition over the original 48-record scored form, not the final eligible 45-study export",
        },
        "sha256_utf8_lf": sha256_utf8_lf(output_path),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contract", type=Path, default=REPO / "data" / "included_study_order.csv")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    result = align_export(
        args.input.resolve(),
        args.output.resolve(),
        args.contract.resolve(),
        args.manifest.resolve(),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
