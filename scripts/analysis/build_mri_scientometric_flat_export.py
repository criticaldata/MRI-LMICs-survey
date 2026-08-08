"""Build one flat, machine-readable MRI scientometric export per DOI.

The CSV is the primary result table.  The XLSX builder consumes the same CSV
and puts only Source_Coverage on a second worksheet.  Reviewer identities and
blank manual-entry columns are intentionally excluded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO / "analysis" / "scientometrics" / "multisource_20260803"
DEFAULT_DESKTOP_DIR = Path(r"C:\Users\Pc\Desktop\MRI_LMICs_scientometric_export")
PUBLIC_TABLE_DIR = REPO / "tables"

ROLE_AUDIT = DEFAULT_RUN_DIR / "multisource_role_audit.csv"
CORPUS = REPO / "data" / "data-clean.csv"
AUTHOR_CANDIDATES = DEFAULT_RUN_DIR / "multisource_author_affiliation_candidates.csv"
ORCID_WORKS = DEFAULT_RUN_DIR / "multisource_orcid_work_matches.csv"
COVERAGE = DEFAULT_RUN_DIR / "multisource_coverage.csv"

RESULT_NAME = "MRI_LMICs_scientometric_results_20260803.csv"
COVERAGE_NAME = "MRI_LMICs_scientometric_source_coverage_20260803.csv"
PUBLIC_RESULT_NAME = "mri_scientometric_results.csv"
PUBLIC_COVERAGE_NAME = "mri_scientometric_source_coverage.csv"
MANIFEST_NAME = "MRI_LMICs_scientometric_flat_export_manifest_20260803.json"
IEEE_PREFIX = "IEEE_CSDL_"
EXCLUDED_RESULT_COLUMNS = {
    "PubMed_Status",
    "EuropePMC_Status",
    "Crossref_First_Country_Candidate",
    "Scopus_Status",
    "Crossref_Status",
    "EuropePMC_FullText_Status",
}
IEEE_MAIN_FIELDS = {
    "IEEE_CSDL_Article_ID",
    "IEEE_CSDL_First_Author",
    "IEEE_CSDL_First_Affiliation",
    "IEEE_CSDL_First_Country_Candidate",
}
EXCLUDED_IEEE_COLUMNS = {
    "IEEE_CSDL_Status",
    "IEEE_CSDL_Corresponding_Role_Available",
}
# The flat result table uses one explicit missing-value label.  Provider
# status fields such as ``not_found`` and ``not_applicable`` are retained
# because they are source-coverage evidence, not missing cell values.
NO_INFO_TOKENS = {"", "not_available", "not available", "n/a", "na", "none", "null", "nan"}


def is_no_information(value: object) -> bool:
    return str(value or "").strip().casefold() in NO_INFO_TOKENS


def normalize_export_value(value: object) -> str:
    text = str(value or "").strip()
    return "Not available" if is_no_information(text) else text


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = [str(header or "").strip() for header in (reader.fieldnames or [])]
        rows = []
        for raw in reader:
            row = {}
            for header in headers:
                value = raw.get(header, "")
                row[header] = "" if value is None else str(value).strip()
            rows.append(row)
    return headers, rows


def paper_key(row: dict[str, str]) -> str:
    return str(row.get("Paper_ID", "")).strip()


def sort_key(value: str) -> tuple[int, str]:
    try:
        return (0, f"{int(value):09d}")
    except ValueError:
        return (1, value)


def unique_join(values: Iterable[str], separator: str = " | ") -> str:
    seen = set()
    result = []
    for value in values:
        value = str(value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return separator.join(result)


def prefixed_fields(
    row: dict[str, str],
    headers: Iterable[str],
    prefix: str,
    excluded: set[str],
) -> dict[str, str]:
    output = {}
    for header in headers:
        if header in excluded:
            continue
        if header.endswith("_Manual") or header == "Field_Manual_Review":
            continue
        if "Reviewer" in header or header in {"Notes_Questions"}:
            continue
        output[f"{prefix}{header}"] = row.get(header, "")
    return output


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = paper_key(row)
        if key:
            grouped[key].append(row)
    return grouped


def aggregate_author_candidates(rows: list[dict[str, str]]) -> dict[str, str]:
    if not rows:
        return {
            "Author_Candidate_Record_Count": "0",
            "Author_Candidate_Source_Count": "0",
            "Author_Candidate_Sources": "",
            "Author_Candidate_Countries": "",
            "Author_Affiliation_Candidates": "",
        }

    records = []
    countries = []
    sources = []
    for row in rows:
        source = row.get("Source", "")
        author = row.get("Author_Name", "")
        position = row.get("Author_Position", "")
        country = row.get("Country_Candidate", "")
        corresponding = row.get("Is_Corresponding", "")
        affiliation = row.get("Affiliation", "")
        sources.append(source)
        countries.append(country)
        records.append(
            "source={source};author={author};position={position};"
            "country={country};corresponding={corresponding};affiliation={affiliation}".format(
                source=source,
                author=author,
                position=position,
                country=country,
                corresponding=corresponding,
                affiliation=affiliation,
            )
        )
    return {
        "Author_Candidate_Record_Count": str(len(rows)),
        "Author_Candidate_Source_Count": str(len(set(filter(None, sources)))),
        "Author_Candidate_Sources": unique_join(sources),
        "Author_Candidate_Countries": unique_join(countries),
        "Author_Affiliation_Candidates": " || ".join(dict.fromkeys(records)),
    }


def aggregate_orcid_work_matches(rows: list[dict[str, str]]) -> dict[str, str]:
    records = []
    for row in rows:
        records.append(
            "orcid={orcid};title={title};year={year};source={source};match={match}".format(
                orcid=row.get("ORCID", ""),
                title=row.get("Work_Title", ""),
                year=row.get("Work_Year", ""),
                source=row.get("ORCID_Work_Source", ""),
                match=row.get("Work_Match", ""),
            )
        )
    return {
        "ORCID_Work_Match_Count": str(len(rows)),
        "ORCID_Work_Matches_Aggregated": " || ".join(dict.fromkeys(records)),
    }


def build_flat_table() -> tuple[list[str], list[dict[str, str]], list[str]]:
    role_headers, role_rows = read_csv(ROLE_AUDIT)
    corpus_headers, corpus_rows = read_csv(CORPUS)
    author_headers, author_rows = read_csv(AUTHOR_CANDIDATES)
    orcid_headers, orcid_rows = read_csv(ORCID_WORKS)

    role_by_id = {paper_key(row): row for row in role_rows if paper_key(row)}
    corpus_by_id = {paper_key(row): row for row in corpus_rows if paper_key(row)}
    authors_by_id = group_rows(author_rows)
    orcid_by_id = group_rows(orcid_rows)

    if len(role_by_id) != len(role_rows):
        raise ValueError("multisource_role_audit.csv must contain one unique row per Paper_ID")

    base_ids = sorted(role_by_id, key=sort_key)
    base_headers = ["Paper_ID", "DOI", "Title", "Year"]
    role_extra_headers = [
        header for header in role_headers
        if header not in {"Paper_ID", "DOI", "Title", "Year"}
        and "Manual" not in header
        and (not header.startswith(IEEE_PREFIX) or header in IEEE_MAIN_FIELDS)
        and header not in EXCLUDED_IEEE_COLUMNS
        and header not in EXCLUDED_RESULT_COLUMNS
        and not header.endswith("_Status")
    ]
    auxiliary_headers = [
        "Author_Candidate_Record_Count",
        "Author_Candidate_Source_Count",
        "Author_Candidate_Sources",
        "Author_Candidate_Countries",
        "Author_Affiliation_Candidates",
        "ORCID_Work_Match_Count",
        "ORCID_Work_Matches_Aggregated",
        "Review_DOI",
    ]
    headers = (
        base_headers
        + role_extra_headers
        + auxiliary_headers
    )

    output_rows = []
    for paper_id in base_ids:
        role = role_by_id[paper_id]
        corpus = corpus_by_id.get(paper_id, {})
        row = {
            "Paper_ID": paper_id,
            "DOI": role.get("DOI", "") or corpus.get("DOI", ""),
            "Title": role.get("Title", "") or corpus.get("Title", ""),
            "Year": corpus.get("Year", "") or role.get("Year", ""),
        }
        for header in role_extra_headers:
            row[header] = role.get(header, "")
        row.update(aggregate_author_candidates(authors_by_id.get(paper_id, [])))
        row.update(aggregate_orcid_work_matches(orcid_by_id.get(paper_id, [])))

        first_manual = role.get("First_Country_Manual_Required", "") == "Yes"
        corresponding_manual = role.get("Corresponding_Country_Manual_Required", "") == "Yes"
        reasons = []
        if role.get("First_Country_Manual_Reason", ""):
            reasons.append("first_author: " + role["First_Country_Manual_Reason"])
        if role.get("Corresponding_Country_Manual_Reason", ""):
            reasons.append("corresponding_author: " + role["Corresponding_Country_Manual_Reason"])
        row["Review_DOI"] = row["DOI"] if first_manual or corresponding_manual else ""
        output_rows.append(row)

    for row in output_rows:
        for header in headers:
            row.setdefault(header, "")

    # Remove only columns that contain no usable information anywhere in the
    # 48-row corpus.  This is deliberately data-driven so future reruns do not
    # require hard-coding provider-specific column names.
    kept_headers = []
    removed_no_information_columns = []
    for header in headers:
        if header in {"Paper_ID", "DOI", "Title", "Year"} or any(
            not is_no_information(row.get(header, "")) for row in output_rows
        ):
            kept_headers.append(header)
        else:
            removed_no_information_columns.append(header)

    # Normalize every missing cell in the flat result.  Coverage remains a
    # separate audit sheet and keeps its structured source-status vocabulary.
    for row in output_rows:
        for header in kept_headers:
            row[header] = normalize_export_value(row.get(header, ""))

    return kept_headers, output_rows, removed_no_information_columns


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop-dir", type=Path, default=DEFAULT_DESKTOP_DIR)
    args = parser.parse_args()

    headers, rows, removed_no_information_columns = build_flat_table()
    if len(rows) != 48:
        raise ValueError(f"Expected 48 DOI rows, found {len(rows)}")
    if len({row["DOI"] for row in rows}) != len(rows):
        raise ValueError("The flat export contains duplicate DOI values")
    output_paths = [
        DEFAULT_RUN_DIR / RESULT_NAME,
        args.desktop_dir / RESULT_NAME,
        PUBLIC_TABLE_DIR / PUBLIC_RESULT_NAME,
    ]
    coverage_paths = [
        DEFAULT_RUN_DIR / COVERAGE_NAME,
        args.desktop_dir / COVERAGE_NAME,
        PUBLIC_TABLE_DIR / PUBLIC_COVERAGE_NAME,
    ]
    for path in output_paths:
        write_csv(path, headers, rows)
    coverage_headers, coverage_rows = read_csv(COVERAGE)
    for path in coverage_paths:
        write_csv(path, coverage_headers, coverage_rows)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "column_count": len(headers),
        "primary_key": "DOI",
        "source_coverage_is_separate": True,
        "manual_columns_included": False,
        "missing_value_label": "Not available",
        "blank_cells_in_result": sum(
            1 for row in rows for header in headers if not row.get(header, "").strip()
        ),
        "removed_no_information_columns": removed_no_information_columns,
        "integrated_ieee_columns": sorted(IEEE_MAIN_FIELDS),
        "excluded_ieee_columns": sorted(EXCLUDED_IEEE_COLUMNS),
        "excluded_result_columns": sorted(EXCLUDED_RESULT_COLUMNS),
        "manual_review_rule": "No manual-entry columns are exported; Review_DOI is populated only when the multisource resolver cannot close a DOI.",
        "result_files": [
            {"path": str(path), "sha256": sha256(path)}
            for path in output_paths
        ],
        "coverage_files": [
            {"path": str(path), "sha256": sha256(path)}
            for path in coverage_paths
        ],
        "separation_policy": {
            "scientometric_result_excludes_prefixes": ["Corpus_", "Dataset_", "Field_"],
            "canonical_methodology_source": "data/data-clean.csv",
        },
        "excluded_private_columns": ["Assigned_Reviewer", "Reviewer_Name", "Notes_Questions"],
        "excluded_manual_columns": ["*_Manual", "*Manual*", "Field_Manual_Review"],
    }
    for path in [DEFAULT_RUN_DIR / MANIFEST_NAME, args.desktop_dir / MANIFEST_NAME]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    manual_dois = [
        row["Review_DOI"]
        for row in rows
        if row["Review_DOI"] != "Not available"
    ]
    print(json.dumps({
        "rows": len(rows),
        "columns": len(headers),
        "manual_review_dois": manual_dois,
        "result_paths": [str(path) for path in output_paths],
        "coverage_paths": [str(path) for path in coverage_paths],
        "integrated_ieee_columns": sorted(IEEE_MAIN_FIELDS),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
