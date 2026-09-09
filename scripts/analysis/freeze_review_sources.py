"""Freeze the local source files used by the MRI-LMICs review.

This script deliberately works from the latest local Excel exports and does
not contact GitHub or any external service.  It creates an auditable local
screening snapshot and updates ``data/data-clean.csv`` with the 48 included
records while preserving the existing CSV in the provenance directory.

The source workbook contains the screening log, but it does not contain the
independent ratings of all 11 reviewers.  That absence is recorded in the
manifest instead of being silently inferred from the assigned-reviewer field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_REPO = Path(__file__).resolve().parents[2]
DEFAULT_CANONICAL_XLSX = Path(
    r"C:\Users\Pc\AppData\Local\Temp\Document from Mateo.xlsx"
)
DEFAULT_SCREENING_XLSX = Path(
    r"C:\Users\Pc\Desktop\MIT\MRI super Resolution Narrative review\TEMP"
    r"\MRI_SR_Extraction_Template-finished.xlsx"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_title(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).replace("\u00a0", " ").split()).casefold()


def clean_text_cell(value: object) -> object:
    """Remove transport whitespace while preserving meaningful line breaks."""
    if pd.isna(value):
        return value
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def export_sources(
    repo: Path,
    canonical_xlsx: Path,
    screening_xlsx: Path,
    run_date: str,
) -> dict:
    if not canonical_xlsx.exists():
        raise FileNotFoundError(canonical_xlsx)
    if not screening_xlsx.exists():
        raise FileNotFoundError(screening_xlsx)

    canonical = pd.read_excel(canonical_xlsx, sheet_name="data-clean")
    screening = pd.read_excel(screening_xlsx, sheet_name="Sheet8")
    assignments = pd.read_excel(screening_xlsx, sheet_name="Sheet7")

    require_columns(canonical, ["Paper_ID", "Title", "Year"], "canonical data")
    require_columns(
        screening,
        ["Paper_ID", "Title", "URL", "Year", "Status", "Reason"],
        "screening log",
    )
    require_columns(assignments, ["#", "Title", "Reviewer"], "reviewer assignment")

    canonical = canonical.copy()
    canonical["Paper_ID"] = pd.to_numeric(canonical["Paper_ID"], errors="raise").astype(int)
    canonical["Year"] = pd.to_numeric(canonical["Year"], errors="coerce").astype("Int64")
    canonical["_title_key"] = canonical["Title"].map(normalize_title)
    if canonical["_title_key"].duplicated().any():
        duplicates = canonical.loc[
            canonical["_title_key"].duplicated(keep=False), "Title"
        ].tolist()
        raise ValueError(f"Duplicate canonical titles prevent deterministic mapping: {duplicates}")

    screening = screening.copy()
    screening["Paper_ID"] = pd.to_numeric(screening["Paper_ID"], errors="raise").astype(int)
    screening["Year"] = pd.to_numeric(screening["Year"], errors="coerce").astype("Int64")
    screening["Status"] = screening["Status"].fillna("").astype(str).str.strip()
    screening["_title_key"] = screening["Title"].map(normalize_title)

    included = screening[screening["Status"].str.casefold() == "included"].copy()
    excluded = screening[screening["Status"].str.casefold() == "excluded"].copy()
    if len(screening) != 183 or len(included) != 48 or len(excluded) != 135:
        raise ValueError(
            "Unexpected screening counts: "
            f"total={len(screening)}, included={len(included)}, excluded={len(excluded)}"
        )

    assignments = assignments.copy()
    assignments["Included_Sequence"] = pd.to_numeric(
        assignments["#"], errors="raise"
    ).astype(int)
    assignments["_title_key"] = assignments["Title"].map(normalize_title)
    assignment_merge = assignments.merge(
        canonical[["Paper_ID", "_title_key"]], on="_title_key", how="left", validate="one_to_one"
    )
    if assignment_merge["Paper_ID"].isna().any():
        missing = assignment_merge.loc[assignment_merge["Paper_ID"].isna(), "Title"].tolist()
        raise ValueError(f"Could not map assigned included titles to canonical data: {missing}")
    assignment_merge["Paper_ID"] = assignment_merge["Paper_ID"].astype(int)
    if len(assignment_merge) != 48 or assignment_merge["Paper_ID"].nunique() != 48:
        raise ValueError("Reviewer assignment sheet does not map one-to-one to 48 studies")

    out_root = repo / "analysis" / "reproducibility"
    provenance = out_root / "provenance"
    out_root.mkdir(parents=True, exist_ok=True)
    provenance.mkdir(parents=True, exist_ok=True)

    data_path = repo / "data" / "data-clean.csv"
    previous_snapshot = provenance / f"data-clean_before_freeze_{run_date}.csv"
    if data_path.exists() and not previous_snapshot.exists():
        shutil.copy2(data_path, previous_snapshot)

    canonical_export = canonical.drop(columns=["_title_key"])
    for column in canonical_export.columns:
        dtype = canonical_export[column].dtype
        if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
            canonical_export[column] = canonical_export[column].map(clean_text_cell)
    canonical_export.to_csv(data_path, index=False, encoding="utf-8")

    screening_export = screening.drop(columns=["_title_key"])
    screening_export.to_csv(out_root / "screening_log_183.csv", index=False, encoding="utf-8")

    included_export = assignment_merge.drop(columns=["_title_key", "#"], errors="ignore")
    included_export = included_export.rename(columns={"Reviewer": "Assigned_Reviewer"})
    included_export = included_export[
        ["Included_Sequence", "Paper_ID", "Title", "Year", "URL", "AI Architecture", "LMIC Score", "Assigned_Reviewer"]
    ].sort_values("Included_Sequence")
    included_export.to_csv(
        out_root / "included_studies_assignments_48.csv", index=False, encoding="utf-8"
    )

    canonical_ids = set(canonical["Paper_ID"].tolist())
    mapped_included_ids = set(included_export["Paper_ID"].tolist())
    if len(canonical_ids) != 48 or mapped_included_ids != canonical_ids:
        raise ValueError("Included screening IDs and canonical IDs are inconsistent")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_date": run_date,
        "repository": "MRI-LMICs-survey",
        "source_files": {
            "canonical_extraction": {
                "logical_path": "TEMP/Document from Mateo.xlsx",
                "sha256": sha256_file(canonical_xlsx),
                "sheet": "data-clean",
                "rows": int(len(canonical_export)),
                "columns": int(len(canonical_export.columns)),
            },
            "screening_and_assignment_workbook": {
                "logical_path": "TEMP/MRI_SR_Extraction_Template-finished.xlsx",
                "sha256": sha256_file(screening_xlsx),
                "screening_sheet": "Sheet8",
                "assignment_sheet": "Sheet7",
                "screening_rows": int(len(screening_export)),
                "included_rows": int(len(included)),
                "excluded_rows": int(len(excluded)),
                "assignment_rows": int(len(included_export)),
            },
        },
        "canonical_data": {
            "included_studies": int(len(canonical_export)),
            "paper_ids_preserved_from_source": True,
            "paper_id_values": sorted(int(value) for value in canonical_export["Paper_ID"]),
        },
        "reviewer_ratings": {
            "independent_ratings_for_all_11_reviewers_available": False,
            "current_assignment_sheet_is_not_an_independent_rating_matrix": True,
            "fleiss_kappa_status": "source_freeze_excludes_private_ratings",
            "recommended_delivery": "one identical 48-paper workbook per reviewer; merge after return",
        },
        "privacy_and_network": {
            "canonical_source_contains_reviewer_columns": [
                "Assigned_Reviewer",
                "Reviewer_Name",
            ],
            "raw_reviewer_names_exported": False,
            "public_upload_ready": False,
            "public_derivative": "analysis/reproducibility/public_package/",
            "network_calls_made": False,
            "github_modified": False,
        },
        "outputs": [
            "data/data-clean.csv",
            "analysis/reproducibility/screening_log_183.csv",
            "analysis/reproducibility/included_studies_assignments_48.csv",
            f"analysis/reproducibility/provenance/{previous_snapshot.name}",
        ],
    }
    (out_root / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--canonical-xlsx", type=Path, default=DEFAULT_CANONICAL_XLSX)
    parser.add_argument("--screening-xlsx", type=Path, default=DEFAULT_SCREENING_XLSX)
    parser.add_argument("--run-date", default="20260803")
    args = parser.parse_args()

    manifest = export_sources(
        args.repo.resolve(),
        args.canonical_xlsx.resolve(),
        args.screening_xlsx.resolve(),
        args.run_date,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
