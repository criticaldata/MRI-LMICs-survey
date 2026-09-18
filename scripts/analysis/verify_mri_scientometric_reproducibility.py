"""Audit the MRI multi-source scientometric artifacts without network access.

This verifier is intentionally offline.  It checks the cached-response
lineage, input/output hashes, coverage arithmetic, flat-export schema,
missing-value policy, workbook structure, and credential hygiene.  It does
not claim that a provider was reachable: provider access results remain the
authoritative coverage record (for example, Scopus is an authentication
error in this run).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


REPO = Path(__file__).resolve().parents[2]
RUN_DIR = REPO / "analysis" / "scientometrics" / "multisource_20260803"
MANIFEST = RUN_DIR / "multisource_run_manifest.json"
FLAT_MANIFEST = RUN_DIR / "MRI_LMICs_scientometric_flat_export_manifest_20260803.json"
FLAT = RUN_DIR / "MRI_LMICs_scientometric_results_20260803.csv"
COVERAGE = RUN_DIR / "multisource_coverage.csv"
EXPORTED_COVERAGE = RUN_DIR / "MRI_LMICs_scientometric_source_coverage_20260803.csv"
XLSX = RUN_DIR / "MRI_LMICs_scientometric_results_20260803.xlsx"
ROLE = RUN_DIR / "multisource_role_audit.csv"
RAW_DIR = RUN_DIR / "raw"
RAW_INVENTORY = RUN_DIR / "mri_scientometric_raw_cache_inventory_20260804.json"
AUDIT = RUN_DIR / "mri_scientometric_reproducibility_audit_20260804.json"
PIPELINE = REPO / "scripts" / "analysis" / "mri_scientometric_multisource.py"
FLAT_BUILDER = REPO / "scripts" / "analysis" / "build_mri_scientometric_flat_export.py"
XLSX_BUILDER = REPO / "scripts" / "analysis" / "build_mri_scientometric_xlsx.mjs"
ENV_FILE = Path(r"C:\Users\Pc\Desktop\MIT\Scientometric Analysis Tool\SCIENTOMETRIC ANALYSIS TOOL\.env")
PUBLIC_RESULTS = REPO / "tables" / "mri_scientometric_results.csv"
PUBLIC_COVERAGE = REPO / "tables" / "mri_scientometric_source_coverage.csv"

EXPECTED_REMOVED_COLUMNS = {
    "Semantic_First_Affiliation",
    "Semantic_First_Country_Candidate",
    "Scopus_First_Author",
    "Scopus_First_Affiliation",
    "Scopus_First_Country_Candidate",
}
MISSING_LABEL = "Not available"
EXPECTED_IEEE_MAIN_COLUMNS = {
    "IEEE_CSDL_Article_ID",
    "IEEE_CSDL_First_Author",
    "IEEE_CSDL_First_Affiliation",
    "IEEE_CSDL_First_Country_Candidate",
}
EXCLUDED_IEEE_COLUMNS = {
    "IEEE_CSDL_Status",
    "IEEE_CSDL_Corresponding_Role_Available",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        return headers, list(reader)


def read_env_keys(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            values[key.strip()] = value
    return values


def build_raw_inventory() -> dict[str, object]:
    files = []
    for path in sorted(RAW_DIR.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            {
                "path": path.relative_to(RUN_DIR).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    inventory = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "offline_cache_inventory",
        "raw_cache_root": "raw/",
        "raw_cache_file_count": len(files),
        "files": files,
    }
    RAW_INVENTORY.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return inventory


def xlsx_sheet_names(path: Path) -> list[str]:
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    return [node.attrib["name"] for node in root.findall(f"{namespace}sheets/{namespace}sheet")]


def run_public_release_audit() -> None:
    """Validate the versioned scientometric release without private API caches."""
    results_headers, results_rows = read_csv(PUBLIC_RESULTS)
    coverage_headers, coverage_rows = read_csv(PUBLIC_COVERAGE)
    forbidden_headers = {"Reviewer_Name", "Assigned_Reviewer", "Notes_Questions"}
    methodology_prefixes = ("Corpus_", "Dataset_", "Field_")
    dois = [str(row.get("DOI", "")).strip().casefold() for row in results_rows]
    blank_cells = [
        f"{row.get('Paper_ID', '')}:{header}"
        for row in results_rows
        for header in results_headers
        if not str(row.get(header, "")).strip()
    ]
    checks = {
        "results_have_48_unique_dois": len(results_rows) == 48 and len(dois) == len(set(dois)) and all(dois),
        "results_exclude_private_and_methodology_fields": not forbidden_headers.intersection(results_headers)
        and not any(header.startswith(methodology_prefixes) for header in results_headers),
        "results_use_explicit_missing_values": not blank_cells,
        "coverage_is_present_and_structured": bool(coverage_rows) and {"Source", "Requests", "Status_Breakdown"}.issubset(coverage_headers),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({
        "status": status,
        "mode": "public_release_audit",
        "checks": checks,
        "results": str(PUBLIC_RESULTS.relative_to(REPO)),
        "coverage": str(PUBLIC_COVERAGE.relative_to(REPO)),
    }, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--public-release",
        action="store_true",
        help="Audit only the versioned flat release; do not require local API caches or credentials.",
    )
    args = parser.parse_args()
    if args.public_release:
        run_public_release_audit()
        return

    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    flat_manifest = json.loads(FLAT_MANIFEST.read_text(encoding="utf-8"))
    flat_headers, flat_rows = read_csv(FLAT)
    coverage_headers, coverage_rows = read_csv(COVERAGE)
    exported_coverage_headers, exported_coverage_rows = read_csv(EXPORTED_COVERAGE)
    role_headers, role_rows = read_csv(ROLE)
    raw_inventory = build_raw_inventory()
    serpapi_rows = [row for row in role_rows if row.get("SerpAPI_Status") not in {"", "not_run"}]
    serpapi_resolved_rows = [
        row for row in serpapi_rows
        if str(row.get("Corresponding_Country_Resolution_Status", "")).startswith("resolved_serpapi")
    ]
    serpapi_summary = [
        {
            "Paper_ID": row.get("Paper_ID", ""),
            "DOI": row.get("DOI", ""),
            "status": row.get("SerpAPI_Status", ""),
            "matched_corresponding_names": row.get("SerpAPI_Matched_Corresponding_Names", ""),
            "countries": row.get("SerpAPI_Corresponding_Countries", ""),
            "resolution_status": row.get("Corresponding_Country_Resolution_Status", ""),
        }
        for row in serpapi_rows
    ]
    serpapi_all_dois = bool(manifest.get("serpapi_query_policy", {}).get("all_dois"))
    expected_serpapi_rows = len(role_rows) if serpapi_all_dois else 2

    check(
        "corpus_has_48_studies",
        manifest.get("source_studies") == 48 and len(role_rows) == 48,
        {"manifest": manifest.get("source_studies"), "role_audit_rows": len(role_rows)},
    )
    role_dois = [str(row.get("DOI", "")).strip().casefold() for row in role_rows]
    check(
        "role_audit_unique_doi",
        len(role_dois) == len(set(role_dois)) and all(role_dois),
        {"rows": len(role_dois), "unique_dois": len(set(role_dois))},
    )
    flat_dois = [str(row.get("DOI", "")).strip().casefold() for row in flat_rows]
    check(
        "flat_export_has_one_row_per_doi",
        len(flat_rows) == 48 and len(flat_dois) == len(set(flat_dois)) and all(flat_dois),
        {"rows": len(flat_rows), "unique_dois": len(set(flat_dois))},
    )
    methodology_prefixes = ("Corpus_", "Dataset_Dataset_", "Field_Field_")
    check(
        "scientometric_export_excludes_methodology_columns",
        not any(header.startswith(methodology_prefixes) for header in flat_headers),
        {"methodology_columns_present": [header for header in flat_headers if header.startswith(methodology_prefixes)]},
    )
    removed = set(flat_manifest.get("removed_no_information_columns", []))
    check(
        "irrelevant_empty_columns_removed",
        EXPECTED_REMOVED_COLUMNS.issubset(removed)
        and not EXPECTED_REMOVED_COLUMNS.intersection(flat_headers),
        {
            "removed_no_information_columns": sorted(removed),
            "requested_columns_absent": sorted(EXPECTED_REMOVED_COLUMNS.intersection(set(flat_headers))),
        },
    )
    check(
        "useful_ieee_csdl_fields_integrated_in_main_export",
        EXPECTED_IEEE_MAIN_COLUMNS.issubset(flat_headers)
        and not EXCLUDED_IEEE_COLUMNS.intersection(flat_headers),
        {
            "main_ieee_headers": [header for header in flat_headers if header.startswith("IEEE_CSDL_")],
            "required_integrated_columns": sorted(EXPECTED_IEEE_MAIN_COLUMNS),
            "excluded_ieee_columns_present": sorted(EXCLUDED_IEEE_COLUMNS.intersection(flat_headers)),
        },
    )
    blank_cells = [
        f"{row.get('Paper_ID', '')}:{header}"
        for row in flat_rows
        for header in flat_headers
        if not str(row.get(header, "")).strip()
    ]
    legacy_missing_cells = [
        f"{row.get('Paper_ID', '')}:{header}"
        for row in flat_rows
        for header in flat_headers
        if str(row.get(header, "")).strip().casefold() in {"not_available", "n/a", "na"}
    ]
    check(
        "flat_export_missing_value_policy",
        not blank_cells and not legacy_missing_cells and flat_manifest.get("missing_value_label") == MISSING_LABEL,
        {
            "missing_value_label": flat_manifest.get("missing_value_label"),
            "blank_cell_count": len(blank_cells),
            "legacy_missing_label_count": len(legacy_missing_cells),
            "not_available_cell_count": sum(
                1 for row in flat_rows for header in flat_headers if row.get(header) == MISSING_LABEL
            ),
        },
    )
    review_dois = [
        str(row.get("Review_DOI", "")).strip()
        for row in flat_rows
        if str(row.get("Review_DOI", "")).strip() != MISSING_LABEL
    ]
    check(
        "manual_residual_is_doi_only",
        review_dois == ["10.1109/tcbb.2022.3168189"],
        {"review_dois": review_dois},
    )
    check(
        "serpapi_query_policy_recorded",
        len(serpapi_rows) == expected_serpapi_rows
        and all(row.get("SerpAPI_Status") == "success" for row in serpapi_rows),
        {"all_dois": serpapi_all_dois, "expected_rows": expected_serpapi_rows, "queried_rows": len(serpapi_rows), "resolved_rows": len(serpapi_resolved_rows), "rows": serpapi_summary},
    )

    coverage_arithmetic = []
    coverage_arithmetic_ok = True
    for row in coverage_rows:
        try:
            breakdown = json.loads(row.get("Status_Breakdown", "{}"))
            request_count = int(row.get("Requests", "0"))
            total_breakdown = sum(int(value) for value in breakdown.values())
            matches = request_count == total_breakdown
        except (TypeError, ValueError, json.JSONDecodeError):
            breakdown = {}
            request_count = -1
            total_breakdown = -2
            matches = False
        coverage_arithmetic.append(
            {
                "source": row.get("Source", ""),
                "requests": request_count,
                "status_breakdown_total": total_breakdown,
                "passed": matches,
            }
        )
        coverage_arithmetic_ok = coverage_arithmetic_ok and matches
    check("source_coverage_arithmetic", coverage_arithmetic_ok, coverage_arithmetic)
    check(
        "coverage_export_matches_source_coverage",
        coverage_headers == exported_coverage_headers and coverage_rows == exported_coverage_rows,
        {"source_rows": len(coverage_rows), "exported_rows": len(exported_coverage_rows)},
    )

    input_hash_checks = {}
    for name, record in manifest.get("input_files", {}).items():
        path = Path(record["path"])
        actual = sha256_file(path) if path.exists() else None
        input_hash_checks[name] = {
            "path": str(path),
            "expected_sha256": record.get("sha256"),
            "actual_sha256": actual,
            "passed": actual == record.get("sha256"),
        }
    check(
        "input_hashes_match_run_manifest",
        bool(input_hash_checks) and all(item["passed"] for item in input_hash_checks.values()),
        input_hash_checks,
    )

    artifact_paths = [FLAT, EXPORTED_COVERAGE, XLSX, ROLE, MANIFEST, FLAT_MANIFEST]
    artifact_hashes = {str(path.relative_to(REPO)): sha256_file(path) for path in artifact_paths}
    expected_result_hashes = {item["path"]: item["sha256"] for item in flat_manifest.get("result_files", [])}
    expected_coverage_hashes = {item["path"]: item["sha256"] for item in flat_manifest.get("coverage_files", [])}
    result_hash_ok = expected_result_hashes.get(str(FLAT)) == artifact_hashes[str(FLAT.relative_to(REPO))]
    coverage_hash_ok = expected_coverage_hashes.get(str(EXPORTED_COVERAGE)) == artifact_hashes[str(EXPORTED_COVERAGE.relative_to(REPO))]
    check(
        "flat_export_hashes_match_manifest",
        result_hash_ok and coverage_hash_ok,
        {"result_hash_ok": result_hash_ok, "coverage_hash_ok": coverage_hash_ok},
    )
    check(
        "raw_cache_inventory_available",
        raw_inventory["raw_cache_file_count"] > 0,
        {
            "raw_cache_file_count": raw_inventory["raw_cache_file_count"],
            "manifest_new_response_file_count": manifest.get("raw_response_files"),
            "interpretation": "The raw directory is cumulative; the manifest count is the response-save count recorded for that run.",
        },
    )

    try:
        sheets = xlsx_sheet_names(XLSX)
        xlsx_ok = sheets == ["Results", "Source_Coverage"]
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        sheets = []
        xlsx_ok = False
    check("xlsx_has_only_results_and_coverage", xlsx_ok, {"sheets": sheets})
    pipeline_text = PIPELINE.read_text(encoding="utf-8")
    check(
        "pipeline_default_includes_crossref",
        bool(re.search(r"default=\[.*?\"crossref\"", pipeline_text, flags=re.DOTALL)),
        {"pipeline": str(PIPELINE), "crossref_in_default_sources": "crossref" in pipeline_text},
    )
    code_hashes = {
        str(path.relative_to(REPO)): sha256_file(path)
        for path in [PIPELINE, FLAT_BUILDER, XLSX_BUILDER, Path(__file__)]
    }

    credential_values = read_env_keys(ENV_FILE)
    scanned_paths = [path for path in RUN_DIR.rglob("*") if path.is_file() and path != AUDIT]
    credential_hits = []
    for path in scanned_paths:
        payload = path.read_bytes()
        for key, value in credential_values.items():
            if len(value) >= 8 and value.encode("utf-8") in payload:
                credential_hits.append({"file": str(path.relative_to(RUN_DIR)), "key": key})
    check(
        "credential_values_absent_from_outputs",
        not credential_hits and manifest.get("credentials", {}).get("credentials_written_to_outputs") is False,
        {"credential_hit_count": len(credential_hits), "credential_keys_checked": sorted(credential_values)},
    )
    check(
        "run_declares_local_only_changes",
        manifest.get("manual_review_policy", {}).get("canonical_review_data_modified") is False
        and manifest.get("manual_review_policy", {}).get("github_modified") is False,
        manifest.get("manual_review_policy", {}),
    )

    status = "PASS" if all(item["passed"] for item in checks) else "FAIL"
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "mode": "offline_cache_and_artifact_audit",
        "network_calls_made": False,
        "scope": "MRI multi-source scientometric adapter and flat CSV/XLSX export",
        "missing_value_label": MISSING_LABEL,
        "removed_no_information_columns": sorted(removed),
        "integrated_ieee_columns": flat_manifest.get("integrated_ieee_columns", []),
        "excluded_ieee_columns": flat_manifest.get("excluded_ieee_columns", []),
        "manual_residual_dois": review_dois,
        "serpapi_refresh": {
            "all_dois": serpapi_all_dois,
            "expected_rows": expected_serpapi_rows,
            "queried_rows": len(serpapi_rows),
            "successful_rows": sum(1 for row in serpapi_rows if row.get("SerpAPI_Status") == "success"),
            "resolved_rows": len(serpapi_resolved_rows),
            "rows": serpapi_summary,
        },
        "checks": checks,
        "code_hashes": code_hashes,
        "artifact_hashes": artifact_hashes,
        "raw_cache_inventory": str(RAW_INVENTORY.relative_to(REPO)),
        "limitations": [
            "This audit reads cached responses and generated artifacts; it does not re-query providers.",
            "Scopus remains an authentication/access error and was stopped after the first request.",
            "Provider metadata is candidate evidence unless a publication-level role or affiliation is explicit.",
        ],
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "checks": len(checks), "failed": [item["name"] for item in checks if not item["passed"]], "audit": str(AUDIT), "raw_cache_files": raw_inventory["raw_cache_file_count"]}, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
