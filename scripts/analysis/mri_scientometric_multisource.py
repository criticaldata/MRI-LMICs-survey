"""Optional multi-source metadata enrichment for the 48-study MRI corpus.

This is deliberately separate from the credential-free OpenAlex run.  It
queries only DOI-scoped metadata sources, stores response bodies and hashes
locally, and never changes the canonical review extraction table.  Provider
responses are treated as candidates: author-country and corresponding-author
claims still require paper-level confirmation when the role or affiliation is
not explicit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests


REPO = Path(__file__).resolve().parents[2]
OPENALEX_AUTHORS = REPO / "analysis" / "scientometrics" / "openalex_20260803" / "openalex_authorships.csv"
REVIEW_METADATA = REPO / "analysis" / "scientometrics" / "openalex_20260803" / "review_metadata_joined.csv"
WORLD_BANK = REPO / "analysis" / "scientometrics" / "openalex_20260803" / "world_bank_countries_raw.json"
DEFAULT_ENV = Path(r"C:\Users\Pc\Desktop\MIT\Scientometric Analysis Tool\SCIENTOMETRIC ANALYSIS TOOL\.env")
DEFAULT_OUTPUT = REPO / "analysis" / "scientometrics" / "multisource_20260803"

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPEPMC_FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
SERPAPI_SEARCH = "https://serpapi.com/search.json"
SEMANTIC_PAPER = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
CROSSREF_WORK = "https://api.crossref.org/works/{doi}"
ELSEVIER_ABSTRACT = "https://api.elsevier.com/content/abstract/doi/{doi}"
IEEE_CSDL_GRAPHQL = "https://www.computer.org/csdl/api/v1/graphql"
ORCID_EMPLOYMENTS = "https://pub.orcid.org/v3.0/{orcid}/employments"
ORCID_EDUCATIONS = "https://pub.orcid.org/v3.0/{orcid}/educations"
ORCID_QUALIFICATIONS = "https://pub.orcid.org/v3.0/{orcid}/qualifications"
ORCID_WORKS = "https://pub.orcid.org/v3.0/{orcid}/works"
ORCID_WORK = "https://pub.orcid.org/v3.0/{orcid}/work/{put_code}"
SCOPUS_SEARCH = "https://api.elsevier.com/content/search/scopus"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_env_file(path: Path) -> dict[str, str]:
    """Read only key/value pairs; never print or write their values."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def env_float(values: dict[str, str], key: str, fallback: float) -> float:
    try:
        return max(0.0, float(values.get(key, fallback)))
    except (TypeError, ValueError):
        return fallback


def normalize_doi(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    doi = str(value).strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi.rstrip(" .;,)\"")


def normalize_orcid(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    value = str(value).strip()
    value = re.sub(r"^https?://orcid\.org/", "", value, flags=re.IGNORECASE)
    return value.rstrip("/")


def normalize_name(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def safe_token(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value))[:80]


def save_raw(response: requests.Response, raw_dir: Path, filename: str) -> dict[str, str]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / filename
    path.write_bytes(response.content)
    return {
        "path": path.name,
        "sha256": sha256_bytes(response.content),
        "http_status": str(response.status_code),
        "bytes": str(len(response.content)),
    }


def cached_raw(path: Path, endpoint: str) -> tuple[bytes, dict[str, str]] | None:
    if not path.exists():
        return None
    payload = path.read_bytes()
    return payload, {
        "path": path.name,
        "sha256": sha256_bytes(payload),
        "http_status": "cached",
        "bytes": str(len(payload)),
        "endpoint": endpoint,
    }


def source_status(response: requests.Response) -> str:
    if response.status_code == 404:
        return "not_found"
    if response.status_code == 429:
        return "rate_limited"
    if response.status_code in {401, 403}:
        return "auth_error"
    if response.status_code == 400:
        return "bad_request_or_access_error"
    if response.ok:
        return "http_ok"
    return f"http_{response.status_code}"


def load_country_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    payload = json.loads(WORLD_BANK.read_text(encoding="utf-8"))
    records = payload.get("response", [None, []])[1] or []
    code_to_income: dict[str, str] = {}
    name_to_code: dict[str, str] = {}
    iso3_to_code: dict[str, str] = {}
    for record in records:
        iso2 = str(record.get("iso2Code", "")).upper()
        iso3 = str(record.get("iso3Code") or record.get("id") or "").upper()
        income = str(record.get("incomeLevel", {}).get("id", "")).upper()
        name = str(record.get("name", "")).strip()
        if len(iso2) == 2 and income in {"HIC", "UMC", "LMC", "LIC"}:
            code_to_income[iso2] = income
        if name and len(iso2) == 2:
            name_to_code[name.casefold()] = iso2
        if iso3 and len(iso3) == 3 and len(iso2) == 2:
            iso3_to_code[iso3] = iso2
    aliases = {
        "usa": "US",
        "u.s.a.": "US",
        "u.s.": "US",
        "united states of america": "US",
        "uk": "GB",
        "u.k.": "GB",
        "england": "GB",
        "scotland": "GB",
        "south korea": "KR",
        "republic of korea": "KR",
        "north korea": "KP",
        "iran": "IR",
        "islamic republic of iran": "IR",
        "russia": "RU",
        "russian federation": "RU",
        "turkey": "TR",
        "türkiye": "TR",
        "viet nam": "VN",
        "vietnam": "VN",
        "czech republic": "CZ",
        "czechia": "CZ",
        "the netherlands": "NL",
        "hong kong": "HK",
        "hong kong sar": "HK",
        "hong kong sar, china": "HK",
    }
    for name, code in aliases.items():
        name_to_code[name.casefold()] = code
    return code_to_income, name_to_code, iso3_to_code


def country_candidate(
    value: object,
    name_to_code: dict[str, str],
    iso3_to_code: dict[str, str] | None = None,
) -> tuple[str, str]:
    text = "" if value is None or pd.isna(value) else str(value)
    text = " ".join(text.split())
    if not text:
        return "", ""
    normalized = unicodedata.normalize("NFKD", text).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    for name in sorted(name_to_code, key=len, reverse=True):
        name_norm = unicodedata.normalize("NFKD", name).casefold()
        name_norm = "".join(char for char in name_norm if not unicodedata.combining(char))
        pattern = r"(?<![a-z])" + re.escape(name_norm) + r"(?![a-z])"
        if re.search(pattern, normalized):
            return name_to_code[name], f"affiliation_text:{name}"
    # ISO3 codes are matched only as explicit uppercase tokens. This avoids
    # treating ordinary words such as "and" as the code AND (Andorra).
    for iso3 in sorted(iso3_to_code or {}, key=len, reverse=True):
        pattern = r"(?<![A-Za-z])" + re.escape(iso3) + r"(?![A-Za-z])"
        if re.search(pattern, text):
            return iso3_to_code[iso3], f"affiliation_iso3:{iso3}"
    return "", ""


def country_candidates_all(
    value: object,
    name_to_code: dict[str, str],
    iso3_to_code: dict[str, str] | None = None,
) -> set[str]:
    """Return every country evidenced in an affiliation string."""
    text = "" if value is None or pd.isna(value) else str(value)
    normalized = unicodedata.normalize("NFKD", text).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    found: set[str] = set()
    for name, code in name_to_code.items():
        name_norm = unicodedata.normalize("NFKD", name).casefold()
        name_norm = "".join(char for char in name_norm if not unicodedata.combining(char))
        pattern = r"(?<![a-z])" + re.escape(name_norm) + r"(?![a-z])"
        if re.search(pattern, normalized):
            found.add(code)
    for iso3, code in (iso3_to_code or {}).items():
        if re.search(r"(?<![A-Za-z])" + re.escape(iso3) + r"(?![A-Za-z])", text):
            found.add(code)
    return found


def parse_pubmed_xml(payload: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    authors: list[dict[str, Any]] = []
    author_nodes = root.findall(".//AuthorList/Author")
    for index, node in enumerate(author_nodes, start=1):
        last = node.findtext("LastName", "")
        fore = node.findtext("ForeName", "")
        collective = node.findtext("CollectiveName", "")
        name = collective or " ".join(part for part in [fore, last] if part).strip()
        affiliations = [
            affiliation.text.strip()
            for affiliation in node.findall("./AffiliationInfo/Affiliation")
            if affiliation.text and affiliation.text.strip()
        ]
        orcids = [
            identifier.text.strip()
            for identifier in node.findall(".//Identifier")
            if identifier.text and identifier.get("Source", "").casefold() == "orcid"
        ]
        authors.append(
            {
                "order": index,
                "name": name,
                "orcid": orcids[0] if orcids else "",
                "affiliation": " | ".join(affiliations),
                "position": "first" if index == 1 else "last" if index == len(author_nodes) else "middle",
            }
        )
    return authors


def xml_local_name(tag: object) -> str:
    """Return an XML tag name without a namespace prefix."""
    return str(tag).rsplit("}", 1)[-1]


def xml_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def europepmc_author_orcid(author: dict[str, Any]) -> str:
    """Extract an ORCID from the variable Europe PMC author-id shapes."""
    identifiers: list[Any] = []
    for key in ("authorId", "authorIds", "author-id"):
        value = author.get(key)
        if isinstance(value, list):
            identifiers.extend(value)
        elif value:
            identifiers.append(value)
    for identifier in identifiers:
        if isinstance(identifier, dict):
            if str(identifier.get("type", "")).casefold() == "orcid":
                candidate = normalize_orcid(identifier.get("value", ""))
                if candidate:
                    return candidate
        elif isinstance(identifier, str) and "orcid" in identifier.casefold():
            candidate = normalize_orcid(identifier)
            if candidate:
                return candidate
    return ""


def parse_europepmc_core_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse publication-level author affiliations from a Europe PMC core result."""
    author_list = result.get("authorList", {}) or {}
    raw_authors = author_list.get("author", []) or []
    if isinstance(raw_authors, dict):
        raw_authors = [raw_authors]
    authors: list[dict[str, Any]] = []
    for index, author in enumerate(raw_authors, start=1):
        if not isinstance(author, dict):
            continue
        full_name = str(author.get("fullName", "")).strip()
        if not full_name:
            full_name = " ".join(
                part for part in [str(author.get("firstName", "")), str(author.get("lastName", ""))] if part
            ).strip()
        details = (author.get("authorAffiliationDetailsList", {}) or {}).get("authorAffiliation", [])
        if isinstance(details, dict):
            details = [details]
        affiliations = []
        for detail in details or []:
            if isinstance(detail, dict):
                value = str(detail.get("affiliation", "")).strip()
            else:
                value = str(detail).strip()
            if value:
                affiliations.append(value)
        authors.append(
            {
                "order": index,
                "name": full_name,
                "orcid": europepmc_author_orcid(author),
                "affiliation": " | ".join(dict.fromkeys(affiliations)),
                "position": "first" if index == 1 else "last" if index == len(raw_authors) else "middle",
                # Europe PMC core metadata does not expose a corresponding
                # marker. Keep it unknown rather than encoding absence as No.
                "is_corresponding": None,
                "corresponding_evidence": "",
            }
        )
    return authors


def parse_europepmc_fulltext(payload: bytes) -> list[dict[str, Any]]:
    """Extract author affiliations and explicit corresponding-author markers from JATS XML."""
    root = ET.fromstring(payload)
    affiliations: dict[str, str] = {}
    for element in root.iter():
        if xml_local_name(element.tag) == "aff" and element.get("id"):
            affiliations[str(element.get("id"))] = xml_text(element)

    authors: list[dict[str, Any]] = []
    for contrib in root.iter():
        if xml_local_name(contrib.tag) != "contrib" or str(contrib.get("contrib-type", "")).casefold() != "author":
            continue
        name_node = next((child for child in contrib.iter() if xml_local_name(child.tag) == "name"), None)
        if name_node is None:
            continue
        given = next((child for child in name_node.iter() if xml_local_name(child.tag) == "given-names"), None)
        surname = next((child for child in name_node.iter() if xml_local_name(child.tag) == "surname"), None)
        full_name = " ".join(value for value in [xml_text(given), xml_text(surname)] if value).strip()
        if not full_name:
            continue
        aff_ids: list[str] = []
        for child in contrib.iter():
            if xml_local_name(child.tag) != "xref" or str(child.get("ref-type", "")).casefold() != "aff":
                continue
            aff_ids.extend(str(child.get("rid", "")).split())
        author_affiliations = [affiliations[value] for value in aff_ids if value in affiliations]
        if not author_affiliations:
            author_affiliations = [xml_text(child) for child in contrib if xml_local_name(child.tag) == "aff"]
        is_corresponding = str(contrib.get("corresp", "")).casefold() in {"yes", "true", "1"}
        authors.append(
            {
                "order": len(authors) + 1,
                "name": full_name,
                "orcid": "",
                "affiliation": " | ".join(dict.fromkeys(value for value in author_affiliations if value)),
                "position": "first" if len(authors) == 0 else "middle",
                "is_corresponding": is_corresponding,
                "corresponding_evidence": "contrib_corresp_attribute" if is_corresponding else "",
            }
        )

    # Some JATS records put the corresponding name only in author-notes/corresp.
    notes = [xml_text(element) for element in root.iter() if xml_local_name(element.tag) == "corresp"]
    if notes and authors:
        normalized_notes = [normalize_name(note) for note in notes if note]
        exact_matches: set[int] = set()
        for index, author in enumerate(authors):
            full = normalize_name(author.get("name", ""))
            surname = normalize_name(str(author.get("name", "")).split()[-1])
            if full and any(full in note for note in normalized_notes):
                exact_matches.add(index)
            elif surname and any(surname in note for note in normalized_notes):
                exact_matches.add(index)
        for index in exact_matches:
            authors[index]["is_corresponding"] = True
            authors[index]["corresponding_evidence"] = "author_notes_corresp"

    for index, author in enumerate(authors):
        author["position"] = "first" if index == 0 else "last" if index == len(authors) - 1 else "middle"
    return authors


def fetch_europepmc(
    session: requests.Session,
    paper_id: int,
    doi: str,
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    """Fetch Europe PMC core metadata and, when available, open JATS full text."""
    raw_dir = output_dir / "raw" / "europepmc"
    base = {
        "paper_id": paper_id,
        "doi": doi,
        "source": "Europe PMC",
        "status": "request_error",
        "pmid": "",
        "pmcid": "",
        "authors": [],
        "fulltext_authors": [],
        "fulltext_status": "not_attempted",
        "raw": [],
        "cached": False,
    }

    def load_search(payload: bytes) -> bool:
        parsed = json.loads(payload)
        results = (parsed.get("resultList", {}) or {}).get("result", []) or []
        if isinstance(results, dict):
            results = [results]
        matching = next(
            (item for item in results if normalize_doi(item.get("doi", "")) == doi),
            results[0] if results else None,
        )
        if not matching:
            base["status"] = "not_indexed"
            base["fulltext_status"] = "not_available"
            return False
        base["pmid"] = str(matching.get("pmid", "") or "")
        base["pmcid"] = str(matching.get("pmcid", "") or "")
        base["authors"] = parse_europepmc_core_result(matching)
        base["status"] = "success"
        if not base["pmcid"]:
            base["fulltext_status"] = "not_available"
        return True

    try:
        cached = cached_raw(raw_dir / f"paper_{safe_token(paper_id)}_search.json", "search")
        if cached:
            cached_bytes, cached_meta = cached
            base["raw"].append(cached_meta)
            found = load_search(cached_bytes)
            base["cached"] = True
        else:
            response = session.get(
                EUROPEPMC_SEARCH,
                params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"},
                timeout=30,
            )
            base["raw"].append(save_raw(response, raw_dir, f"paper_{safe_token(paper_id)}_search.json"))
            if not response.ok:
                base["status"] = source_status(response)
                base["fulltext_status"] = "not_available"
                return base
            found = load_search(response.content)
            time.sleep(delay)
        if not found or not base["pmcid"]:
            return base

        fulltext_path = raw_dir / f"paper_{safe_token(paper_id)}_fulltext.xml"
        cached_fulltext = cached_raw(fulltext_path, "fulltext_xml")
        if cached_fulltext:
            fulltext_bytes, fulltext_meta = cached_fulltext
            base["raw"].append(fulltext_meta)
            base["fulltext_status"] = "success"
            base["fulltext_authors"] = parse_europepmc_fulltext(fulltext_bytes)
        else:
            response = session.get(
                EUROPEPMC_FULLTEXT.format(pmcid=quote(base["pmcid"], safe="")),
                timeout=30,
            )
            fulltext_meta = save_raw(response, raw_dir, f"paper_{safe_token(paper_id)}_fulltext.xml")
            fulltext_meta["endpoint"] = "fulltext_xml"
            base["raw"].append(fulltext_meta)
            base["fulltext_status"] = source_status(response) if not response.ok else "success"
            if response.ok:
                base["fulltext_authors"] = parse_europepmc_fulltext(response.content)
            time.sleep(delay)
        if base["fulltext_authors"]:
            base["authors"] = base["fulltext_authors"]
    except ET.ParseError:
        base["fulltext_status"] = "parse_error"
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base


def fetch_pubmed(
    session: requests.Session,
    paper_id: int,
    doi: str,
    api_key: str,
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    raw_dir = output_dir / "raw" / "pubmed"
    base = {"paper_id": paper_id, "doi": doi, "source": "PubMed", "status": "request_error", "pmid": "", "authors": [], "raw": [], "cached": False}
    params: dict[str, str] = {"db": "pubmed", "term": f"{doi}[LID]", "retmode": "json"}
    if api_key:
        params["api_key"] = api_key
    try:
        cached_search = cached_raw(raw_dir / f"paper_{safe_token(paper_id)}_search.json", "search")
        cached_record = cached_raw(raw_dir / f"paper_{safe_token(paper_id)}_record.xml", "record")
        if cached_search:
            search_bytes, search_meta = cached_search
            base["raw"].append(search_meta)
            ids = json.loads(search_bytes).get("esearchresult", {}).get("idlist", [])
            if not ids:
                base["status"] = "not_indexed"
                return base
            base["pmid"] = str(ids[0])
            if cached_record:
                record_bytes, record_meta = cached_record
                base["raw"].append(record_meta)
                base["authors"] = parse_pubmed_xml(record_bytes)
                base["status"] = "success"
                base["cached"] = True
                return base
        search = session.get(PUBMED_SEARCH, params=params, timeout=30)
        base["raw"].append(save_raw(search, raw_dir, f"paper_{safe_token(paper_id)}_search.json"))
        if not search.ok:
            base["status"] = source_status(search)
            return base
        ids = search.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            base["status"] = "not_indexed"
            return base
        base["pmid"] = str(ids[0])
        time.sleep(delay)
        fetch_params: dict[str, str] = {"db": "pubmed", "id": base["pmid"], "retmode": "xml"}
        if api_key:
            fetch_params["api_key"] = api_key
        fetched = session.get(PUBMED_FETCH, params=fetch_params, timeout=30)
        base["raw"].append(save_raw(fetched, raw_dir, f"paper_{safe_token(paper_id)}_record.xml"))
        if not fetched.ok:
            base["status"] = source_status(fetched)
            return base
        base["authors"] = parse_pubmed_xml(fetched.content)
        base["status"] = "success"
    except ET.ParseError:
        base["status"] = "parse_error"
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base


def parse_semantic_payload(payload: dict[str, Any]) -> tuple[str, Any, list[dict[str, Any]]]:
    title = payload.get("title", "")
    influential_citations = payload.get("influentialCitationCount", 0)
    raw_authors = payload.get("authors", []) or []
    authors = []
    for index, author in enumerate(raw_authors, start=1):
        external = author.get("externalIds") or {}
        affiliations = author.get("affiliations") or []
        if isinstance(affiliations, list):
            affiliation = " | ".join(str(value) for value in affiliations if value)
        else:
            affiliation = str(affiliations)
        authors.append(
            {
                "order": index,
                "name": author.get("name", ""),
                "author_id": author.get("authorId", ""),
                "orcid": external.get("ORCID", "") or "",
                "affiliation": affiliation,
                "position": "first" if index == 1 else "last" if index == len(raw_authors) else "middle",
            }
        )
    return title, influential_citations, authors


def fetch_semantic_scholar(
    session: requests.Session,
    paper_id: int,
    doi: str,
    api_key: str,
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    raw_dir = output_dir / "raw" / "semantic_scholar"
    base = {"paper_id": paper_id, "doi": doi, "source": "Semantic Scholar", "status": "request_error", "authors": [], "raw": [], "cached": False}
    fields = "title,year,authors.name,authors.authorId,authors.externalIds,authors.affiliations,influentialCitationCount"
    headers = {"x-api-key": api_key} if api_key else {}
    try:
        cached_candidates = [
            cached_raw(raw_dir / f"paper_{safe_token(paper_id)}.json", "primary"),
            cached_raw(raw_dir / f"paper_{safe_token(paper_id)}_fallback.json", "fallback"),
        ]
        for cached in cached_candidates:
            if not cached:
                continue
            cached_bytes, cached_meta = cached
            payload = json.loads(cached_bytes)
            if not isinstance(payload, dict) or "authors" not in payload:
                continue
            base["raw"].append(cached_meta)
            base["title"], base["influential_citations"], base["authors"] = parse_semantic_payload(payload)
            base["status"] = "success"
            base["cached"] = True
            return base
        response = session.get(
            SEMANTIC_PAPER.format(doi=doi),
            params={"fields": fields},
            headers=headers,
            timeout=30,
        )
        base["raw"].append(save_raw(response, raw_dir, f"paper_{safe_token(paper_id)}.json"))
        if response.status_code == 400:
            time.sleep(delay)
            fallback = session.get(
                SEMANTIC_PAPER.format(doi=doi),
                params={"fields": "title,year,authors.name,authors.authorId,authors.externalIds,influentialCitationCount"},
                headers=headers,
                timeout=30,
            )
            base["raw"].append(save_raw(fallback, raw_dir, f"paper_{safe_token(paper_id)}_fallback.json"))
            response = fallback
        if not response.ok:
            base["status"] = source_status(response)
            return base
        payload = response.json()
        base["title"], base["influential_citations"], base["authors"] = parse_semantic_payload(payload)
        base["status"] = "success"
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base


def parse_crossref_payload(payload: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    message = payload.get("message", {}) or {}
    authors = []
    raw_authors = message.get("author", []) or []
    for index, author in enumerate(raw_authors, start=1):
        affiliations = [
            str(item.get("name", "")).strip()
            for item in author.get("affiliation", []) or []
            if str(item.get("name", "")).strip()
        ]
        given = str(author.get("given", "")).strip()
        family = str(author.get("family", "")).strip()
        sequence = str(author.get("sequence", "")).strip().casefold()
        authors.append(
            {
                "order": index,
                "name": " ".join(part for part in [given, family] if part).strip(),
                "orcid": author.get("ORCID", "") or "",
                "affiliation": " | ".join(affiliations),
                "position": "first" if sequence == "first" or index == 1 else "last" if index == len(raw_authors) else "middle",
                "sequence": sequence,
            }
        )
    title = " | ".join(str(value) for value in message.get("title", []) or [] if value)
    published_parts = message.get("published", {}).get("date-parts", [[""]]) or [[""]]
    year = str((published_parts[0] or [""])[0])
    return title, year, authors


def fetch_crossref(
    session: requests.Session,
    paper_id: int,
    doi: str,
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    """Fetch publication-level author affiliations from Crossref."""
    raw_dir = output_dir / "raw" / "crossref"
    base = {
        "paper_id": paper_id,
        "doi": doi,
        "source": "Crossref",
        "status": "request_error",
        "authors": [],
        "raw": [],
        "cached": False,
    }
    try:
        cached = cached_raw(raw_dir / f"paper_{safe_token(paper_id)}.json", "work")
        if cached:
            cached_bytes, cached_meta = cached
            payload = json.loads(cached_bytes)
            base["raw"].append(cached_meta)
            base["title"], base["year"], base["authors"] = parse_crossref_payload(payload)
            base["status"] = "success"
            base["cached"] = True
            return base
        response = session.get(
            CROSSREF_WORK.format(doi=quote(doi, safe="")),
            timeout=30,
        )
        base["raw"].append(save_raw(response, raw_dir, f"paper_{safe_token(paper_id)}.json"))
        if not response.ok:
            base["status"] = source_status(response)
            return base
        base["title"], base["year"], base["authors"] = parse_crossref_payload(response.json())
        base["status"] = "success"
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base


def parse_elsevier_abstract_payload(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Parse the DOI abstract endpoint's publication-level first-author record.

    The Elsevier abstract endpoint exposes only the indexed first author in
    this response shape, but it links that author to the article's affiliation
    block. We use it for first-author country evidence only; it does not expose
    a corresponding-author role marker.
    """
    record = payload.get("abstracts-retrieval-response", {}) or {}
    coredata = record.get("coredata", {}) or {}
    title = str(coredata.get("dc:title", "") or "").strip()
    creator = coredata.get("dc:creator", {}) or {}
    raw_authors = creator.get("author", []) if isinstance(creator, dict) else []
    if isinstance(raw_authors, dict):
        raw_authors = [raw_authors]
    raw_affiliations = record.get("affiliation", []) or []
    if isinstance(raw_affiliations, dict):
        raw_affiliations = [raw_affiliations]
    affiliation_texts: list[str] = []
    affiliation_countries: set[str] = set()
    for affiliation in raw_affiliations:
        if not isinstance(affiliation, dict):
            continue
        name = str(affiliation.get("affilname", "") or "").strip()
        city = str(affiliation.get("affiliation-city", "") or "").strip()
        country = str(affiliation.get("affiliation-country", "") or "").strip()
        text = ", ".join(value for value in [name, city, country] if value)
        if text:
            affiliation_texts.append(text)
        if country:
            affiliation_countries.add(country)
    affiliation_text = " | ".join(dict.fromkeys(affiliation_texts))
    authors: list[dict[str, Any]] = []
    for index, author in enumerate(raw_authors or [], start=1):
        if not isinstance(author, dict):
            continue
        preferred = author.get("preferred-name", {}) or {}
        given = str(author.get("ce:given-name") or preferred.get("ce:given-name") or "").strip()
        surname = str(author.get("ce:surname") or preferred.get("ce:surname") or "").strip()
        name = " ".join(value for value in [given, surname] if value).strip()
        if not name:
            name = str(preferred.get("ce:indexed-name", "") or author.get("ce:indexed-name", "")).strip()
        if not name:
            continue
        # If multiple affiliation countries are returned but the endpoint does
        # not provide their names-to-affiliation mapping, mark it ambiguous.
        # The downstream helper will not select an arbitrary first country.
        country_override = "__ambiguous__" if len(affiliation_countries) > 1 else ""
        authors.append(
            {
                "order": int(author.get("@seq", index) or index),
                "name": name,
                "orcid": "",
                "affiliation": affiliation_text,
                "position": "first" if index == 1 else "middle",
                "is_corresponding": None,
                "corresponding_evidence": "",
                "country_candidate_override": country_override,
            }
        )
    return title, authors


def fetch_elsevier_abstract(
    session: requests.Session,
    paper_id: int,
    doi: str,
    api_key: str,
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    """Fetch Elsevier/Scopus abstract metadata when the DOI is an Elsevier article."""
    raw_dir = output_dir / "raw" / "elsevier"
    base = {
        "paper_id": paper_id,
        "doi": doi,
        "source": "Elsevier Abstract API",
        "status": "not_applicable" if not doi.startswith("10.1016/") else ("not_run_no_key" if not api_key else "request_error"),
        "authors": [],
        "raw": [],
        "cached": False,
        "corresponding_role_available": False,
    }
    if not doi.startswith("10.1016/") or not api_key:
        return base
    raw_path = raw_dir / f"paper_{safe_token(paper_id)}.json"
    try:
        cached = cached_raw(raw_path, "abstract_doi")
        if cached:
            payload_bytes, metadata = cached
            base["raw"].append(metadata)
            payload = json.loads(payload_bytes)
            base["title"], base["authors"] = parse_elsevier_abstract_payload(payload)
            base["status"] = "success"
            base["cached"] = True
            return base
        response = session.get(
            ELSEVIER_ABSTRACT.format(doi=quote(doi, safe="")),
            headers={"X-ELS-APIKey": api_key, "Accept": "application/json"},
            timeout=45,
        )
        metadata = save_raw(response, raw_dir, raw_path.name)
        metadata["endpoint"] = "abstract_doi"
        base["raw"].append(metadata)
        if not response.ok:
            base["status"] = source_status(response)
            return base
        base["title"], base["authors"] = parse_elsevier_abstract_payload(response.json())
        base["status"] = "success"
        time.sleep(delay)
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base


def parse_ieee_csdl_article(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Parse the IEEE Computer Society GraphQL article metadata."""
    data = payload.get("data", {}) or {}
    article = data.get("article") or {}
    if not article:
        return "", [], {}
    raw_authors = article.get("authors", []) or []
    if isinstance(raw_authors, dict):
        raw_authors = [raw_authors]
    authors: list[dict[str, Any]] = []
    for index, author in enumerate(raw_authors, start=1):
        if not isinstance(author, dict):
            continue
        name = str(author.get("fullName", "") or "").strip()
        if not name:
            name = " ".join(
                value for value in [str(author.get("givenName", "") or "").strip(), str(author.get("surname", "") or "").strip()]
                if value
            )
        authors.append(
            {
                "order": index,
                "name": name,
                "orcid": "",
                "affiliation": str(author.get("affiliation", "") or "").strip(),
                "position": "first" if index == 1 else "last" if index == len(raw_authors) else "middle",
                # The CSDL GraphQL schema exposes no corresponding-author field.
                "is_corresponding": None,
                "corresponding_evidence": "",
            }
        )
    return str(article.get("title", "") or "").strip(), authors, article


def fetch_ieee_csdl(
    session: requests.Session,
    paper_id: int,
    doi: str,
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    """Fetch DOI-scoped IEEE Computer Society article metadata via GraphQL."""
    raw_dir = output_dir / "raw" / "ieee_csdl"
    base = {
        "paper_id": paper_id,
        "doi": doi,
        "source": "IEEE Computer Society CSDL",
        "status": "not_applicable" if not doi.startswith("10.1109/") else "request_error",
        "authors": [],
        "raw": [],
        "cached": False,
        "corresponding_role_available": False,
        "article_id": "",
    }
    if not doi.startswith("10.1109/"):
        return base
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.computer.org",
        "Referer": "https://www.computer.org/csdl",
    }
    doi_query = 'query ($doi: String!) { article: articleByDoi(doi: $doi) { id fno pubType idPrefix issueNum year } }'
    article_query = (
        'query ($articleId: String!) { article: articleById(articleId: $articleId) '
        '{ id doi title fno authors { affiliation fullName givenName surname } '
        'idPrefix issueNum year pubType isOpenAccess hasPdf pages pubDate } }'
    )
    doi_path = raw_dir / f"paper_{safe_token(paper_id)}_by_doi.json"
    try:
        cached_doi = cached_raw(doi_path, "article_by_doi")
        if cached_doi:
            doi_bytes, doi_meta = cached_doi
            base["raw"].append(doi_meta)
            doi_payload = json.loads(doi_bytes)
            doi_data = (doi_payload.get("data", {}) or {}).get("article") or {}
            base["cached"] = True
        else:
            response = session.post(
                IEEE_CSDL_GRAPHQL,
                headers=headers,
                json={"query": doi_query, "variables": {"doi": doi.upper()}},
                timeout=45,
            )
            doi_meta = save_raw(response, raw_dir, doi_path.name)
            doi_meta["endpoint"] = "article_by_doi"
            base["raw"].append(doi_meta)
            if not response.ok:
                base["status"] = source_status(response)
                return base
            doi_payload = response.json()
            doi_data = (doi_payload.get("data", {}) or {}).get("article") or {}
            time.sleep(delay)
        if not doi_data:
            base["status"] = "not_found"
            return base
        article_id = str(doi_data.get("id", "") or "")
        base["article_id"] = article_id
        if not article_id:
            base["status"] = "parse_error"
            return base
        article_path = raw_dir / f"paper_{safe_token(paper_id)}_article.json"
        cached_article = cached_raw(article_path, "article_by_id")
        if cached_article:
            article_bytes, article_meta = cached_article
            base["raw"].append(article_meta)
            article_payload = json.loads(article_bytes)
            base["cached"] = base["cached"] and True
        else:
            response = session.post(
                IEEE_CSDL_GRAPHQL,
                headers=headers,
                json={"query": article_query, "variables": {"articleId": article_id}},
                timeout=45,
            )
            article_meta = save_raw(response, raw_dir, article_path.name)
            article_meta["endpoint"] = "article_by_id"
            base["raw"].append(article_meta)
            base["cached"] = False
            if not response.ok:
                base["status"] = source_status(response)
                return base
            article_payload = response.json()
            time.sleep(delay)
        title, authors, article = parse_ieee_csdl_article(article_payload)
        if not article:
            base["status"] = "parse_error"
            return base
        base["title"] = title
        base["authors"] = authors
        base["status"] = "success"
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base


def parse_serpapi_contacts(payload: dict[str, Any], doi: str, title: str = "") -> list[dict[str, str]]:
    """Extract DOI-specific correspondence snippets without treating search text as affiliation."""
    contacts: list[dict[str, str]] = []
    for result in payload.get("organic_results", []) or []:
        if not isinstance(result, dict):
            continue
        text = " ".join(
            str(value)
            for value in [result.get("title", ""), result.get("snippet", ""), result.get("rich_snippet", "")]
            if value
        )
        link = str(result.get("link", ""))
        target_title = normalize_name(title)
        result_title = normalize_name(result.get("title", ""))
        normalized_doi = normalize_doi(doi)
        doi_in_link = normalized_doi and normalized_doi in link.casefold()
        title_match = bool(
            target_title
            and result_title
            and (target_title in result_title or result_title in target_title)
        )
        if not doi_in_link and not title_match:
            continue
        if "correspond" not in text.casefold():
            continue
        emails = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text)
        correspondence_context_match = re.search(
            r"(?:address\s+correspondence|correspondence\s+to|corresponding\s+author).{0,140}",
            text,
            flags=re.IGNORECASE,
        )
        correspondence_context = correspondence_context_match.group(0) if correspondence_context_match else ""
        initials = re.findall(r"(?<![A-Za-z])(?:[A-Z]\.){2,6}(?![A-Za-z])", correspondence_context)
        initials = [value.replace(".", "") for value in initials]
        if not emails and not initials:
            continue
        for email in emails or [""]:
            local = email.split("@", 1)[0] if email else ""
            name_hint = " ".join(re.findall(r"[A-Za-z]+", local.replace(".", " ").replace("_", " ").replace("-", " ")))
            contacts.append(
                {
                    "Email": email,
                    "Name_Hint": name_hint,
                    "Initials": " | ".join(initials),
                    "Snippet": str(result.get("snippet", "")),
                    "Title": str(result.get("title", "")),
                    "Link": link,
                    "DOI": doi,
                }
            )
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for contact in contacts:
        key = (contact.get("Email", ""), contact.get("Initials", ""), contact.get("Link", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(contact)
    return deduped


def fetch_serpapi_correspondence(
    session: requests.Session,
    paper_id: int,
    doi: str,
    title: str,
    api_key: str,
    delay: float,
    output_dir: Path,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Use DOI-specific Google snippets only to recover explicit correspondence contacts."""
    raw_dir = output_dir / "raw" / "serpapi"
    base = {
        "paper_id": paper_id,
        "doi": doi,
        "source": "SerpAPI (Google)",
        "status": "not_run_no_key" if not api_key else "request_error",
        "contacts": [],
        "raw": [],
        "cached": True,
    }
    if not api_key:
        return base
    query_specs = [
        ("doi", f'"{doi}" "Address correspondence"'),
        ("title", f'"{title}" "corresponding author"' if title else f'"{doi}" "corresponding author"'),
    ]
    any_success = False
    for label, query in query_specs:
        try:
            raw_path = raw_dir / f"paper_{safe_token(paper_id)}_{label}.json"
            cached = None if force_refresh else cached_raw(raw_path, label)
            if cached:
                cached_bytes, cached_meta = cached
                base["raw"].append(cached_meta)
                payload = json.loads(cached_bytes)
                base["contacts"].extend(parse_serpapi_contacts(payload, doi, title))
                any_success = True
                continue
            response = session.get(
                SERPAPI_SEARCH,
                params={"engine": "google", "q": query, "api_key": api_key, "num": "10"},
                timeout=45,
            )
            base["cached"] = False
            raw = save_raw(response, raw_dir, raw_path.name)
            raw["endpoint"] = label
            base["raw"].append(raw)
            if response.ok:
                base["contacts"].extend(parse_serpapi_contacts(response.json(), doi, title))
                any_success = True
            elif base["status"] == "request_error":
                base["status"] = source_status(response)
            time.sleep(delay)
        except requests.RequestException as exc:
            base["error_type"] = type(exc).__name__
        except (ValueError, KeyError, TypeError) as exc:
            base["error_type"] = type(exc).__name__
    # The same DOI contact may appear in both targeted queries with different
    # Google result URLs. Deduplicate by the contact identity, not by URL.
    deduped_contacts: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in base["contacts"]:
        key = (
            str(item.get("Email", "")).casefold().strip(),
            str(item.get("Initials", "")).casefold().strip(),
            str(item.get("Name_Hint", "")).casefold().strip(),
        )
        if key not in deduped_contacts:
            deduped_contacts[key] = item
    base["contacts"] = list(deduped_contacts.values())
    email_links = {item.get("Link", "") for item in base["contacts"] if item.get("Email", "")}
    if email_links:
        base["contacts"] = [
            item for item in base["contacts"]
            if item.get("Email", "")
        ]
    base["status"] = "success" if any_success else base["status"]
    return base


def fetch_scopus(
    session: requests.Session,
    paper_id: int,
    doi: str,
    api_key: str,
    delay: float,
    output_dir: Path,
) -> tuple[dict[str, Any], bool]:
    raw_dir = output_dir / "raw" / "scopus"
    base = {"paper_id": paper_id, "doi": doi, "source": "Scopus", "status": "not_run_no_key", "authors": [], "raw": []}
    if not api_key:
        return base, False
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    try:
        response = session.get(
            SCOPUS_SEARCH,
            params={"query": f'DOI("{doi}")', "view": "COMPLETE"},
            headers=headers,
            timeout=30,
        )
        base["raw"].append(save_raw(response, raw_dir, f"paper_{safe_token(paper_id)}.json"))
        if not response.ok:
            base["status"] = source_status(response)
            return base, response.status_code in {400, 401, 403, 429}
        payload = response.json()
        results = payload.get("search-results", {})
        entries = results.get("entry", []) or []
        total = int(results.get("opensearch:totalResults", 0) or 0)
        base["total_results"] = total
        if not entries or total == 0:
            base["status"] = "not_indexed"
            return base, False
        entry = entries[0]
        authors = []
        for index, author in enumerate(entry.get("author", []) or [], start=1):
            given = author.get("given-name", "")
            surname = author.get("surname", "")
            authors.append(
                {
                    "order": index,
                    "name": f"{given} {surname}".strip(),
                    "author_id": author.get("authid", ""),
                    "orcid": author.get("orcid", "") or "",
                    "affiliation": json.dumps(author.get("afid", ""), ensure_ascii=False),
                    "position": "first" if index == 1 else "last" if index == len(entry.get("author", []) or []) else "middle",
                }
            )
        base["authors"] = authors
        base["status"] = "success"
    except requests.RequestException as exc:
        base["status"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["status"] = "parse_error"
        base["error_type"] = type(exc).__name__
    return base, False


def parse_orcid_affiliation_summaries(
    payload: dict[str, Any],
    summary_key: str,
    affiliation_type: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group in payload.get("affiliation-group", []) or []:
        for summary in group.get("summaries", []) or []:
            affiliation = summary.get(summary_key, {}) or {}
            organization = affiliation.get("organization", {}) or {}
            address = organization.get("address", {}) or {}
            source = affiliation.get("source", {}) or {}
            source_name = (source.get("source-name", {}) or {}).get("value", "")
            rows.append(
                {
                    "affiliation_type": affiliation_type,
                    "put_code": str(affiliation.get("put-code", "")),
                    "organization": str(organization.get("name", "")),
                    "department": str(affiliation.get("department-name", "") or ""),
                    "role_title": str(affiliation.get("role-title", "") or ""),
                    "city": str(address.get("city", "")),
                    "country": str(address.get("country", "")),
                    "start_year": str(((affiliation.get("start-date", {}) or {}).get("year", {}) or {}).get("value", "")),
                    "end_year": str(((affiliation.get("end-date", {}) or {}).get("year", {}) or {}).get("value", "")),
                    "source_name": str(source_name or ""),
                }
            )
    return rows


def parse_orcid_employments(payload: dict[str, Any]) -> list[dict[str, str]]:
    return parse_orcid_affiliation_summaries(payload, "employment-summary", "employment")


def parse_orcid_works(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group in payload.get("group", []) or []:
        group_external_ids = group.get("external-ids", {}) or {}
        group_dois = [
            normalize_doi(item.get("external-id-value", ""))
            for item in group_external_ids.get("external-id", []) or []
            if str(item.get("external-id-type", "")).casefold() == "doi"
        ]
        for summary in group.get("work-summary", []) or []:
            summary_external_ids = summary.get("external-ids", {}) or {}
            doi_values = group_dois + [
                normalize_doi(item.get("external-id-value", ""))
                for item in summary_external_ids.get("external-id", []) or []
                if str(item.get("external-id-type", "")).casefold() == "doi"
            ]
            doi_values = list(dict.fromkeys(value for value in doi_values if value))
            title = ((summary.get("title", {}) or {}).get("title", {}) or {}).get("value", "")
            year = (((summary.get("publication-date", {}) or {}).get("year", {}) or {}).get("value", ""))
            source = (summary.get("source", {}) or {}).get("source-name", {}) or {}
            rows.append(
                {
                    "put_code": str(summary.get("put-code", "")),
                    "doi": " | ".join(doi_values),
                    "title": str(title or ""),
                    "year": str(year or ""),
                    "type": str(summary.get("type", "") or ""),
                    "source_name": str(source.get("value", "") or ""),
                }
            )
    return rows


def parse_orcid_work_detail(payload: dict[str, Any]) -> dict[str, str]:
    contributors = []
    for contributor in (payload.get("contributors", {}) or {}).get("contributor", []) or []:
        credit_name = ((contributor.get("credit-name", {}) or {}).get("value", ""))
        attributes = contributor.get("contributor-attributes", {}) or {}
        sequence = str(attributes.get("contributor-sequence", "") or "")
        role = str(attributes.get("contributor-role", "") or "")
        contributor_orcid = contributor.get("contributor-orcid") or {}
        contributor_orcid = str(contributor_orcid.get("path", "") or "")
        contributors.append(
            " | ".join(value for value in [str(credit_name), sequence, role, normalize_orcid(contributor_orcid)] if value)
        )
    title = ((payload.get("title", {}) or {}).get("title", {}) or {}).get("value", "")
    year = (((payload.get("publication-date", {}) or {}).get("year", {}) or {}).get("value", ""))
    doi_values = [
        normalize_doi(item.get("external-id-value", ""))
        for item in ((payload.get("external-ids", {}) or {}).get("external-id", []) or [])
        if str(item.get("external-id-type", "")).casefold() == "doi"
    ]
    return {
        "put_code": str(payload.get("put-code", "")),
        "doi": " | ".join(dict.fromkeys(value for value in doi_values if value)),
        "title": str(title or ""),
        "year": str(year or ""),
        "type": str(payload.get("type", "") or ""),
        "contributors": " || ".join(contributors),
        "source_name": str(((payload.get("source", {}) or {}).get("source-name", {}) or {}).get("value", "") or ""),
    }


def fetch_orcid(
    session: requests.Session,
    orcid: str,
    target_dois: set[str],
    delay: float,
    output_dir: Path,
) -> dict[str, Any]:
    raw_dir = output_dir / "raw" / "orcid"
    base = {
        "orcid": orcid,
        "source": "ORCID",
        "status": "request_error",
        "employments": [],
        "educations": [],
        "qualifications": [],
        "affiliations": [],
        "works": [],
        "work_details": [],
        "work_matches": [],
        "endpoint_statuses": {},
        "raw": [],
        "cached": True,
    }
    endpoint_specs = [
        ("employments", ORCID_EMPLOYMENTS, "employment-summary", "employment"),
        ("educations", ORCID_EDUCATIONS, "education-summary", "education"),
        ("qualifications", ORCID_QUALIFICATIONS, "qualification-summary", "qualification"),
    ]
    headers = {"Accept": "application/vnd.orcid+json"}
    any_success = False
    for endpoint_name, endpoint_template, summary_key, affiliation_type in endpoint_specs:
        try:
            cached = cached_raw(raw_dir / f"orcid_{safe_token(orcid)}_{endpoint_name}.json", endpoint_name)
            if cached:
                cached_bytes, cached_meta = cached
                base["raw"].append(cached_meta)
                records = parse_orcid_affiliation_summaries(json.loads(cached_bytes), summary_key, affiliation_type)
                base[endpoint_name] = records
                base["affiliations"].extend(records)
                base["endpoint_statuses"][endpoint_name] = "cached_success"
                any_success = True
                continue
            response = session.get(endpoint_template.format(orcid=orcid), headers=headers, timeout=30)
            base["cached"] = False
            raw = save_raw(response, raw_dir, f"orcid_{safe_token(orcid)}_{endpoint_name}.json")
            raw["endpoint"] = endpoint_name
            base["raw"].append(raw)
            status = source_status(response) if not response.ok else "success"
            base["endpoint_statuses"][endpoint_name] = status
            if response.ok:
                records = parse_orcid_affiliation_summaries(response.json(), summary_key, affiliation_type)
                base[endpoint_name] = records
                base["affiliations"].extend(records)
                any_success = True
            time.sleep(delay)
        except requests.RequestException as exc:
            base["endpoint_statuses"][endpoint_name] = "request_error"
            base["error_type"] = type(exc).__name__
        except (ValueError, KeyError, TypeError) as exc:
            base["endpoint_statuses"][endpoint_name] = "parse_error"
            base["error_type"] = type(exc).__name__

    try:
        cached = cached_raw(raw_dir / f"orcid_{safe_token(orcid)}_works.json", "works")
        if cached:
            cached_bytes, cached_meta = cached
            base["raw"].append(cached_meta)
            base["works"] = parse_orcid_works(json.loads(cached_bytes))
            base["endpoint_statuses"]["works"] = "cached_success"
            any_success = True
        else:
            response = session.get(ORCID_WORKS.format(orcid=orcid), headers=headers, timeout=30)
            base["cached"] = False
            raw = save_raw(response, raw_dir, f"orcid_{safe_token(orcid)}_works.json")
            raw["endpoint"] = "works"
            base["raw"].append(raw)
            base["endpoint_statuses"]["works"] = source_status(response) if not response.ok else "success"
            if response.ok:
                base["works"] = parse_orcid_works(response.json())
                any_success = True
            time.sleep(delay)
    except requests.RequestException as exc:
        base["endpoint_statuses"]["works"] = "request_error"
        base["error_type"] = type(exc).__name__
    except (ValueError, KeyError, TypeError) as exc:
        base["endpoint_statuses"]["works"] = "parse_error"
        base["error_type"] = type(exc).__name__

    matches = []
    for work in base["works"]:
        work_dois = {normalize_doi(value) for value in str(work.get("doi", "")).split(" | ") if normalize_doi(value)}
        if work_dois & target_dois:
            matches.append(work)
    base["work_matches"] = matches
    for index, work in enumerate(matches, start=1):
        put_code = str(work.get("put_code", ""))
        if not put_code:
            continue
        try:
            cached = cached_raw(raw_dir / f"orcid_{safe_token(orcid)}_work_{safe_token(put_code)}.json", "work_detail")
            if cached:
                cached_bytes, cached_meta = cached
                base["raw"].append(cached_meta)
                detail = parse_orcid_work_detail(json.loads(cached_bytes))
                detail["matched_target_dois"] = " | ".join(sorted({doi for doi in str(work.get("doi", "")).split(" | ") if doi in target_dois}))
                base["work_details"].append(detail)
                continue
            response = session.get(
                ORCID_WORK.format(orcid=orcid, put_code=quote(put_code, safe="")),
                headers=headers,
                timeout=30,
            )
            base["cached"] = False
            raw = save_raw(response, raw_dir, f"orcid_{safe_token(orcid)}_work_{safe_token(put_code)}.json")
            raw["endpoint"] = "work_detail"
            base["raw"].append(raw)
            if response.ok:
                detail = parse_orcid_work_detail(response.json())
                detail["matched_target_dois"] = " | ".join(sorted({doi for doi in str(work.get("doi", "")).split(" | ") if doi in target_dois}))
                base["work_details"].append(detail)
            time.sleep(delay)
        except requests.RequestException as exc:
            base["error_type"] = type(exc).__name__
        except (ValueError, KeyError, TypeError) as exc:
            base["error_type"] = type(exc).__name__

    base["status"] = "success" if any_success else "request_error"
    return base


def bool_text(value: object) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes"}


def load_targets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    review = pd.read_csv(REVIEW_METADATA, dtype=str).fillna("")
    authorships = pd.read_csv(OPENALEX_AUTHORS, dtype=str).fillna("")
    authorships["Paper_ID"] = authorships["Paper_ID"].astype(str)
    targets = []
    for paper_id, group in authorships.groupby("Paper_ID", sort=False):
        first_rows = group.loc[group["Author_Position"].str.casefold() == "first"]
        if first_rows.empty:
            first_rows = group.sort_values("Author_Order").head(1)
        first = first_rows.iloc[0] if not first_rows.empty else pd.Series(dtype=object)
        corresponding = group.loc[group["Is_Corresponding"].map(bool_text)]
        targets.append(
            {
                "Paper_ID": paper_id,
                "First_Author_Name_OpenAlex": first.get("Author_Name", ""),
                "First_Author_ORCID_OpenAlex": normalize_orcid(first.get("ORCID", "")),
                "First_Author_Country_OpenAlex": first.get("Affiliation_Countries", ""),
                "Corresponding_Author_Names_OpenAlex": " | ".join(corresponding["Author_Name"].tolist()),
                "Corresponding_Author_ORCIDs_OpenAlex": " | ".join(
                    normalize_orcid(value) for value in corresponding["ORCID"].tolist() if normalize_orcid(value)
                ),
                "Corresponding_Author_Country_OpenAlex": " | ".join(
                    sorted({value for value in corresponding["Affiliation_Countries"].tolist() if value})
                ),
            }
        )
    targets_frame = pd.DataFrame(targets)
    targets_frame["Paper_ID"] = targets_frame["Paper_ID"].astype(str)
    merged = targets_frame.merge(review, on="Paper_ID", how="left", suffixes=("", "_review"))
    return merged, authorships, review


def single_country_from_all_authors(authorships: pd.DataFrame, paper_id: str) -> str:
    """Return a deterministic article country when every author has one same country."""
    group = authorships.loc[authorships["Paper_ID"].astype(str) == str(paper_id)]
    if group.empty:
        return ""
    countries: list[str] = []
    for value in group["Affiliation_Countries"].tolist():
        parts = [part.strip().upper() for part in str(value).split("|") if part.strip()]
        # A multi-country affiliation is not deterministic for the corresponding author.
        if len(parts) != 1:
            return ""
        countries.append(parts[0])
    unique = sorted(set(countries))
    return unique[0] if unique and len(unique) == 1 else ""


def first_author_record(result: dict[str, Any]) -> dict[str, Any]:
    authors = result.get("authors", []) or []
    return authors[0] if authors else {}


def employment_summary(records: list[dict[str, str]]) -> tuple[str, str, str]:
    organizations = [record.get("organization", "") for record in records if record.get("organization")]
    countries = [record.get("country", "") for record in records if record.get("country")]
    locations = [
        " ".join(value for value in [record.get("city", ""), record.get("country", "")] if value)
        for record in records
    ]
    return " | ".join(dict.fromkeys(organizations)), " | ".join(dict.fromkeys(countries)), " | ".join(dict.fromkeys(locations))


def orcid_profile_summary(
    profiles: list[dict[str, Any]],
    affiliation_types: set[str],
    target_doi: str,
) -> dict[str, str]:
    records = [
        record
        for profile in profiles
        for record in profile.get("affiliations", []) or []
        if record.get("affiliation_type") in affiliation_types
    ]
    organizations, countries, locations = employment_summary(records)
    work_matches = [
        work
        for profile in profiles
        for work in profile.get("work_matches", []) or []
        if target_doi in {normalize_doi(value) for value in str(work.get("doi", "")).split(" | ") if normalize_doi(value)}
    ]
    work_details = [
        detail
        for profile in profiles
        for detail in profile.get("work_details", []) or []
        if target_doi in {normalize_doi(value) for value in str(detail.get("matched_target_dois", "")).split(" | ") if normalize_doi(value)}
    ]
    work_descriptions = []
    for work in work_matches + work_details:
        description = " ".join(value for value in [str(work.get("title", "")), f"({work.get('year', '')})" if work.get("year") else ""] if value)
        if description and description not in work_descriptions:
            work_descriptions.append(description)
    return {
        "organizations": organizations,
        "countries": countries,
        "locations": locations,
        "work_matches": " | ".join(work_descriptions),
        "work_match": "Yes" if work_matches or work_details else "No",
    }


def author_name_signature(value: object) -> tuple[str, str]:
    """Return surname and initials so abbreviated author records can be matched."""
    text = unicodedata.normalize("NFKD", "" if value is None else str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    tokens = re.findall(r"[A-Za-z]+", text)
    if not tokens:
        return "", ""
    long_tokens = [token for token in tokens if len(token) > 2]
    surname = long_tokens[-1] if len(long_tokens) >= 2 else long_tokens[0] if long_tokens else tokens[-1]
    surname_index = max(index for index, token in enumerate(tokens) if token.casefold() == surname.casefold())
    initials = ""
    for index, token in enumerate(tokens):
        if index == surname_index:
            continue
        initials += token if len(token) <= 2 else token[0]
    initials += surname[0]
    return surname.casefold(), initials.casefold()


def names_compatible(left: object, right: object) -> bool:
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return False
    if left_norm == right_norm or (len(left_norm) >= 6 and (left_norm in right_norm or right_norm in left_norm)):
        return True
    left_surname, left_initials = author_name_signature(left)
    right_surname, right_initials = author_name_signature(right)
    return bool(left_surname and left_surname == right_surname and left_initials == right_initials)


def contact_matches_author(contact: dict[str, str], author_name: object) -> bool:
    """Match a DOI-specific correspondence contact to one publication author."""
    surname, initials = author_name_signature(author_name)
    if not surname:
        return False
    email = str(contact.get("Email", ""))
    local = email.split("@", 1)[0] if "@" in email else ""
    email_tokens = [token.casefold() for token in re.findall(r"[A-Za-z]+", local)]
    if email_tokens and surname == email_tokens[-1]:
        return True
    contact_initials = {
        value.casefold()
        for value in str(contact.get("Initials", "")).split("|")
        if value.strip()
    }
    if initials and initials in contact_initials:
        return True
    hint = str(contact.get("Name_Hint", "")).strip()
    return bool(hint and names_compatible(hint, author_name))


def contact_email_country(contact: dict[str, str], known_codes: set[str]) -> str:
    email = str(contact.get("Email", ""))
    if "@" not in email:
        return ""
    domain = email.rsplit("@", 1)[1].casefold().strip(".")
    tld = domain.rsplit(".", 1)[-1].upper() if "." in domain else ""
    return tld if len(tld) == 2 and tld in known_codes else ""


def collect_role_orcids(
    target_name: object,
    baseline_orcids: list[str],
    source_results: list[dict[str, Any]],
) -> list[str]:
    values = {normalize_orcid(value) for value in baseline_orcids if normalize_orcid(value)}
    for source_result in source_results:
        for author in source_result.get("authors", []) or []:
            if names_compatible(target_name, author.get("name", "")):
                candidate = normalize_orcid(author.get("orcid", ""))
                if candidate:
                    values.add(candidate)
    return sorted(values)


def author_country_candidates_for_names(
    names: list[str],
    source_results: list[dict[str, Any]],
    name_to_code: dict[str, str],
    iso3_to_code: dict[str, str],
) -> dict[str, str]:
    candidates: dict[str, str] = {}
    for source_result in source_results:
        source_name = str(source_result.get("source", ""))
        for author in source_result.get("authors", []) or []:
            if not any(names_compatible(name, author.get("name", "")) for name in names):
                continue
            candidate, _ = author_country_candidate(author, name_to_code, iso3_to_code)
            if candidate:
                candidates[source_name] = candidate
    return candidates


def author_country_candidate(
    author: dict[str, Any],
    name_to_code: dict[str, str],
    iso3_to_code: dict[str, str],
) -> tuple[str, str]:
    """Use a provider's safe override, or parse the recorded affiliation."""
    if author.get("country_candidate_override") == "__ambiguous__":
        return "", "provider_affiliation_multiple_country_candidates"
    return country_candidate(author.get("affiliation", ""), name_to_code, iso3_to_code)


def append_source_author_rows(
    rows: list[dict[str, Any]],
    source_result: dict[str, Any],
    name_to_code: dict[str, str],
    iso3_to_code: dict[str, str],
) -> None:
    for author in source_result.get("authors", []) or []:
        candidate, method = author_country_candidate(author, name_to_code, iso3_to_code)
        marker = author.get("is_corresponding")
        if marker is None or str(marker).strip() == "":
            corresponding_value = "Unknown"
        else:
            corresponding_value = "Yes" if bool_text(marker) else "No"
        rows.append(
            {
                "Paper_ID": source_result.get("paper_id", ""),
                "DOI": source_result.get("doi", ""),
                "Source": source_result.get("source", ""),
                "Source_Status": source_result.get("status", ""),
                "Author_Order": author.get("order", ""),
                "Author_Name": author.get("name", ""),
                "Author_ID": author.get("author_id", ""),
                "ORCID": normalize_orcid(author.get("orcid", "")),
                "Author_Position": author.get("position", ""),
                "Is_Corresponding": corresponding_value,
                "Corresponding_Evidence": author.get("corresponding_evidence", ""),
                "Affiliation": author.get("affiliation", ""),
                "Country_Candidate": candidate,
                "Country_Candidate_Method": method,
            }
        )


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    env = read_env_file(args.env_file.resolve())
    # Runtime environment variables may override a file value without
    # requiring a secret to be written to the generic tool's .env file.
    if os.environ.get("SCHOLAR_KEY"):
        env["SCHOLAR_KEY"] = os.environ["SCHOLAR_KEY"]
    targets, authorships, _ = load_targets()
    code_to_income, name_to_code, iso3_to_code = load_country_maps()
    session = requests.Session()
    session.headers.update({"User-Agent": "MRI-LMICs-survey-reproducible-enrichment/1.0"})

    pubmed_delay = max(env_float(env, "PUBMED_DELAY", 0.35), 0.25)
    europepmc_delay = max(env_float(env, "EUROPEPMC_DELAY", 0.35), 0.25)
    semantic_delay = max(env_float(env, "SEMANTIC_DELAY", 0.75), 0.5)
    elsevier_delay = max(env_float(env, "SCOPUS_DELAY", 0.75), 0.5)
    ieee_delay = 0.5
    scopus_delay = max(env_float(env, "SCOPUS_DELAY", 0.75), 0.5)
    serpapi_delay = max(env_float(env, "SCHOLAR_DELAY", 1.0), 0.5)
    orcid_delay = 0.5
    pubmed_results: dict[str, dict[str, Any]] = {}
    europepmc_results: dict[str, dict[str, Any]] = {}
    semantic_results: dict[str, dict[str, Any]] = {}
    crossref_results: dict[str, dict[str, Any]] = {}
    elsevier_results: dict[str, dict[str, Any]] = {}
    ieee_results: dict[str, dict[str, Any]] = {}
    scopus_results: dict[str, dict[str, Any]] = {}
    serpapi_results: dict[str, dict[str, Any]] = {}
    orcid_results: dict[str, dict[str, Any]] = {}
    source_statuses: dict[str, list[str]] = {source: [] for source in ["PubMed", "Europe PMC", "Semantic Scholar", "Crossref", "Elsevier Abstract API", "IEEE Computer Society CSDL", "Scopus", "SerpAPI (Google)", "ORCID"]}
    fulltext_statuses: dict[str, list[str]] = {"Europe PMC": []}
    raw_file_count = 0
    scopus_stopped = ""

    selected_sources = {source.casefold() for source in args.sources}
    refresh_sources = {source.casefold() for source in getattr(args, "refresh_sources", [])}
    serpapi_all = bool(getattr(args, "serpapi_all", False))
    for index, row in targets.iterrows():
        paper_id = int(row["Paper_ID"])
        doi = normalize_doi(row.get("DOI", ""))
        if not doi:
            continue
        if "pubmed" in selected_sources:
            result = fetch_pubmed(
                session, paper_id, doi, env.get("PUBMED_KEY", ""), pubmed_delay, output_dir
            )
            pubmed_results[str(paper_id)] = result
            source_statuses["PubMed"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached"):
                time.sleep(pubmed_delay)
        if "europepmc" in selected_sources or "europe pmc" in selected_sources:
            result = fetch_europepmc(
                session, paper_id, doi, europepmc_delay, output_dir
            )
            europepmc_results[str(paper_id)] = result
            source_statuses["Europe PMC"].append(result["status"])
            fulltext_statuses["Europe PMC"].append(result.get("fulltext_status", "not_attempted"))
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached"):
                time.sleep(europepmc_delay)
        if "semantic" in selected_sources or "semantic scholar" in selected_sources:
            result = fetch_semantic_scholar(
                session, paper_id, doi, env.get("SEMANTIC_KEY", ""), semantic_delay, output_dir
            )
            semantic_results[str(paper_id)] = result
            source_statuses["Semantic Scholar"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached"):
                time.sleep(semantic_delay)
        if "crossref" in selected_sources:
            result = fetch_crossref(
                session, paper_id, doi, semantic_delay, output_dir
            )
            crossref_results[str(paper_id)] = result
            source_statuses["Crossref"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached"):
                time.sleep(semantic_delay)
        if "elsevier" in selected_sources or "elsevier abstract" in selected_sources:
            result = fetch_elsevier_abstract(
                session, paper_id, doi, env.get("SCOPUS_KEY", ""), elsevier_delay, output_dir
            )
            elsevier_results[str(paper_id)] = result
            source_statuses["Elsevier Abstract API"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached") and result.get("status") not in {"not_applicable", "not_run_no_key"}:
                time.sleep(elsevier_delay)
        if "ieee" in selected_sources or "ieee csdl" in selected_sources or "ieee_csdl" in selected_sources or "ieee computer society" in selected_sources:
            result = fetch_ieee_csdl(session, paper_id, doi, ieee_delay, output_dir)
            ieee_results[str(paper_id)] = result
            source_statuses["IEEE Computer Society CSDL"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached") and result.get("status") not in {"not_applicable"}:
                time.sleep(ieee_delay)
        if "serpapi" in selected_sources or "google" in selected_sources:
            # Only query papers whose corresponding-country value is not
            # already deterministic from a baseline or a single-country paper.
            baseline_corr = str(row.get("Corresponding_Author_Names_OpenAlex", "")).strip()
            single_country = single_country_from_all_authors(authorships, str(row["Paper_ID"]))
            if serpapi_all or (not baseline_corr and not single_country):
                result = fetch_serpapi_correspondence(
                    session,
                    paper_id,
                    doi,
                    str(row.get("Title", "")),
                    env.get("SCHOLAR_KEY", ""),
                    serpapi_delay,
                    output_dir,
                    force_refresh="serpapi" in refresh_sources or "google" in refresh_sources,
                )
                serpapi_results[str(paper_id)] = result
                source_statuses["SerpAPI (Google)"].append(result["status"])
                raw_file_count += len(result.get("raw", []))
                if not result.get("cached"):
                    time.sleep(serpapi_delay)
        if "scopus" in selected_sources and not scopus_stopped:
            result, fatal = fetch_scopus(
                session, paper_id, doi, env.get("SCOPUS_KEY", ""), scopus_delay, output_dir
            )
            scopus_results[str(paper_id)] = result
            source_statuses["Scopus"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if fatal:
                scopus_stopped = result["status"]
            else:
                time.sleep(scopus_delay)
        print(f"processed {index + 1}/{len(targets)} paper_id={paper_id}", flush=True)

    target_orcids = (
        {
            orcid
            for value in targets["First_Author_ORCID_OpenAlex"].tolist()
            for orcid in [normalize_orcid(value)]
            if orcid
        }
        | {
            orcid
            for value in targets["Corresponding_Author_ORCIDs_OpenAlex"].tolist()
            for orcid in str(value).split(" | ")
            if normalize_orcid(orcid)
        }
    )
    for source_result in list(pubmed_results.values()) + list(europepmc_results.values()) + list(semantic_results.values()) + list(crossref_results.values()) + list(elsevier_results.values()) + list(ieee_results.values()) + list(scopus_results.values()):
        for author in source_result.get("authors", []) or []:
            candidate = normalize_orcid(author.get("orcid", ""))
            if candidate:
                target_orcids.add(candidate)
    target_orcids = sorted(target_orcids)
    target_dois = {normalize_doi(value) for value in targets["DOI"].tolist() if normalize_doi(value)}
    if "orcid" in selected_sources:
        for index, orcid in enumerate(target_orcids, start=1):
            result = fetch_orcid(session, orcid, target_dois, orcid_delay, output_dir)
            orcid_results[orcid] = result
            source_statuses["ORCID"].append(result["status"])
            raw_file_count += len(result.get("raw", []))
            if not result.get("cached"):
                time.sleep(orcid_delay)
            print(f"processed ORCID {index}/{len(target_orcids)}", flush=True)

    source_author_rows: list[dict[str, Any]] = []
    for source_result in list(pubmed_results.values()) + list(europepmc_results.values()) + list(semantic_results.values()) + list(crossref_results.values()) + list(elsevier_results.values()) + list(ieee_results.values()) + list(scopus_results.values()):
        append_source_author_rows(source_author_rows, source_result, name_to_code, iso3_to_code)
    source_authors = pd.DataFrame(source_author_rows)
    if source_authors.empty:
        source_authors = pd.DataFrame(
            columns=[
                "Paper_ID", "DOI", "Source", "Source_Status", "Author_Order", "Author_Name", "Author_ID",
                "ORCID", "Author_Position", "Is_Corresponding", "Corresponding_Evidence", "Affiliation",
                "Country_Candidate", "Country_Candidate_Method",
            ]
        )
    source_authors.to_csv(output_dir / "multisource_author_affiliation_candidates.csv", index=False, encoding="utf-8")

    role_rows: list[dict[str, Any]] = []
    unknown_rows: list[dict[str, Any]] = []
    manual_queue_rows: list[dict[str, Any]] = []
    for _, row in targets.iterrows():
        paper_id = str(row["Paper_ID"])
        target_doi = normalize_doi(row.get("DOI", ""))
        pubmed_first = first_author_record(pubmed_results.get(paper_id, {}))
        europepmc_first = first_author_record(europepmc_results.get(paper_id, {}))
        semantic_first = first_author_record(semantic_results.get(paper_id, {}))
        crossref_first = first_author_record(crossref_results.get(paper_id, {}))
        elsevier_first = first_author_record(elsevier_results.get(paper_id, {}))
        ieee_first = first_author_record(ieee_results.get(paper_id, {}))
        scopus_first = first_author_record(scopus_results.get(paper_id, {}))
        publication_sources = [
            result
            for result in [
                pubmed_results.get(paper_id, {}),
                europepmc_results.get(paper_id, {}),
                semantic_results.get(paper_id, {}),
                crossref_results.get(paper_id, {}),
                elsevier_results.get(paper_id, {}),
                ieee_results.get(paper_id, {}),
                scopus_results.get(paper_id, {}),
            ]
            if result
        ]
        publication_country_evidence: dict[str, str] = {}
        for source_result in publication_sources:
            source_name = str(source_result.get("source", "")).strip()
            countries: set[str] = set()
            for author in source_result.get("authors", []) or []:
                countries.update(country_candidates_all(author.get("affiliation", ""), name_to_code, iso3_to_code))
            if source_name and countries:
                publication_country_evidence[source_name] = "|".join(sorted(countries))
        serpapi_contacts = serpapi_results.get(paper_id, {}).get("contacts", []) or []
        source_author_records = [
            author
            for source_result in publication_sources
            for author in source_result.get("authors", []) or []
        ]
        serpapi_corresponding_names: list[str] = []
        serpapi_corresponding_countries: list[str] = []
        serpapi_matched_signatures: set[tuple[str, str]] = set()
        serpapi_matched_surnames: set[str] = set()
        known_country_codes = set(name_to_code.values())
        for contact in serpapi_contacts:
            matched_authors = [
                author
                for author in source_author_records
                if contact_matches_author(contact, author.get("name", ""))
            ]
            matched_signatures = set()
            for author in matched_authors:
                signature = author_name_signature(author.get("name", ""))
                surname = signature[0]
                if signature in matched_signatures or signature in serpapi_matched_signatures or surname in serpapi_matched_surnames:
                    continue
                matched_signatures.add(signature)
                serpapi_matched_signatures.add(signature)
                serpapi_matched_surnames.add(surname)
                author_name = str(author.get("name", "")).strip()
                if author_name and author_name not in serpapi_corresponding_names:
                    serpapi_corresponding_names.append(author_name)
                email_country = contact_email_country(contact, known_country_codes)
                affiliation_countries = country_candidates_all(
                    author.get("affiliation", ""), name_to_code, iso3_to_code
                )
                if email_country and email_country in affiliation_countries:
                    serpapi_corresponding_countries.append(email_country)
        first_candidates: dict[str, str] = {}
        for source_name, author in [
            ("PubMed", pubmed_first),
            ("Europe PMC", europepmc_first),
            ("Semantic Scholar", semantic_first),
            ("Crossref", crossref_first),
            ("Elsevier Abstract API", elsevier_first),
            ("IEEE Computer Society CSDL", ieee_first),
            ("Scopus", scopus_first),
        ]:
            candidate, _ = author_country_candidate(author, name_to_code, iso3_to_code)
            if candidate:
                first_candidates[source_name] = candidate
        first_orcid_ids = collect_role_orcids(
            row.get("First_Author_Name_OpenAlex", ""),
            [row.get("First_Author_ORCID_OpenAlex", "")],
            publication_sources,
        )
        first_profiles = [orcid_results[orcid] for orcid in first_orcid_ids if orcid in orcid_results]
        first_employment = orcid_profile_summary(first_profiles, {"employment"}, target_doi)
        first_education = orcid_profile_summary(first_profiles, {"education", "qualification"}, target_doi)
        first_orcid_countries = sorted(
            set(value for value in (first_employment["countries"] + " | " + first_education["countries"]).split(" | ") if value)
        )
        first_orcid_work_match = first_employment["work_match"] == "Yes" or first_education["work_match"] == "Yes"
        first_unique = sorted(set(first_candidates.values()))
        first_consensus = first_unique[0] if len(first_unique) == 1 else ""
        first_baseline = str(row.get("First_Author_Country_OpenAlex", "")).strip()
        baseline_codes = {value.strip().upper() for value in first_baseline.split("|") if value.strip()}
        first_reason = []
        if first_baseline and first_candidates and not set(first_unique).issubset(baseline_codes):
            first_status = "conflict"
            first_suggested = ""
            first_reason.append("publication metadata candidate conflicts with OpenAlex affiliation country")
        elif first_baseline:
            first_status = "resolved_existing_publication_metadata"
            first_suggested = sorted(baseline_codes)[0] if len(baseline_codes) == 1 else first_baseline
        elif len(first_unique) == 1:
            first_status = "resolved_secondary_publication_metadata"
            first_suggested = first_unique[0]
            first_reason.append("single country candidate recovered from publication-level metadata")
        elif len(first_unique) > 1:
            first_status = "conflict"
            first_suggested = ""
            first_reason.append("publication-level country candidates conflict")
        elif len(first_orcid_countries) == 1 and first_orcid_work_match:
            first_status = "candidate_orcid_work_link_requires_affiliation_check"
            first_suggested = first_orcid_countries[0]
            first_reason.append("ORCID work matches the DOI and supplies one profile country, but publication affiliation still requires confirmation")
        else:
            first_status = "unresolved_no_external_candidate"
            first_suggested = ""
            first_reason.append("no external publication-level or linked ORCID country candidate")
        first_income_candidate = code_to_income.get(first_suggested, "")

        corresponding_baseline = str(row.get("Corresponding_Author_Country_OpenAlex", "")).strip()
        paper_single_country = single_country_from_all_authors(authorships, paper_id)
        corr_names = [value.strip() for value in str(row.get("Corresponding_Author_Names_OpenAlex", "")).split(" | ") if value.strip()]
        baseline_corr_names = list(corr_names)
        explicit_corresponding_names: list[str] = []
        explicit_corresponding_candidates: list[tuple[str, str]] = []
        for source_result in publication_sources:
            source_name = str(source_result.get("source", ""))
            for author in source_result.get("authors", []) or []:
                if not bool_text(author.get("is_corresponding", False)):
                    continue
                author_name = str(author.get("name", "")).strip()
                if author_name and author_name not in explicit_corresponding_names:
                    explicit_corresponding_names.append(author_name)
                candidate, _ = author_country_candidate(author, name_to_code, iso3_to_code)
                if candidate:
                    explicit_corresponding_candidates.append((source_name, candidate))
        for author_name in explicit_corresponding_names:
            if author_name not in corr_names:
                corr_names.append(author_name)
        for author_name in serpapi_corresponding_names:
            if author_name not in corr_names:
                corr_names.append(author_name)
        corr_baseline_orcids = [value for value in str(row.get("Corresponding_Author_ORCIDs_OpenAlex", "")).split(" | ") if normalize_orcid(value)]
        corr_orcid_ids = sorted({
            orcid
            for name in corr_names
            for orcid in collect_role_orcids(name, corr_baseline_orcids, publication_sources)
            if orcid
        })
        corr_profiles = [orcid_results[orcid] for orcid in corr_orcid_ids if orcid in orcid_results]
        corr_employment = orcid_profile_summary(corr_profiles, {"employment"}, target_doi)
        corr_education = orcid_profile_summary(corr_profiles, {"education", "qualification"}, target_doi)
        corr_orcid_countries = sorted(
            set(value for value in (corr_employment["countries"] + " | " + corr_education["countries"]).split(" | ") if value)
        )
        corr_provider_candidates = author_country_candidates_for_names(
            corr_names, publication_sources, name_to_code, iso3_to_code
        )
        corr_unique = sorted(set(corr_provider_candidates.values()))
        corr_explicit_unique = sorted(set(country for _, country in explicit_corresponding_candidates))
        serpapi_country_unique = sorted(set(serpapi_corresponding_countries))
        corr_reason = []
        if corresponding_baseline:
            corr_status = "resolved_existing_publication_metadata"
            corr_suggested = sorted(value.strip().upper() for value in corresponding_baseline.split("|") if value.strip())[0]
        elif explicit_corresponding_names and len(corr_unique) == 1:
            corr_status = "resolved_explicit_corresponding_metadata"
            corr_suggested = corr_unique[0]
            corr_reason.append(
                "Europe PMC full text explicitly identifies the corresponding author and publication-level metadata supplies one country"
            )
        elif explicit_corresponding_names and len(corr_explicit_unique) > 1:
            corr_status = "conflict"
            corr_suggested = ""
            corr_reason.append("full-text corresponding-author affiliations contain multiple country candidates")
        elif serpapi_corresponding_names and len(serpapi_country_unique) == 1:
            corr_status = "resolved_serpapi_correspondence"
            corr_suggested = serpapi_country_unique[0]
            corr_reason.append(
                "DOI-specific search result states the correspondence contact; the contact matches one publication author and its country-code email agrees with the recorded affiliation"
            )
        elif baseline_corr_names and len(corr_unique) == 1:
            corr_status = "resolved_openalex_role_plus_external_affiliation"
            corr_suggested = corr_unique[0]
            corr_reason.append(
                "OpenAlex identifies the corresponding author and an external publication metadata source supplies one matching affiliation country"
            )
        elif paper_single_country and len(corr_unique) <= 1:
            corr_status = "resolved_paper_single_country"
            corr_suggested = paper_single_country
            corr_reason.append(
                "all publication authors have one identical affiliation country; the corresponding-author country is deterministic even though the role marker is unavailable"
            )
        elif len(corr_unique) == 1:
            corr_status = "candidate_author_affiliation_requires_role_validation"
            corr_suggested = corr_unique[0]
            corr_reason.append("provider affiliation matches a corresponding-author name, but the corresponding role still requires article confirmation")
        elif len(corr_unique) > 1:
            corr_status = "conflict"
            corr_suggested = ""
            corr_reason.append("provider affiliation candidates for the corresponding author conflict")
        elif len(corr_orcid_countries) == 1 and (corr_employment["work_match"] == "Yes" or corr_education["work_match"] == "Yes"):
            corr_status = "candidate_orcid_work_link_requires_role_validation"
            corr_suggested = corr_orcid_countries[0]
            corr_reason.append("ORCID work matches the DOI and supplies one profile country, but the corresponding role and publication affiliation require article confirmation")
        else:
            corr_status = "unresolved_no_external_candidate"
            corr_suggested = ""
            if publication_country_evidence:
                corr_reason.append(
                    "publication-level affiliation countries are available, but no provider exposes a validated corresponding-author role"
                )
            else:
                corr_reason.append("no external country candidate and no validated corresponding-author role")
        if not corresponding_baseline and not corr_reason:
            corr_reason.append("corresponding-author role requires article confirmation")
        role_row = {
            "Paper_ID": paper_id,
            "DOI": row.get("DOI", ""),
            "Title": row.get("Title", ""),
            "First_Author_Name_OpenAlex": row.get("First_Author_Name_OpenAlex", ""),
            "First_Author_Country_OpenAlex": first_baseline,
            "First_Author_WB_Group_Current": row.get("First_Author_WB_Group", ""),
            "PubMed_Status": pubmed_results.get(paper_id, {}).get("status", "not_run"),
            "PubMed_First_Author": pubmed_first.get("name", ""),
            "PubMed_First_Affiliation": pubmed_first.get("affiliation", ""),
            "PubMed_First_Country_Candidate": first_candidates.get("PubMed", ""),
            "EuropePMC_Status": europepmc_results.get(paper_id, {}).get("status", "not_run"),
            "EuropePMC_PMID": europepmc_results.get(paper_id, {}).get("pmid", ""),
            "EuropePMC_PMCID": europepmc_results.get(paper_id, {}).get("pmcid", ""),
            "EuropePMC_FullText_Status": europepmc_results.get(paper_id, {}).get("fulltext_status", "not_run"),
            "EuropePMC_First_Author": europepmc_first.get("name", ""),
            "EuropePMC_First_Affiliation": europepmc_first.get("affiliation", ""),
            "EuropePMC_First_Country_Candidate": first_candidates.get("Europe PMC", ""),
            "EuropePMC_Explicit_Corresponding_Names": " | ".join(explicit_corresponding_names),
            "EuropePMC_Explicit_Corresponding_Countries": " | ".join(corr_explicit_unique),
            "EuropePMC_Explicit_Corresponding_Evidence": " | ".join(
                f"{source}:{country}" for source, country in explicit_corresponding_candidates
            ),
            "SerpAPI_Status": serpapi_results.get(paper_id, {}).get("status", "not_run"),
            "SerpAPI_Contacts": " | ".join(
                " ".join(value for value in [contact.get("Email", ""), contact.get("Initials", "")] if value)
                for contact in serpapi_contacts
            ),
            "SerpAPI_Matched_Corresponding_Names": " | ".join(serpapi_corresponding_names),
            "SerpAPI_Corresponding_Countries": " | ".join(serpapi_country_unique),
            "Semantic_Status": semantic_results.get(paper_id, {}).get("status", "not_run"),
            "Semantic_First_Author": semantic_first.get("name", ""),
            "Semantic_First_Affiliation": semantic_first.get("affiliation", ""),
            "Semantic_First_Country_Candidate": first_candidates.get("Semantic Scholar", ""),
            "Crossref_Status": crossref_results.get(paper_id, {}).get("status", "not_run"),
            "Crossref_First_Author": crossref_first.get("name", ""),
            "Crossref_First_Affiliation": crossref_first.get("affiliation", ""),
            "Crossref_First_Country_Candidate": first_candidates.get("Crossref", ""),
            "Elsevier_Status": elsevier_results.get(paper_id, {}).get("status", "not_run"),
            "Elsevier_First_Author": elsevier_first.get("name", ""),
            "Elsevier_First_Affiliation": elsevier_first.get("affiliation", ""),
            "Elsevier_First_Country_Candidate": first_candidates.get("Elsevier Abstract API", ""),
            "Elsevier_Corresponding_Role_Available": "Yes" if elsevier_results.get(paper_id, {}).get("corresponding_role_available") else "No",
            "IEEE_CSDL_Status": ieee_results.get(paper_id, {}).get("status", "not_run"),
            "IEEE_CSDL_Article_ID": ieee_results.get(paper_id, {}).get("article_id", ""),
            "IEEE_CSDL_First_Author": ieee_first.get("name", ""),
            "IEEE_CSDL_First_Affiliation": ieee_first.get("affiliation", ""),
            "IEEE_CSDL_First_Country_Candidate": first_candidates.get("IEEE Computer Society CSDL", ""),
            "IEEE_CSDL_Corresponding_Role_Available": "Yes" if ieee_results.get(paper_id, {}).get("corresponding_role_available") else "No",
            "Scopus_Status": scopus_results.get(paper_id, {}).get("status", "not_run"),
            "Scopus_First_Author": scopus_first.get("name", ""),
            "Scopus_First_Affiliation": scopus_first.get("affiliation", ""),
            "Scopus_First_Country_Candidate": first_candidates.get("Scopus", ""),
            "ORCID_First_ID": " | ".join(first_orcid_ids),
            "ORCID_First_Organization": first_employment["organizations"],
            "ORCID_First_Country": first_employment["countries"],
            "ORCID_First_Education_Organization": first_education["organizations"],
            "ORCID_First_Education_Country": first_education["countries"],
            "ORCID_First_Work_Match": first_employment["work_match"] if first_employment["work_match"] == "Yes" else first_education["work_match"],
            "ORCID_First_Work_Details": " | ".join(dict.fromkeys(value for value in [first_employment["work_matches"], first_education["work_matches"]] if value)),
            "First_Country_Candidates": " | ".join(
                [*(f"{source}:{country}" for source, country in sorted(first_candidates.items())),
                 *(f"ORCID_{kind}:{country}" for kind, country in [("employment", first_employment["countries"]), ("education", first_education["countries"])] if country)]
            ),
            "Suggested_First_Country": first_suggested,
            "Suggested_First_WB_Group": first_income_candidate,
            "First_Country_Resolution_Status": first_status,
            "First_Country_Manual_Required": "No" if first_status.startswith("resolved_") else "Yes",
            "First_Country_Manual_Reason": "; ".join(first_reason),
            "Corresponding_Author_Names_OpenAlex": row.get("Corresponding_Author_Names_OpenAlex", ""),
            "Corresponding_Author_Names_External_Explicit": " | ".join(explicit_corresponding_names),
            "Corresponding_Author_Country_OpenAlex": corresponding_baseline,
            "OpenAlex_All_Authors_Single_Country": paper_single_country,
            "Corresponding_Publication_Country_Evidence": " | ".join(
                f"{source}:{countries}" for source, countries in sorted(publication_country_evidence.items())
            ),
            "ORCID_Corresponding_IDs": " | ".join(corr_orcid_ids),
            "ORCID_Corresponding_Organizations": corr_employment["organizations"],
            "ORCID_Corresponding_Countries": corr_employment["countries"],
            "ORCID_Corresponding_Education_Organizations": corr_education["organizations"],
            "ORCID_Corresponding_Education_Countries": corr_education["countries"],
            "ORCID_Corresponding_Work_Match": corr_employment["work_match"] if corr_employment["work_match"] == "Yes" else corr_education["work_match"],
            "ORCID_Corresponding_Work_Details": " | ".join(dict.fromkeys(value for value in [corr_employment["work_matches"], corr_education["work_matches"]] if value)),
            "Corresponding_Country_Candidates": " | ".join(
                [*(f"{source}:{country}" for source, country in sorted(corr_provider_candidates.items())),
                 *(f"ORCID_{kind}:{country}" for kind, country in [("employment", corr_employment["countries"]), ("education", corr_education["countries"])] if country),
                 *(f"SerpAPI:{country}" for country in serpapi_country_unique)]
            ),
            "Suggested_Corresponding_Country": corr_suggested,
            "Corresponding_Country_Resolution_Status": corr_status,
            "Corresponding_Country_Manual_Required": "No" if corr_status.startswith("resolved_") else "Yes",
            "Corresponding_Country_Manual_Reason": "; ".join(corr_reason),
        }
        role_rows.append(role_row)
        if role_row["First_Country_Manual_Required"] == "Yes":
            manual_row = {
                "Paper_ID": paper_id,
                "DOI": row.get("DOI", ""),
                "Title": row.get("Title", ""),
                "Role": "first_author_country",
                "Resolution_Status": first_status,
                "Reason": role_row["First_Country_Manual_Reason"],
                "Suggested_Country": first_suggested,
                "Evidence_Candidates": role_row["First_Country_Candidates"],
                "ORCID_Work_Match": role_row["ORCID_First_Work_Match"],
            }
            manual_queue_rows.append(manual_row)
            if first_status in {"conflict", "unresolved_no_external_candidate"}:
                unknown_rows.append(manual_row)
        if role_row["Corresponding_Country_Manual_Required"] == "Yes":
            manual_row = {
                "Paper_ID": paper_id,
                "DOI": row.get("DOI", ""),
                "Title": row.get("Title", ""),
                "Role": "corresponding_author_country",
                "Resolution_Status": corr_status,
                "Reason": role_row["Corresponding_Country_Manual_Reason"],
                "Suggested_Country": corr_suggested,
                "Evidence_Candidates": role_row["Corresponding_Country_Candidates"] or role_row["Corresponding_Publication_Country_Evidence"],
                "ORCID_Work_Match": role_row["ORCID_Corresponding_Work_Match"],
            }
            manual_queue_rows.append(manual_row)
            if corr_status in {"conflict", "unresolved_no_external_candidate"}:
                unknown_rows.append(manual_row)

    role_audit = pd.DataFrame(role_rows)
    unknown_audit = pd.DataFrame(unknown_rows)
    manual_queue = pd.DataFrame(manual_queue_rows)
    role_audit.to_csv(output_dir / "multisource_role_audit.csv", index=False, encoding="utf-8")
    unknown_audit.to_csv(output_dir / "multisource_unknown_audit.csv", index=False, encoding="utf-8")
    manual_queue.to_csv(output_dir / "multisource_manual_confirmation_queue.csv", index=False, encoding="utf-8")

    doi_to_paper = {
        normalize_doi(row.get("DOI", "")): str(row.get("Paper_ID", ""))
        for _, row in targets.iterrows()
        if normalize_doi(row.get("DOI", ""))
    }
    orcid_affiliation_rows: list[dict[str, Any]] = []
    orcid_work_rows: list[dict[str, Any]] = []
    for orcid, profile in sorted(orcid_results.items()):
        raw_by_endpoint = {str(item.get("endpoint", "")): item for item in profile.get("raw", []) or []}
        for record in profile.get("affiliations", []) or []:
            endpoint = str(record.get("affiliation_type", "")) + "s"
            raw = raw_by_endpoint.get(endpoint, {})
            orcid_affiliation_rows.append(
                {
                    "ORCID": orcid,
                    "ORCID_Status": profile.get("status", ""),
                    "Affiliation_Type": record.get("affiliation_type", ""),
                    "Organization": record.get("organization", ""),
                    "Department": record.get("department", ""),
                    "Role_Title": record.get("role_title", ""),
                    "City": record.get("city", ""),
                    "Country": record.get("country", ""),
                    "Start_Year": record.get("start_year", ""),
                    "End_Year": record.get("end_year", ""),
                    "Source_Name": record.get("source_name", ""),
                    "Raw_File": raw.get("path", ""),
                    "Raw_SHA256": raw.get("sha256", ""),
                }
            )
        details_by_doi = {}
        for detail in profile.get("work_details", []) or []:
            for doi in str(detail.get("matched_target_dois", "")).split(" | "):
                if normalize_doi(doi):
                    details_by_doi[normalize_doi(doi)] = detail
        for work in profile.get("work_matches", []) or []:
            for doi in str(work.get("doi", "")).split(" | "):
                normalized_work_doi = normalize_doi(doi)
                if normalized_work_doi not in doi_to_paper:
                    continue
                detail = details_by_doi.get(normalized_work_doi, {})
                orcid_work_rows.append(
                    {
                        "Paper_ID": doi_to_paper[normalized_work_doi],
                        "DOI": normalized_work_doi,
                        "ORCID": orcid,
                        "Work_Title": detail.get("title", work.get("title", "")),
                        "Work_Year": detail.get("year", work.get("year", "")),
                        "Work_Type": detail.get("type", work.get("type", "")),
                        "ORCID_Work_Source": detail.get("source_name", work.get("source_name", "")),
                        "Contributors": detail.get("contributors", ""),
                        "Work_Match": "Yes",
                    }
                )
    pd.DataFrame(orcid_affiliation_rows).to_csv(output_dir / "multisource_orcid_affiliations.csv", index=False, encoding="utf-8")
    pd.DataFrame(orcid_work_rows).to_csv(output_dir / "multisource_orcid_work_matches.csv", index=False, encoding="utf-8")

    coverage_rows = []
    for source, statuses in source_statuses.items():
        counts = pd.Series(statuses, dtype="string").value_counts().to_dict()
        source_fulltext_statuses = fulltext_statuses.get(source, [])
        fulltext_counts = pd.Series(source_fulltext_statuses, dtype="string").value_counts().to_dict()
        coverage_rows.append(
            {
                "Source": source,
                "Requests": int(len(statuses)),
                "Success": int(counts.get("success", 0)),
                "Not_Indexed": int(counts.get("not_indexed", 0)),
                "Not_Applicable": int(counts.get("not_applicable", 0)),
                "Auth_or_Access_Errors": int(sum(counts.get(status, 0) for status in ["auth_error", "bad_request_or_access_error"])),
                "Rate_Limited": int(counts.get("rate_limited", 0)),
                "Other_Errors": int(sum(count for status, count in counts.items() if status not in {"success", "not_indexed", "not_applicable", "auth_error", "bad_request_or_access_error", "rate_limited"})),
                "Status_Breakdown": json.dumps(counts, ensure_ascii=False, sort_keys=True),
                "FullText_Requests": int(sum(count for status, count in fulltext_counts.items() if status not in {"not_attempted", "not_available"})),
                "FullText_Success": int(fulltext_counts.get("success", 0)),
                "FullText_Status_Breakdown": json.dumps(fulltext_counts, ensure_ascii=False, sort_keys=True),
            }
        )
    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(output_dir / "multisource_coverage.csv", index=False, encoding="utf-8")

    manifest = {
        "run_timestamp_utc": now_utc(),
        "corpus": "MRI-LMICs-survey included studies",
        "source_studies": int(len(targets)),
        "input_files": {
            "review_metadata_joined": {"path": str(REVIEW_METADATA), "sha256": sha256_file(REVIEW_METADATA)},
            "openalex_authorships": {"path": str(OPENALEX_AUTHORS), "sha256": sha256_file(OPENALEX_AUTHORS)},
            "world_bank_snapshot": {"path": str(WORLD_BANK), "sha256": sha256_file(WORLD_BANK)},
        },
        "credentials": {
            "pubmed_key_present": bool(env.get("PUBMED_KEY")),
            "semantic_key_present": bool(env.get("SEMANTIC_KEY")),
            "scopus_key_present": bool(env.get("SCOPUS_KEY")),
            "elsevier_key_present": bool(env.get("SCOPUS_KEY")),
            "credentials_written_to_outputs": False,
            "serpapi_key_present": bool(env.get("SCHOLAR_KEY")),
        },
        "sources_requested": sorted(selected_sources),
        "serpapi_query_policy": {
            "all_dois": serpapi_all,
            "refresh_sources": sorted(refresh_sources),
            "queries_per_doi": 2,
        },
        "endpoint_bases": {
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            "europepmc_search": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            "europepmc_fulltext": "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
            "serpapi_google": "https://serpapi.com/search.json",
            "semantic_scholar": "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            "crossref": "https://api.crossref.org/works/{doi}",
            "elsevier_abstract": "https://api.elsevier.com/content/abstract/doi/{doi}",
            "ieee_csdl_graphql": "https://www.computer.org/csdl/api/v1/graphql",
            "orcid": "https://pub.orcid.org/v3.0/{orcid}/employments",
            "orcid_educations": "https://pub.orcid.org/v3.0/{orcid}/educations",
            "orcid_qualifications": "https://pub.orcid.org/v3.0/{orcid}/qualifications",
            "orcid_works": "https://pub.orcid.org/v3.0/{orcid}/works",
            "scopus": "https://api.elsevier.com/content/search/scopus",
        },
        "raw_response_files": int(raw_file_count),
        "scopus_stopped_after_access_error": scopus_stopped,
        "coverage_file": "multisource_coverage.csv",
        "role_audit_file": "multisource_role_audit.csv",
        "unknown_audit_file": "multisource_unknown_audit.csv",
        "manual_confirmation_queue_file": "multisource_manual_confirmation_queue.csv",
        "orcid_affiliations_file": "multisource_orcid_affiliations.csv",
        "orcid_work_matches_file": "multisource_orcid_work_matches.csv",
        "manual_review_policy": {
            "first_author_country": "resolved when a single publication-level country candidate is available; ORCID-only candidates remain article-confirmation candidates",
            "corresponding_author_country": "resolved automatically when an explicit full-text corresponding-author marker, an OpenAlex corresponding role plus matching external affiliation, or a deterministic single-country record supports one country; otherwise retained as candidate or unknown",
            "unknown_audit": "contains only conflicts and cases without any external country candidate; candidate-but-unverified rows are in the manual confirmation queue",
            "income_group": "derived only from a confirmed country using the cached World Bank classification",
            "canonical_review_data_modified": False,
            "github_modified": False,
        },
    }
    (output_dir / "multisource_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# MRI multi-source scientometric enrichment\n\n"
        "This is a local, optional enrichment run for the 48 included MRI studies. "
        "It does not overwrite `data/data-clean.csv`, the OpenAlex baseline, or GitHub. "
        "Raw API responses are stored under `raw/` with hashes. Crossref, PubMed, Europe PMC, "
        "Elsevier Abstract API, IEEE Computer Society CSDL and Semantic Scholar provide "
        "publication-level author metadata; Europe PMC JATS full text is parsed for explicit "
        "corresponding-author markers when available. Elsevier is queried through the credentialed "
        "abstract endpoint for DOI-level first-author affiliation evidence; IEEE CSDL is queried "
        "through its public GraphQL metadata endpoint. "
        "ORCID provides employment, education, qualification and work-link evidence. Provider metadata "
        "is candidate evidence unless the full-text role is explicit or OpenAlex identifies the role "
        "and an external publication affiliation agrees. SerpAPI/Google runs two DOI-specific "
        "queries per paper when `--serpapi-all` is supplied; otherwise it is limited to papers still "
        "lacking a deterministic corresponding country. A contact is accepted only when it matches "
        "one publication author and the country-code email agrees with the publication affiliation. "
        "Credentials are read from the generic tool `.env` or an ephemeral `SCHOLAR_KEY` environment "
        "override and are not written to outputs.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["pubmed", "europepmc", "semantic", "crossref", "orcid", "scopus", "serpapi", "elsevier", "ieee_csdl"],
        help="Sources to query: pubmed europepmc semantic crossref elsevier ieee_csdl orcid scopus serpapi",
    )
    parser.add_argument(
        "--refresh-sources",
        nargs="*",
        default=[],
        help="Bypass cached responses for selected sources; use 'serpapi' to refresh DOI-specific Google queries.",
    )
    parser.add_argument(
        "--serpapi-all",
        action="store_true",
        help="Run the two DOI-specific SerpAPI queries for every DOI instead of only unresolved correspondence cases.",
    )
    args = parser.parse_args()
    manifest = run(args)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "source_studies": manifest["source_studies"], "raw_response_files": manifest["raw_response_files"], "scopus_stopped_after_access_error": manifest["scopus_stopped_after_access_error"]}, indent=2))


if __name__ == "__main__":
    main()
