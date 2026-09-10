"""Canonical 48-study identity and Paper_ID alignment utilities.

The included-study order is a public data contract.  IDs are assigned by an
exact title match to the reference corpus and are never corrected by shifting
or arithmetic on legacy IDs.  DOI matching is used as a second identity check
where DOI columns are available.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import unicodedata
from pathlib import Path

import pandas as pd


EXPECTED_STUDIES = 48
ID_COLUMN = "Paper_ID"
TITLE_COLUMN = "Title"
DOI_COLUMN = "DOI"
SCREENING_LOG_NAME = "screening_log_"


def normalize_title(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = text.translate(str.maketrans({"–": "-", "—": "-", "’": "'", "‘": "'"}))
    text = text.replace("\u00a0", " ")
    return " ".join(text.split()).casefold()


def normalize_doi(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.rstrip("/").strip()
    if text in {"", "not available", "not reported", "unknown", "n/a"}:
        return ""
    return text


def _read_csv_bytes(payload: bytes, label: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(payload))
    except Exception as exc:  # pragma: no cover - diagnostic wrapper
        raise ValueError(f"Could not read {label} as CSV: {exc}") from exc


def read_git_csv(repo: Path, revision: str = "origin/main:data/data-clean.csv") -> pd.DataFrame:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", revision],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Unable to read canonical reference {revision}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    return _read_csv_bytes(result.stdout, revision)


def _require_study_columns(frame: pd.DataFrame, label: str) -> None:
    missing = {ID_COLUMN, TITLE_COLUMN} - set(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing required identity columns: {sorted(missing)}")


def _check_unique_titles(frame: pd.DataFrame, label: str) -> pd.Series:
    keys = frame[TITLE_COLUMN].map(normalize_title)
    if keys.eq("").any():
        raise ValueError(f"{label} contains blank study titles")
    if keys.duplicated().any():
        duplicates = frame.loc[keys.duplicated(keep=False), TITLE_COLUMN].tolist()
        raise ValueError(f"{label} contains duplicate normalized titles: {duplicates}")
    return keys


def validate_reference(reference: pd.DataFrame, label: str = "canonical reference") -> pd.DataFrame:
    _require_study_columns(reference, label)
    result = reference.copy()
    result[ID_COLUMN] = pd.to_numeric(result[ID_COLUMN], errors="raise").astype(int)
    if len(result) != EXPECTED_STUDIES:
        raise ValueError(f"{label} must contain exactly {EXPECTED_STUDIES} studies")
    if result[ID_COLUMN].tolist() != list(range(1, EXPECTED_STUDIES + 1)):
        raise ValueError(f"{label} IDs must be ordered contiguously from 1 to {EXPECTED_STUDIES}")
    result["_title_key"] = _check_unique_titles(result, label)
    return result


def build_crosswalk(current: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Build old-to-canonical IDs using exact normalized titles."""

    _require_study_columns(current, "current canonical data")
    current = current.copy()
    current[ID_COLUMN] = pd.to_numeric(current[ID_COLUMN], errors="raise").astype(int)
    if len(current) != EXPECTED_STUDIES or current[ID_COLUMN].nunique() != EXPECTED_STUDIES:
        raise ValueError("Current canonical data must contain 48 unique Paper_ID values")
    current["_title_key"] = _check_unique_titles(current, "current canonical data")

    reference = validate_reference(reference)
    current_keys = set(current["_title_key"])
    reference_keys = set(reference["_title_key"])
    if current_keys != reference_keys:
        raise ValueError(
            "Current and reference corpora do not contain the same 48 normalized titles: "
            f"missing_from_current={sorted(reference_keys - current_keys)}, "
            f"extra_in_current={sorted(current_keys - reference_keys)}"
        )

    mapping = current[[ID_COLUMN, TITLE_COLUMN, "_title_key"]].merge(
        reference[[ID_COLUMN, TITLE_COLUMN, "_title_key"]],
        on="_title_key",
        how="left",
        validate="one_to_one",
        suffixes=("_old", "_canonical"),
    )
    if mapping["Paper_ID_canonical"].isna().any():
        raise ValueError("Every current study must map to a canonical reference study")
    mapping = mapping.rename(
        columns={
            "Paper_ID_old": "Old_Paper_ID",
            "Paper_ID_canonical": "Paper_ID",
            "Title_old": "Current_Title",
            "Title_canonical": "Canonical_Title",
        }
    )
    mapping["Old_Paper_ID"] = mapping["Old_Paper_ID"].astype(int)
    mapping["Paper_ID"] = mapping["Paper_ID"].astype(int)
    return mapping[["Old_Paper_ID", "Paper_ID", "Current_Title", "Canonical_Title"]].sort_values(
        "Old_Paper_ID"
    )


def build_public_order_contract(
    reference: pd.DataFrame,
    tr_evidence: pd.DataFrame,
    additional_doi_sources: list[pd.DataFrame] | None = None,
) -> pd.DataFrame:
    reference = validate_reference(reference)
    doi_by_title: dict[str, str] = {}
    sources = [tr_evidence, *(additional_doi_sources or [])]
    for source in sources:
        if TITLE_COLUMN not in source.columns or DOI_COLUMN not in source.columns:
            continue
        for _, row in source.iterrows():
            title_key = normalize_title(row[TITLE_COLUMN])
            doi = normalize_doi(row[DOI_COLUMN])
            if not title_key or not doi:
                continue
            # The first source is the canonical evidence layer.  Later sources
            # may identify a related preprint; they are not allowed to replace
            # the canonical DOI used for study identity.
            doi_by_title.setdefault(title_key, doi)

    contract = reference[[ID_COLUMN, TITLE_COLUMN, "_title_key"]].copy()
    contract["DOI"] = contract["_title_key"].map(doi_by_title)
    if contract["DOI"].isna().any() or contract["DOI"].map(normalize_doi).eq("").any():
        missing = contract.loc[contract["DOI"].isna(), TITLE_COLUMN].tolist()
        raise ValueError(f"Missing DOI in identity contract: {missing}")
    contract["DOI"] = contract["DOI"].map(lambda value: str(value).strip())
    return contract[[ID_COLUMN, TITLE_COLUMN, DOI_COLUMN]].copy()


def remap_frame(
    frame: pd.DataFrame,
    mapping: pd.DataFrame,
    label: str,
    doi_to_new: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, str]:
    """Remap a data frame and return the method used for its identity check."""

    if ID_COLUMN not in frame.columns:
        return frame, "not_applicable"
    result = frame.copy()
    old_to_new = dict(zip(mapping["Old_Paper_ID"], mapping["Paper_ID"]))
    old_ids = set(old_to_new)
    canonical_title_by_id = dict(zip(mapping["Paper_ID"], mapping["Canonical_Title"]))

    def apply_canonical_title(mapped_frame: pd.DataFrame) -> pd.DataFrame:
        if TITLE_COLUMN in mapped_frame.columns:
            mapped_frame[TITLE_COLUMN] = mapped_frame[ID_COLUMN].map(canonical_title_by_id)
        return mapped_frame

    if TITLE_COLUMN in result.columns:
        keys = result[TITLE_COLUMN].map(normalize_title)
        title_to_new = dict(zip(mapping["Current_Title"].map(normalize_title), mapping["Paper_ID"]))
        mapped = keys.map(title_to_new)
        if mapped.isna().any() and DOI_COLUMN in result.columns:
            doi_mapped = result[DOI_COLUMN].map(normalize_doi).map(doi_to_new or {})
            mapped = mapped.fillna(doi_mapped)
            if mapped.notna().all():
                result[ID_COLUMN] = mapped.astype(int)
                return apply_canonical_title(result), "title_or_doi"
        if mapped.isna().any():
            bad = result.loc[mapped.isna(), TITLE_COLUMN].head(5).tolist()
            raise ValueError(f"{label} contains titles outside the canonical 48-study set: {bad}")
        result[ID_COLUMN] = mapped.astype(int)
        return apply_canonical_title(result), "title"

    if DOI_COLUMN in result.columns:
        doi_map = doi_to_new or {}
        mapped = result[DOI_COLUMN].map(normalize_doi).map(doi_map)
        if mapped.notna().all():
            result[ID_COLUMN] = mapped.astype(int)
            return apply_canonical_title(result), "doi"

    ids = pd.to_numeric(result[ID_COLUMN], errors="raise").astype(int)
    canonical_ids = set(range(1, EXPECTED_STUDIES + 1))
    if set(ids).issubset(canonical_ids):
        return apply_canonical_title(result), "already_canonical_without_identity_column"
    unknown = sorted(set(ids) - old_ids)
    if not unknown and (set(ids) - canonical_ids):
        result[ID_COLUMN] = ids.map(old_to_new).astype(int)
        return apply_canonical_title(result), "legacy_crosswalk"
    raise ValueError(f"{label} contains unknown legacy Paper_ID values: {unknown[:10]}")


def active_csv_paths(repo: Path) -> list[Path]:
    paths: list[Path] = []
    roots = [repo / "data", repo / "tables", repo / "analysis" / "review_20260803", repo / "analysis" / "scientometrics", repo / "analysis" / "reproducibility"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            relative = path.relative_to(repo).as_posix()
            if "provenance/" in relative:
                continue
            if path.name.casefold().startswith(SCREENING_LOG_NAME):
                continue
            if "/private/" in f"/{relative}" and path.name != "data-clean_internal.csv":
                continue
            paths.append(path)
    return sorted(set(paths))


def remap_active_csvs(repo: Path, mapping: pd.DataFrame) -> list[dict[str, str]]:
    report: list[dict[str, str]] = []
    paths = active_csv_paths(repo)
    title_to_new = dict(zip(mapping["Current_Title"].map(normalize_title), mapping["Paper_ID"]))
    doi_to_new: dict[str, int] = {}
    frames: dict[Path, pd.DataFrame] = {}
    for path in paths:
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        frames[path] = frame
        if TITLE_COLUMN in frame.columns and DOI_COLUMN in frame.columns:
            for _, row in frame.iterrows():
                title_id = title_to_new.get(normalize_title(row[TITLE_COLUMN]))
                doi = normalize_doi(row[DOI_COLUMN])
                if title_id is not None and doi:
                    doi_to_new.setdefault(doi, int(title_id))

    for path in paths:
        frame = frames.get(path)
        if frame is None:
            continue
        if ID_COLUMN not in frame.columns:
            continue
        remapped, method = remap_frame(
            frame, mapping, path.relative_to(repo).as_posix(), doi_to_new
        )
        remapped.to_csv(path, index=False, encoding="utf-8")
        report.append({"path": path.relative_to(repo).as_posix(), "method": method, "rows": str(len(frame))})
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--reference", default="origin/main:data/data-clean.csv")
    parser.add_argument("--apply", action="store_true", help="Write the contract and remap active CSV files")
    args = parser.parse_args()

    repo = args.repo.resolve()
    current_path = repo / "data" / "data-clean.csv"
    evidence_path = repo / "data" / "tr_criteria_evidence.csv"
    # Use the committed pre-migration source as the legacy side of the
    # crosswalk. This keeps reruns idempotent after a partial or completed
    # migration while the working-tree data are being regenerated.
    try:
        current = read_git_csv(repo, "HEAD:data/data-clean.csv")
    except RuntimeError:
        current = pd.read_csv(current_path)
    reference = read_git_csv(repo, args.reference)
    mapping = build_crosswalk(current, reference)
    doi_sources = [
        pd.read_csv(repo / "tables" / "mri_scientometric_results.csv")
    ] if (repo / "tables" / "mri_scientometric_results.csv").exists() else []
    contract = build_public_order_contract(reference, pd.read_csv(evidence_path), doi_sources)

    if args.apply:
        contract.to_csv(repo / "data" / "included_study_order.csv", index=False, encoding="utf-8")
        report = remap_active_csvs(repo, mapping)
    else:
        report = [{"path": "(dry-run)", "method": "no files written", "rows": str(len(mapping))}]

    print(json.dumps({
        "reference": args.reference,
        "mapping_rows": len(mapping),
        "old_ids": sorted(mapping["Old_Paper_ID"].tolist()),
        "canonical_ids": sorted(mapping["Paper_ID"].tolist()),
        "paper_24": contract.loc[contract["Paper_ID"] == 24, TITLE_COLUMN].iloc[0],
        "apply": args.apply,
        "files": report,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
