"""Build a privacy-scrubbed local package suitable for later publication.

The internal canonical CSV is retained for the review team because it contains
reviewer assignment fields.  This script creates a separate public derivative
with reviewer names and assignment columns removed.  It never contacts GitHub
or any external service and does not publish the result.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
TRACKED_PUBLIC_DATA = REPO / "data" / "data-clean.csv"
PRIVATE_DATA = REPO / "data" / "private" / "data-clean_internal.csv"
SOURCE_SCREENING = REPO / "analysis" / "reproducibility" / "screening_log_183.csv"
SOURCE_ASSIGNMENTS = (
    REPO / "analysis" / "reproducibility" / "included_studies_assignments_48.csv"
)
OUTPUT = REPO / "analysis" / "reproducibility" / "public_package"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8")


def sanitize_public_url(value: object) -> object:
    """Remove query strings/fragments from public HTTP(S) URLs.

    Publisher URLs in the internal extraction sometimes contain session or
    access-query parameters such as ``casa_token``.  The public derivative
    keeps the stable article path while removing those parameters.
    """
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    parsed = urlsplit(stripped)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def sanitize_url_columns(frames: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], int, list[str]]:
    sanitized = {}
    changed = 0
    columns_seen = []
    for frame_name, frame in frames.items():
        result = frame.copy()
        for column in result.columns:
            if "url" not in str(column).casefold():
                continue
            before = result[column].copy()
            result[column] = result[column].map(sanitize_public_url)
            changed += int((before.fillna("").astype(str) != result[column].fillna("").astype(str)).sum())
            columns_seen.append(f"{frame_name}.{column}")
        sanitized[frame_name] = result
    return sanitized, changed, sorted(set(columns_seen))


def build_package() -> dict:
    for path in (TRACKED_PUBLIC_DATA, SOURCE_SCREENING, SOURCE_ASSIGNMENTS):
        if not path.exists():
            raise FileNotFoundError(path)

    PRIVATE_DATA.parent.mkdir(parents=True, exist_ok=True)
    if not PRIVATE_DATA.exists():
        shutil.copy2(TRACKED_PUBLIC_DATA, PRIVATE_DATA)

    internal_data = pd.read_csv(PRIVATE_DATA)
    internal_screening = pd.read_csv(SOURCE_SCREENING)
    internal_assignments = pd.read_csv(SOURCE_ASSIGNMENTS)

    reviewer_name_column = "Reviewer_Name"
    reviewer_assignment_columns = {"Assigned_Reviewer", "Reviewer", "Reviewer_Name"}
    if reviewer_name_column not in internal_data.columns:
        raise ValueError("The internal canonical data no longer contains Reviewer_Name")

    reviewer_names = {
        str(value).strip().casefold()
        for value in internal_data[reviewer_name_column].dropna()
        if str(value).strip()
    }
    reviewer_tokens = reviewer_names | {
        "reviewer_1",
        "reviewer_2",
        "reviewer_3",
        "reviewer_4",
        "reviewer_5",
        "reviewer_6",
        "reviewer_7",
        "reviewer_8",
        "reviewer_9",
        "reviewer_10",
        "reviewer_11",
    }

    public_data = internal_data.drop(
        columns=sorted(reviewer_assignment_columns & set(internal_data.columns))
    ).copy()
    public_screening = internal_screening.drop(
        columns=sorted(reviewer_assignment_columns & set(internal_screening.columns)),
        errors="ignore",
    ).copy()
    public_assignments = internal_assignments.drop(
        columns=sorted(reviewer_assignment_columns & set(internal_assignments.columns)),
        errors="ignore",
    ).copy()
    public_frames, url_query_parameters_removed, url_columns_sanitized = sanitize_url_columns(
        {
            "data": public_data,
            "screening": public_screening,
            "assignments": public_assignments,
        }
    )
    public_data = public_frames["data"]
    public_screening = public_frames["screening"]
    public_assignments = public_frames["assignments"]

    public_text = "\n".join(
        frame.fillna("").astype(str).agg(" | ".join, axis=1).str.cat(sep="\n")
        for frame in (public_data, public_screening, public_assignments)
    ).casefold()
    leaked_tokens = sorted(token for token in reviewer_tokens if token in public_text)
    if leaked_tokens:
        raise ValueError(
            "Reviewer identifiers remain in the public canonical derivative: "
            f"{leaked_tokens}"
        )
    query_tokens = ["casa_token=", "api_key=", "access_token=", "token="]
    remaining_query_tokens = sorted(token for token in query_tokens if token in public_text)
    if remaining_query_tokens:
        raise ValueError(
            "URL query parameters remain in the public canonical derivative: "
            f"{remaining_query_tokens}"
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_path = OUTPUT / "data-clean_public.csv"
    screening_path = OUTPUT / "screening_log_183_public.csv"
    assignments_path = OUTPUT / "included_studies_public_48.csv"
    write_csv(public_data, data_path)
    write_csv(public_data, TRACKED_PUBLIC_DATA)
    write_csv(public_screening, screening_path)
    write_csv(public_assignments, assignments_path)

    readme = """# Public reproducibility package (local, not published)

This directory contains derivatives prepared for a future public release of
the MRI-LMICs review. The internal canonical CSV is not copied here because it
contains reviewer names and assignment fields.

Removed from the public canonical derivative:

- `Reviewer_Name`
- `Assigned_Reviewer`
- any equivalent reviewer assignment column in the derived assignment file

The package contains no independent reviewer ratings. Aggregate Fleiss kappa
results may be published separately, but the private workbook is never copied
into this package. The private-input runner is
`scripts/analysis/statistical/run_fleiss_kappa_from_private_xlsx.py`.

Before any upload, perform a final human privacy review of titles, notes,
URLs, and supplementary documents. Query strings and URL fragments were
removed from HTTP(S) links; no article PDFs or independent reviewer ratings
are included. This package was generated locally and was not pushed to GitHub.
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "MRI-LMICs-survey",
        "published": False,
        "github_modified": False,
        "privacy": {
            "internal_source_contains_reviewer_names": True,
            "removed_columns_from_public_canonical": sorted(
                reviewer_assignment_columns & set(internal_data.columns)
            ),
            "reviewer_identifiers_detected_after_scrub": leaked_tokens,
            "independent_reviewer_ratings_included": False,
            "url_query_parameters_removed": int(url_query_parameters_removed),
            "url_columns_sanitized": url_columns_sanitized,
            "query_tokens_detected_after_scrub": remaining_query_tokens,
        },
        "source_files": {
            "internal_data": {
                "logical_path": "data/private/data-clean_internal.csv",
                "sha256": sha256_file(PRIVATE_DATA),
                "rows": int(len(internal_data)),
            },
            "screening_log": {
                "logical_path": "analysis/reproducibility/screening_log_183.csv",
                "sha256": sha256_file(SOURCE_SCREENING),
                "rows": int(len(internal_screening)),
            },
            "assignments": {
                "logical_path": "analysis/reproducibility/included_studies_assignments_48.csv",
                "sha256": sha256_file(SOURCE_ASSIGNMENTS),
                "rows": int(len(internal_assignments)),
            },
        },
        "outputs": {
            "data": {
                "logical_path": "analysis/reproducibility/public_package/data-clean_public.csv",
                "sha256": sha256_file(data_path),
                "rows": int(len(public_data)),
                "columns": int(len(public_data.columns)),
            },
            "screening": {
                "logical_path": "analysis/reproducibility/public_package/screening_log_183_public.csv",
                "sha256": sha256_file(screening_path),
                "rows": int(len(public_screening)),
            },
            "assignments": {
                "logical_path": "analysis/reproducibility/public_package/included_studies_public_48.csv",
                "sha256": sha256_file(assignments_path),
                "rows": int(len(public_assignments)),
            },
        },
    }
    (OUTPUT / "public_package_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    public_manifest = {
        "generated_at_utc": manifest["generated_at_utc"],
        "repository": manifest["repository"],
        "tracked_public_corpus": {
            "logical_path": "data/data-clean.csv",
            "sha256": sha256_file(TRACKED_PUBLIC_DATA),
            "rows": int(len(public_data)),
            "columns": int(len(public_data.columns)),
        },
        "privacy": manifest["privacy"],
        "independent_reviewer_ratings_included": False,
        "fleiss_kappa_status": "aggregate_summary_published_private_input",
    }
    (REPO / "data" / "public_release_manifest.json").write_text(
        json.dumps(public_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build_package(), indent=2, ensure_ascii=False))
