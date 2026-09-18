"""Reproducible scientometric enrichment for the MRI review corpus.

This adapter reuses the DOI reconciliation, cached API retrieval, authorship
role extraction, and coverage-audit ideas from the generic scientometric tool.
It is deliberately MRI-specific at the input/output boundary and does not
rewrite review-derived variables such as LMIC score, quality, TR, architecture,
field strength, or performance metrics.

The primary run uses OpenAlex and a cached World Bank country snapshot. It does
not read .env files and does not call Genderize, Azure, Scopus, or Google
Scholar. Affiliation country is treated as institutional metadata, not author
nationality or evidence of clinical deployment.
"""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import hashlib
import json
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests
from docx import Document


OPENALEX_TEMPLATE = "https://api.openalex.org/works/https://doi.org/{doi}"
WORLD_BANK_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
UNKNOWN_CODES = {"", "NAN", "NONE", "UNKNOWN", "NULL"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_doi(value: object) -> str:
    """Normalize a DOI without guessing or changing its identity."""

    if value is None or pd.isna(value):
        return ""
    doi = str(value).strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(" .;,)")


def split_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [
        code.strip().upper()
        for code in str(value).split("|")
        if code.strip().upper() not in UNKNOWN_CODES
    ]


def join_unique(values: Iterable[str]) -> str:
    return "|".join(sorted({value for value in values if value}))


def normalized_title(value: object) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", str(value).lower())


def title_similarity(left: object, right: object) -> float:
    return round(
        SequenceMatcher(None, normalized_title(left), normalized_title(right)).ratio(),
        4,
    )


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def read_source(path: Path) -> pd.DataFrame:
    source = pd.read_excel(path, sheet_name="data-clean")
    required = {"Paper_ID", "Title", "Year"}
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"Source Excel is missing columns: {sorted(missing)}")
    source = source.copy()
    source["Paper_ID"] = pd.to_numeric(source["Paper_ID"], errors="raise").astype(int)
    if source["Paper_ID"].duplicated().any():
        raise ValueError("Source Excel contains duplicated Paper_ID values")
    return source.sort_values("Paper_ID").reset_index(drop=True)


def read_supplementary_geography(path: Path, study_count: int) -> pd.DataFrame:
    """Read Table 8 and align its sequential rows to sorted Paper_ID values."""

    document = Document(path)
    candidates = []
    for table_index, table in enumerate(document.tables):
        if not table.rows:
            continue
        header = " | ".join(cell.text.strip() for cell in table.rows[0].cells)
        if "First Author Country" in header and (
            "Corresponding" in header or "Corr." in header
        ):
            candidates.append((table_index, table))
    if len(candidates) != 1:
        raise ValueError(
            "Expected exactly one supplementary geography table with first and "
            f"corresponding author country columns; found {len(candidates)}"
        )
    _, table = candidates[0]
    rows = [
        [cell.text.replace("\n", " ").strip() for cell in row.cells]
        for row in table.rows[1:]
    ]
    expected = [
        "Supplement_Sequence",
        "Supplement_Year",
        "Supplement_Title",
        "First_Author_Country",
        "First_Author_WB_Group",
        "First_Author_Equity",
        "Corresponding_Author_Country",
        "Corresponding_Author_Equity",
    ]
    if any(len(row) != len(expected) for row in rows):
        raise ValueError("Supplementary geography table has an unexpected width")
    geography = pd.DataFrame(rows, columns=expected)
    geography["Supplement_Sequence"] = pd.to_numeric(
        geography["Supplement_Sequence"], errors="raise"
    ).astype(int)
    expected_sequence = list(range(1, study_count + 1))
    if geography["Supplement_Sequence"].tolist() != expected_sequence:
        raise ValueError("Supplementary geography sequence is not 1..N")
    return geography


def read_doi_map(path: Path, source_ids: set[int]) -> pd.DataFrame:
    doi_map = pd.read_csv(path)
    required = {"Paper_ID", "DOI"}
    missing = required - set(doi_map.columns)
    if missing:
        raise ValueError(f"DOI map is missing columns: {sorted(missing)}")
    doi_map = doi_map.copy()
    doi_map["Paper_ID"] = pd.to_numeric(doi_map["Paper_ID"], errors="raise").astype(int)
    doi_map["DOI"] = doi_map["DOI"].map(normalize_doi)
    if set(doi_map["Paper_ID"]) != source_ids:
        raise ValueError("DOI map Paper_ID values do not match the canonical source")
    if doi_map["DOI"].eq("").any() or doi_map["DOI"].duplicated().any():
        raise ValueError("DOI map must contain one non-empty, unique DOI per study")
    return doi_map.sort_values("Paper_ID").reset_index(drop=True)


def load_or_fetch_work(
    session: requests.Session,
    paper_id: int,
    doi: str,
    raw_dir: Path,
    contact_email: str | None,
    attempts: int = 3,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    raw_path = raw_dir / f"paper_{paper_id:02d}.json"
    if raw_path.exists():
        try:
            return json.loads(raw_path.read_text(encoding="utf-8")), {
                "Paper_ID": paper_id,
                "DOI": doi,
                "HTTP_Status": 200,
                "Request_Status": "cached",
                "Retrieved_At_UTC": now_utc(),
                "Request_URL": OPENALEX_TEMPLATE.format(doi=doi),
            }
        except json.JSONDecodeError:
            raw_path.unlink(missing_ok=True)

    headers = {"User-Agent": "MRI-LMICs scientometric adapter/1.0"}
    if contact_email:
        headers["User-Agent"] += f" (mailto:{contact_email})"
    url = OPENALEX_TEMPLATE.format(doi=doi)
    last_error = ""
    status: int | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, headers=headers, timeout=30)
            status = response.status_code
            if status == 200:
                data = response.json()
                raw_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return data, {
                    "Paper_ID": paper_id,
                    "DOI": doi,
                    "HTTP_Status": status,
                    "Request_Status": "fetched",
                    "Retrieved_At_UTC": now_utc(),
                    "Request_URL": url,
                }
            last_error = response.text[:300]
            if status != 429:
                break
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(1.5 * attempt)
    return None, {
        "Paper_ID": paper_id,
        "DOI": doi,
        "HTTP_Status": status,
        "Request_Status": "error",
        "Error": last_error,
        "Retrieved_At_UTC": now_utc(),
        "Request_URL": url,
    }


def extract_openalex(
    source: pd.DataFrame,
    doi_map: pd.DataFrame,
    output_dir: Path,
    contact_email: str | None,
    offline: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_dir = output_dir / "raw_openalex_works"
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    works: list[dict[str, Any]] = []
    authors: list[dict[str, Any]] = []
    requests_log: list[dict[str, Any]] = []
    doi_by_id = doi_map.set_index("Paper_ID")["DOI"].to_dict()

    for position, row in source.iterrows():
        paper_id = int(row["Paper_ID"])
        doi = doi_by_id[paper_id]
        if offline:
            raw_path = raw_dir / f"paper_{paper_id:02d}.json"
            if not raw_path.exists():
                data = None
                request_log = {
                    "Paper_ID": paper_id,
                    "DOI": doi,
                    "HTTP_Status": None,
                    "Request_Status": "missing_offline_cache",
                    "Error": str(raw_path),
                    "Retrieved_At_UTC": now_utc(),
                    "Request_URL": OPENALEX_TEMPLATE.format(doi=doi),
                }
            else:
                data, request_log = load_or_fetch_work(
                    session, paper_id, doi, raw_dir, contact_email
                )
        else:
            data, request_log = load_or_fetch_work(
                session, paper_id, doi, raw_dir, contact_email
            )
        requests_log.append(request_log)
        if data is None:
            continue

        authorships = data.get("authorships") or []
        author_country_values = []
        institution_values = []
        for authorship in authorships:
            author_country_values.extend(authorship.get("countries") or [])
            institution_values.extend(
                item.get("id", "") for item in (authorship.get("institutions") or [])
            )
        countries_distinct = join_unique(author_country_values)
        institutions_distinct = join_unique(institution_values)
        primary_location = data.get("primary_location") or {}
        primary_source = primary_location.get("source") or {}
        open_access = data.get("open_access") or {}
        best_oa = data.get("best_oa_location") or {}
        retrieved = request_log["Retrieved_At_UTC"]
        works.append(
            {
                "Paper_ID": paper_id,
                "DOI": doi,
                "Input_Title": row["Title"],
                "Input_Year": row["Year"],
                "OpenAlex_ID": data.get("id"),
                "OpenAlex_Title": data.get("title"),
                "OpenAlex_Year": data.get("publication_year"),
                "OpenAlex_Type": data.get("type"),
                "Cited_By_Count": data.get("cited_by_count"),
                "Referenced_Works_Count": len(data.get("referenced_works") or []),
                "Authors_Count": len(authorships),
                "Institution_Count": len(split_codes(institutions_distinct)),
                "Country_Count": len(split_codes(countries_distinct)),
                "Countries_Distinct": countries_distinct,
                "Is_OA": open_access.get("is_oa"),
                "OA_Status": open_access.get("oa_status"),
                "Best_OA_URL": best_oa.get("landing_page_url")
                or best_oa.get("pdf_url"),
                "Primary_Source": primary_source.get("display_name"),
                "Primary_Source_Type": primary_source.get("type"),
                "Retrieved_At_UTC": retrieved,
                "HTTP_Status": request_log.get("HTTP_Status"),
            }
        )
        for author_order, authorship in enumerate(authorships, start=1):
            author = authorship.get("author") or {}
            institutions = authorship.get("institutions") or []
            authors.append(
                {
                    "Paper_ID": paper_id,
                    "DOI": doi,
                    "Author_Order": author_order,
                    "Author_ID": author.get("id"),
                    "Author_Name": author.get("display_name"),
                    "ORCID": author.get("orcid"),
                    "Author_Position": authorship.get("author_position"),
                    "Is_Corresponding": authorship.get("is_corresponding"),
                    "Affiliation_Countries": join_unique(
                        authorship.get("countries") or []
                    ),
                    "Institution_IDs": join_unique(
                        item.get("id", "") for item in institutions
                    ),
                    "Institution_Names": join_unique(
                        item.get("display_name", "") for item in institutions
                    ),
                    "Retrieved_At_UTC": retrieved,
                }
            )
        if not offline:
            time.sleep(0.12)
        print(f"[{position + 1}/{len(source)}] Paper_ID={paper_id}: {len(authorships)} authors")

    works_df = pd.DataFrame(works).sort_values("Paper_ID")
    authors_df = pd.DataFrame(authors).sort_values(["Paper_ID", "Author_Order"])
    requests_df = pd.DataFrame(requests_log).sort_values("Paper_ID")
    works_df.to_csv(output_dir / "openalex_works.csv", index=False, encoding="utf-8-sig")
    authors_df.to_csv(
        output_dir / "openalex_authorships.csv", index=False, encoding="utf-8-sig"
    )
    requests_df.to_csv(
        output_dir / "openalex_requests.csv", index=False, encoding="utf-8-sig"
    )
    return works_df, authors_df, requests_df


def load_world_bank_snapshot(output_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    snapshot_path = output_dir / "world_bank_countries_raw.json"
    if snapshot_path.exists():
        wrapper = json.loads(snapshot_path.read_text(encoding="utf-8"))
        payload = wrapper["response"]
    else:
        response = requests.get(
            WORLD_BANK_URL,
            headers={"User-Agent": "MRI-LMICs scientometric adapter/1.0"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        snapshot_path.write_text(
            json.dumps(
                {
                    "retrieved_at_utc": now_utc(),
                    "endpoint": WORLD_BANK_URL,
                    "response": payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    income: dict[str, str] = {}
    names: dict[str, str] = {}
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("World Bank response has an unexpected shape")
    for country in payload[1]:
        code = str(country.get("iso2Code") or "").upper()
        income_id = (country.get("incomeLevel") or {}).get("id")
        income[code] = {
            "HIC": "HIC",
            "UMC": "UMIC",
            "LMC": "LMIC",
            "LIC": "LIC",
        }.get(income_id, "UNKNOWN")
        names[code] = country.get("name", "")
    return income, names


def income_groups(codes: Iterable[str], income: dict[str, str]) -> list[str]:
    return sorted({income.get(code, "UNKNOWN") for code in codes})


def collaboration_category(groups: list[str], countries: list[str]) -> str:
    if not countries:
        return "Unknown affiliations only"
    if groups == ["HIC"]:
        return "HIC-only known affiliations"
    if "HIC" in groups and any(group in groups for group in ("LMIC", "LIC")):
        return "Mixed HIC + LMIC/LIC"
    if "HIC" in groups and "UMIC" in groups:
        return "Mixed HIC + UMIC"
    if "UNKNOWN" in groups:
        return "Known income + unknown affiliations"
    return "Global South only known affiliations"


def build_analysis(
    source: pd.DataFrame,
    geography: pd.DataFrame,
    doi_map: pd.DataFrame,
    works: pd.DataFrame,
    authors: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    income, country_names = load_world_bank_snapshot(output_dir)
    source = source.copy()
    source["Supplement_Sequence"] = range(1, len(source) + 1)
    source = source.merge(geography, on="Supplement_Sequence", how="left")
    source = source.merge(doi_map[["Paper_ID", "DOI"]], on="Paper_ID", how="left")
    public_source = source.drop(columns=["Reviewer_Name", "Assigned_Reviewer"], errors="ignore")
    public_source.to_csv(output_dir / "review_metadata_joined.csv", index=False, encoding="utf-8-sig")
    alignment = public_source[
        ["Paper_ID", "Supplement_Sequence", "Title", "Supplement_Title"]
    ].copy()
    alignment["Title_Similarity"] = [
        title_similarity(left, right)
        for left, right in zip(alignment["Title"], alignment["Supplement_Title"])
    ]
    alignment["Alignment_Method"] = "sorted source Paper_ID to supplementary sequence"
    alignment["Low_Similarity_Flag"] = alignment["Title_Similarity"].lt(0.5)
    alignment.to_csv(
        output_dir / "supplement_alignment_audit.csv",
        index=False,
        encoding="utf-8-sig",
    )

    paper_geo: list[dict[str, Any]] = []
    exploded: list[dict[str, Any]] = []
    leadership: list[dict[str, Any]] = []
    for paper_id, group in authors.groupby("Paper_ID", sort=True):
        group = group.sort_values("Author_Order")
        all_countries: list[str] = []
        for value in group["Affiliation_Countries"]:
            all_countries.extend(split_codes(value))
        first = group[group["Author_Position"].eq("first")].head(1)
        last = group[group["Author_Position"].eq("last")].head(1)
        corresponding = group[group["Is_Corresponding"].map(bool_value)]
        first_countries = (
            split_codes(first.iloc[0]["Affiliation_Countries"]) if len(first) else []
        )
        last_countries = (
            split_codes(last.iloc[0]["Affiliation_Countries"]) if len(last) else []
        )
        corresponding_countries: list[str] = []
        for value in corresponding["Affiliation_Countries"]:
            corresponding_countries.extend(split_codes(value))
        groups = income_groups(all_countries, income)
        known_author_count = sum(
            bool(split_codes(value)) for value in group["Affiliation_Countries"]
        )
        paper_geo.append(
            {
                "Paper_ID": int(paper_id),
                "OpenAlex_All_Countries": join_unique(all_countries),
                "OpenAlex_All_Income_Groups": join_unique(groups),
                "Known_Author_Affiliation_Count": known_author_count,
                "Total_Author_Count": len(group),
                "First_Author_OpenAlex_Countries": join_unique(first_countries),
                "First_Author_OpenAlex_Income_Groups": join_unique(
                    income_groups(first_countries, income)
                ),
                "Last_Author_OpenAlex_Countries": join_unique(last_countries),
                "Corresponding_Author_OpenAlex_Countries": join_unique(
                    corresponding_countries
                ),
                "Corresponding_Author_OpenAlex_Income_Groups": join_unique(
                    income_groups(corresponding_countries, income)
                ),
                "Collaboration_Category": collaboration_category(groups, all_countries),
            }
        )
        for _, author in group.iterrows():
            countries = split_codes(author["Affiliation_Countries"])
            for country in countries:
                exploded.append(
                    {
                        "Paper_ID": int(paper_id),
                        "Country": country,
                        "Country_Name": country_names.get(country, ""),
                        "Income_Group": income.get(country, "UNKNOWN"),
                        "Author_ID": author["Author_ID"],
                        "Author_Name": author["Author_Name"],
                        "Author_Position": author["Author_Position"],
                        "Is_Corresponding": bool_value(author["Is_Corresponding"]),
                    }
                )
        for role, subset in (
            ("first", first),
            ("last", last),
            ("corresponding", corresponding),
        ):
            for _, author in subset.iterrows():
                for country in split_codes(author["Affiliation_Countries"]):
                    leadership.append(
                        {
                            "Paper_ID": int(paper_id),
                            "Author_Role": role,
                            "Country": country,
                            "Income_Group": income.get(country, "UNKNOWN"),
                            "Author_ID": author["Author_ID"],
                            "Author_Name": author["Author_Name"],
                        }
                    )

    paper_geo_df = pd.DataFrame(paper_geo).sort_values("Paper_ID")
    country_affiliations = pd.DataFrame(exploded)
    leadership_df = pd.DataFrame(leadership)
    paper = public_source.merge(works, on=["Paper_ID", "DOI"], how="left").merge(
        paper_geo_df, on="Paper_ID", how="left"
    )
    paper.to_csv(
        output_dir / "paper_geography_and_impact.csv", index=False, encoding="utf-8-sig"
    )
    country_affiliations.to_csv(
        output_dir / "author_country_affiliations.csv",
        index=False,
        encoding="utf-8-sig",
    )
    leadership_df.to_csv(
        output_dir / "leadership_country_roles.csv", index=False, encoding="utf-8-sig"
    )

    country_rows = []
    if not country_affiliations.empty:
        for country, group in country_affiliations.groupby("Country"):
            country_rows.append(
                {
                    "Country": country,
                    "Country_Name": country_names.get(country, ""),
                    "Income_Group": income.get(country, "UNKNOWN"),
                    "Paper_Count": group["Paper_ID"].nunique(),
                    "Author_Affiliation_Count": len(group),
                    "First_Author_Paper_Count": group.loc[
                        group["Author_Position"].eq("first"), "Paper_ID"
                    ].nunique(),
                    "Last_Author_Paper_Count": group.loc[
                        group["Author_Position"].eq("last"), "Paper_ID"
                    ].nunique(),
                    "Corresponding_Author_Paper_Count": group.loc[
                        group["Is_Corresponding"], "Paper_ID"
                    ].nunique(),
                }
            )
    country_summary = pd.DataFrame(country_rows).sort_values(
        ["Paper_Count", "Author_Affiliation_Count", "Country"],
        ascending=[False, False, True],
    )
    country_summary.to_csv(
        output_dir / "country_summary.csv", index=False, encoding="utf-8-sig"
    )

    collaboration = paper_geo_df["Collaboration_Category"].value_counts().rename_axis(
        "Collaboration_Category"
    ).reset_index(name="Paper_Count")
    collaboration["Percent"] = (
        collaboration["Paper_Count"] / len(source) * 100
    ).round(1)
    collaboration.to_csv(
        output_dir / "collaboration_summary.csv", index=False, encoding="utf-8-sig"
    )

    role_rows = []
    for role, column in (
        ("first", "First_Author_OpenAlex_Countries"),
        ("last", "Last_Author_OpenAlex_Countries"),
        ("corresponding", "Corresponding_Author_OpenAlex_Countries"),
    ):
        known = paper_geo_df[column].fillna("").ne("")
        role_rows.append(
            {
                "Author_Role": role,
                "Studies": len(paper_geo_df),
                "Known_Country": int(known.sum()),
                "Missing_Country": int((~known).sum()),
                "Coverage_Percent": round(float(known.mean() * 100), 1),
            }
        )
    pd.DataFrame(role_rows).to_csv(
        output_dir / "author_role_summary.csv", index=False, encoding="utf-8-sig"
    )

    year = paper[
        ["Paper_ID", "DOI", "Input_Year", "OpenAlex_Year", "Input_Title", "OpenAlex_Title"]
    ].copy()
    year["Year_Match"] = year["Input_Year"].eq(year["OpenAlex_Year"])
    year.to_csv(output_dir / "year_reconciliation.csv", index=False, encoding="utf-8-sig")

    country_pair_count = len(country_affiliations)
    known_papers = paper_geo_df["OpenAlex_All_Countries"].fillna("").ne("")
    coverage = pd.DataFrame(
        [
            {
                "Metric": "Source studies in latest Excel",
                "Count": len(source),
                "Denominator": len(source),
                "Percent": 100.0,
            },
            {
                "Metric": "Verified DOI mappings",
                "Count": int(doi_map["DOI"].ne("").sum()),
                "Denominator": len(source),
                "Percent": round(doi_map["DOI"].ne("").mean() * 100, 1),
            },
            {
                "Metric": "OpenAlex works retrieved",
                "Count": int(works["Paper_ID"].nunique()),
                "Denominator": len(source),
                "Percent": round(works["Paper_ID"].nunique() / len(source) * 100, 1),
            },
            {
                "Metric": "Authorship records retrieved",
                "Count": len(authors),
                "Denominator": "",
                "Percent": "",
            },
            {
                "Metric": "Author-country affiliation pairs",
                "Count": country_pair_count,
                "Denominator": len(authors),
                "Percent": round(country_pair_count / len(authors) * 100, 1),
            },
            {
                "Metric": "Papers with at least one known author country",
                "Count": int(known_papers.sum()),
                "Denominator": len(source),
                "Percent": round(known_papers.mean() * 100, 1),
            },
            {
                "Metric": "Papers with first-author country",
                "Count": int(
                    paper_geo_df["First_Author_OpenAlex_Countries"].fillna("").ne("").sum()
                ),
                "Denominator": len(source),
                "Percent": round(
                    paper_geo_df["First_Author_OpenAlex_Countries"].fillna("").ne("").mean()
                    * 100,
                    1,
                ),
            },
            {
                "Metric": "Papers with corresponding-author country",
                "Count": int(
                    paper_geo_df[
                        "Corresponding_Author_OpenAlex_Countries"
                    ].fillna("").ne("").sum()
                ),
                "Denominator": len(source),
                "Percent": round(
                    paper_geo_df[
                        "Corresponding_Author_OpenAlex_Countries"
                    ].fillna("").ne("").mean()
                    * 100,
                    1,
                ),
            },
            {
                "Metric": "OpenAlex OA papers",
                "Count": int(works["Is_OA"].fillna(False).map(bool_value).sum()),
                "Denominator": len(source),
                "Percent": round(
                    works["Is_OA"].fillna(False).map(bool_value).mean() * 100, 1
                ),
            },
        ]
    )
    coverage.to_csv(output_dir / "metadata_coverage.csv", index=False, encoding="utf-8-sig")

    # Explicit audit of missing/unknown metadata.  Unknown values are retained
    # as unknown and are never converted into a country, income group, or
    # corresponding-author assignment by default.
    unknown_rows: list[dict[str, Any]] = []
    unknown_records: list[dict[str, Any]] = []

    def add_unknown_metric(metric: str, count: int, denominator: int, action: str) -> None:
        unknown_rows.append(
            {
                "Metric": metric,
                "Count": int(count),
                "Denominator": int(denominator),
                "Percent": round((count / denominator * 100) if denominator else 0.0, 1),
                "Action": action,
            }
        )

    first_wb = source["First_Author_WB_Group"].fillna("").astype(str).str.upper()
    corresponding_equity = source["Corresponding_Author_Equity"].fillna("").astype(str).str.upper()
    add_unknown_metric(
        "Supplementary first-author income group UNKNOWN",
        int(first_wb.str.contains("UNKNOWN|NOT REPORTED", regex=True).sum()),
        len(source),
        "Retain UNKNOWN; do not infer income group from author name or study location.",
    )
    add_unknown_metric(
        "Supplementary corresponding-author equity UNKNOWN/manual review",
        int(corresponding_equity.str.contains("UNKNOWN|MANUAL REVIEW|NOT REPORTED", regex=True).sum()),
        len(source),
        "Retain manual-review status; do not infer corresponding-author role from first/last author.",
    )

    first_openalex_missing = paper_geo_df["First_Author_OpenAlex_Countries"].fillna("").eq("")
    corr_openalex_missing = paper_geo_df["Corresponding_Author_OpenAlex_Countries"].fillna("").eq("")
    add_unknown_metric(
        "OpenAlex first-author country missing",
        int(first_openalex_missing.sum()),
        len(paper_geo_df),
        "Retain missing; no country imputation.",
    )
    add_unknown_metric(
        "OpenAlex corresponding-author country missing",
        int(corr_openalex_missing.sum()),
        len(paper_geo_df),
        "Retain missing because OpenAlex corresponding flags are incomplete.",
    )
    add_unknown_metric(
        "OpenAlex work-level country metadata missing",
        int(works["Countries_Distinct"].fillna("").eq("").sum()),
        len(works),
        "Derived from authorship affiliations in the corrected run; zero is expected only after derivation succeeds.",
    )
    add_unknown_metric(
        "OpenAlex work-level OA status missing",
        int(works["OA_Status"].fillna("").astype(str).eq("").sum()),
        len(works),
        "Retain missing OA status; do not equate missing with closed or open.",
    )
    add_unknown_metric(
        "Author-country income group UNKNOWN",
        int((country_affiliations["Income_Group"] == "UNKNOWN").sum()) if not country_affiliations.empty else 0,
        len(country_affiliations),
        "Retain UNKNOWN when World Bank country mapping is unavailable.",
    )
    add_unknown_metric(
        "Supplementary title alignment below 0.5",
        int(alignment["Low_Similarity_Flag"].sum()),
        len(alignment),
        "Manual title alignment review required before using the supplementary geography join.",
    )
    add_unknown_metric(
        "Source/OpenAlex publication year mismatch",
        int((~year["Year_Match"]).sum()),
        len(year),
        "Keep both years and report the reconciliation; do not silently replace the review year.",
    )

    for _, row in source.loc[first_wb.str.contains("UNKNOWN|NOT REPORTED", regex=True)].iterrows():
        unknown_records.append(
            {
                "Paper_ID": int(row["Paper_ID"]),
                "Field": "Supplementary_First_Author_WB_Group",
                "Value": row["First_Author_WB_Group"],
                "Reason": "source geography table does not provide a resolved income group",
            }
        )
    for _, row in source.loc[corresponding_equity.str.contains("UNKNOWN|MANUAL REVIEW|NOT REPORTED", regex=True)].iterrows():
        unknown_records.append(
            {
                "Paper_ID": int(row["Paper_ID"]),
                "Field": "Supplementary_Corresponding_Author_Equity",
                "Value": row["Corresponding_Author_Equity"],
                "Reason": "source geography table marks this role/equity classification for manual review",
            }
        )
    for _, row in paper_geo_df.loc[first_openalex_missing].iterrows():
        unknown_records.append(
            {
                "Paper_ID": int(row["Paper_ID"]),
                "Field": "OpenAlex_First_Author_Country",
                "Value": "",
                "Reason": "no OpenAlex affiliation country for the first-author record",
            }
        )
    for _, row in paper_geo_df.loc[corr_openalex_missing].iterrows():
        unknown_records.append(
            {
                "Paper_ID": int(row["Paper_ID"]),
                "Field": "OpenAlex_Corresponding_Author_Country",
                "Value": "",
                "Reason": "no OpenAlex corresponding-author flag/country",
            }
        )
    pd.DataFrame(unknown_rows).to_csv(
        output_dir / "scientometric_unknown_audit.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(unknown_records).sort_values(["Paper_ID", "Field"]).to_csv(
        output_dir / "scientometric_unknown_records.csv", index=False, encoding="utf-8-sig"
    )

    summary: dict[str, Any] = {
        "run_timestamp_utc": now_utc(),
        "source_studies": int(len(source)),
        "doi_mappings": int(doi_map["DOI"].ne("").sum()),
        "openalex_works": int(works["Paper_ID"].nunique()),
        "authorship_records": int(len(authors)),
        "author_country_affiliation_pairs": int(country_pair_count),
        "year_mismatches": int((~year["Year_Match"]).sum()),
        "citations_median": float(works["Cited_By_Count"].median()),
        "citations_iqr": [
            float(works["Cited_By_Count"].quantile(0.25)),
            float(works["Cited_By_Count"].quantile(0.75)),
        ],
        "oa_papers": int(works["Is_OA"].fillna(False).map(bool_value).sum()),
        "openalex_country_codes": sorted(country_affiliations["Country"].unique()),
        "collaboration_categories": collaboration.set_index(
            "Collaboration_Category"
        )["Paper_Count"].to_dict(),
        "first_author_income_source": source[
            "First_Author_WB_Group"
        ].value_counts(dropna=False).to_dict(),
        "corresponding_author_equity_source": source[
            "Corresponding_Author_Equity"
        ].value_counts(dropna=False).to_dict(),
        "year_reconciliation": {
            "source_year_column": "Year",
            "openalex_year_column": "OpenAlex_Year",
            "mismatched_studies": int((~year["Year_Match"]).sum()),
        },
        "unknown_metadata_audit": {
            "audit_file": "scientometric_unknown_audit.csv",
            "record_file": "scientometric_unknown_records.csv",
            "openalex_first_author_country_missing": int(first_openalex_missing.sum()),
            "openalex_corresponding_author_country_missing": int(corr_openalex_missing.sum()),
            "openalex_work_country_metadata_missing": int(works["Countries_Distinct"].fillna("").eq("").sum()),
            "supplementary_first_income_unknown": int(first_wb.str.contains("UNKNOWN|NOT REPORTED", regex=True).sum()),
            "supplementary_corresponding_equity_unknown_or_manual": int(corresponding_equity.str.contains("UNKNOWN|MANUAL REVIEW|NOT REPORTED", regex=True).sum()),
        },
        "methodological_boundaries": [
            "Affiliation country is institutional metadata, not author nationality.",
            "Affiliation country is not evidence of clinical deployment or data origin.",
            "Review-derived LMIC score, quality, architecture, field strength, TR, inclusion, and performance metrics are not replaced.",
            "OpenAlex and World Bank values are snapshot-dependent; raw API responses and timestamps are retained.",
        ],
    }
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument("--supplementary-docx", type=Path, required=True)
    parser.add_argument("--doi-map", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contact-email", default=None)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Only use raw OpenAlex JSON already present in output-dir/raw_openalex_works",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Write partial outputs instead of failing when an OpenAlex work is missing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = read_source(args.input_xlsx)
    geography = read_supplementary_geography(args.supplementary_docx, len(source))
    doi_map = read_doi_map(args.doi_map, set(source["Paper_ID"]))
    doi_map.to_csv(args.output_dir / "doi_resolution.csv", index=False, encoding="utf-8-sig")
    works, authors, requests_log = extract_openalex(
        source,
        doi_map,
        args.output_dir,
        args.contact_email,
        args.offline,
    )
    errors = requests_log[requests_log["Request_Status"].eq("error")]
    missing = set(source["Paper_ID"]) - set(works["Paper_ID"])
    if (not errors.empty or missing) and not args.allow_missing:
        raise RuntimeError(
            f"OpenAlex retrieval incomplete: {len(missing)} missing studies; "
            "rerun with --allow-missing only for a diagnostic partial run"
        )
    summary = build_analysis(
        source,
        geography,
        doi_map,
        works,
        authors,
        args.output_dir,
    )
    summary["openalex_request_errors"] = int(len(errors))
    summary["openalex_missing_studies"] = sorted(int(value) for value in missing)
    (args.output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    manifest = {
        "run_timestamp_utc": now_utc(),
        "script": str(Path(__file__).resolve()),
        "python_version": sys.version,
        "platform": platform.platform(),
        "offline": bool(args.offline),
        "input_files": {
            "source_xlsx": {
                "path": str(args.input_xlsx.resolve()),
                "sha256": sha256_file(args.input_xlsx),
            },
            "supplementary_docx": {
                "path": str(args.supplementary_docx.resolve()),
                "sha256": sha256_file(args.supplementary_docx),
            },
            "doi_map": {
                "path": str(args.doi_map.resolve()),
                "sha256": sha256_file(args.doi_map),
            },
        },
        "api_endpoints": {
            "openalex": OPENALEX_TEMPLATE,
            "world_bank": WORLD_BANK_URL,
        },
        "credentials_used": False,
        "output_dir": str(args.output_dir.resolve()),
        "summary": summary,
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
