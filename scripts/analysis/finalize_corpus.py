"""Reconcile the final eligible corpus without shifting study IDs numerically.

The 48-row reviewer form is preserved as the scoring-order contract. Records
are identified by DOI and title, exclusions are applied from explicit DOI-based
rules, and the resulting eligible corpus receives contiguous final Paper_IDs.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
FORM_ORDER_PATH = REPO / "data" / "reviewer_scoring_order.csv"
FINAL_ORDER_PATH = REPO / "data" / "included_study_order.csv"
FORM_SIZE = 48

EXCLUSION_RULES = {
    "10.1101/2023.12.28.23300409": {
        "category": "Duplicate",
        "reason": (
            "Earlier medRxiv preprint of the peer-reviewed 2025 LowGAN report "
            "(DOI 10.1148/radiol.233529); retain the final article, which adds "
            "a validation cohort and expanded reported metrics."
        ),
    },
    "10.1109/inocon57975.2023.10100995": {
        "category": "Not MRI modality",
        "reason": (
            "The study demonstrates generic natural-image SRCNN enhancement "
            "and reports no MRI-specific experiment or MRI dataset."
        ),
    },
    "10.3389/fneur.2024.1330203": {
        "category": "No AI/DL method",
        "reason": (
            "The full text (Methods, p. 8) explicitly states that FouSR "
            "does not rely on deep learning. The review's eligibility scope "
            "requires an AI/deep-learning MRI enhancement or super-resolution method."
        ),
    },
}


def normalize_doi(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().casefold()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text)
    text = text.split("?", 1)[0].strip().rstrip("/ ")
    return text


def normalize_title(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = text.replace("\u00a0", " ").replace("–", "-").replace("—", "-")
    return " ".join(text.split()).casefold()


def build_form_contract(study_order: pd.DataFrame) -> pd.DataFrame:
    """Create the persistent 48-form-to-final-corpus mapping from DOI/title."""
    required = {"Paper_ID", "Title", "DOI"}
    if not required.issubset(study_order.columns):
        raise ValueError(f"Study order must contain {sorted(required)}")
    order = study_order[["Paper_ID", "Title", "DOI"]].copy()
    order["Form_Paper_ID"] = pd.to_numeric(order.pop("Paper_ID"), errors="raise").astype(int)
    order = order[["Form_Paper_ID", "Title", "DOI"]]
    order["_doi_key"] = order["DOI"].map(normalize_doi)
    order["_title_key"] = order["Title"].map(normalize_title)
    if order["Form_Paper_ID"].tolist() != list(range(1, FORM_SIZE + 1)):
        raise ValueError("Initial reviewer scoring order must be contiguous 1-48")
    if order["_doi_key"].eq("").any() or order["_doi_key"].duplicated().any():
        raise ValueError("Reviewer scoring order must have unique, non-empty DOIs")
    if order["_title_key"].eq("").any() or order["_title_key"].duplicated().any():
        raise ValueError("Reviewer scoring order must have unique, non-empty titles")

    order["Include_In_Final_Corpus"] = ~order["_doi_key"].isin(EXCLUSION_RULES)
    final_ids: list[int | None] = []
    exclusions: list[dict[str, str]] = []
    final_id = 0
    for _, row in order.iterrows():
        rule = EXCLUSION_RULES.get(row["_doi_key"])
        if rule is None:
            final_id += 1
            final_ids.append(final_id)
            exclusions.append({"category": "", "reason": ""})
        else:
            final_ids.append(None)
            exclusions.append(rule)
    order["Final_Paper_ID"] = pd.array(final_ids, dtype="Int64")
    order["Exclusion_Category"] = [row["category"] for row in exclusions]
    order["Exclusion_Reason"] = [row["reason"] for row in exclusions]
    order = order.drop(columns=["_doi_key", "_title_key"])
    validate_form_contract(order)
    return order


def validate_form_contract(contract: pd.DataFrame) -> None:
    required = {
        "Form_Paper_ID",
        "Title",
        "DOI",
        "Include_In_Final_Corpus",
        "Final_Paper_ID",
        "Exclusion_Category",
        "Exclusion_Reason",
    }
    if not required.issubset(contract.columns):
        raise ValueError(f"Scoring-order contract must contain {sorted(required)}")
    if len(contract) != FORM_SIZE:
        raise ValueError(f"Scoring-order contract must contain {FORM_SIZE} studies")
    form_ids = pd.to_numeric(contract["Form_Paper_ID"], errors="raise").astype(int)
    if form_ids.tolist() != list(range(1, FORM_SIZE + 1)):
        raise ValueError("Form_Paper_ID values must be contiguous 1-48 in scoring order")
    doi_keys = contract["DOI"].map(normalize_doi)
    title_keys = contract["Title"].map(normalize_title)
    if doi_keys.eq("").any() or doi_keys.duplicated().any():
        raise ValueError("Scoring-order contract DOIs must be unique and non-empty")
    if title_keys.eq("").any() or title_keys.duplicated().any():
        raise ValueError("Scoring-order contract titles must be unique and non-empty")

    included = contract["Include_In_Final_Corpus"].map(_as_bool)
    expected_ids = list(range(1, int(included.sum()) + 1))
    final_ids = pd.to_numeric(contract.loc[included, "Final_Paper_ID"], errors="raise").astype(int)
    if final_ids.tolist() != expected_ids:
        raise ValueError("Included Final_Paper_ID values must be contiguous and in form order")
    excluded = contract.loc[~included]
    if excluded[["Exclusion_Category", "Exclusion_Reason"]].fillna("").eq("").any().any():
        raise ValueError("Every excluded form record needs a category and evidence-based reason")


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid Include_In_Final_Corpus value: {value!r}")


def _normalize_exclusion_category(value: object) -> str:
    text = " ".join(str(value).split())
    if text.casefold() == "duplicate report":
        return "Duplicate"
    return text


def remap_study_table(source: pd.DataFrame, contract: pd.DataFrame) -> pd.DataFrame:
    """Filter/reindex a table by DOI and verify title; never shift old IDs."""
    validate_form_contract(contract)
    if "Title" not in source.columns:
        raise ValueError("Study-level source table must contain Title")
    if "_study_key" in source.columns:
        raise ValueError("Source table contains a reserved internal join field")

    source = source.copy()
    use_doi = "DOI" in source.columns
    key_function = normalize_doi if use_doi else normalize_title
    source["_study_key"] = source["DOI" if use_doi else "Title"].map(key_function)
    if source["_study_key"].eq("").any() or source["_study_key"].duplicated().any():
        raise ValueError("Source table must contain unique, non-empty study identities")

    mapping = contract.copy()
    mapping["_study_key"] = mapping["DOI" if use_doi else "Title"].map(key_function)
    mapping["_title_key"] = mapping["Title"].map(normalize_title)
    included = mapping["Include_In_Final_Corpus"].map(_as_bool)
    full_keys = set(mapping["_study_key"])
    active_keys = set(mapping.loc[included, "_study_key"])
    source_keys = set(source["_study_key"])
    if not active_keys.issubset(source_keys) or not source_keys.issubset(full_keys):
        missing = sorted(active_keys - source_keys)
        unexpected = sorted(source_keys - full_keys)
        raise ValueError(
            "Source DOI set does not cover the final corpus or contains unknown studies; "
            f"missing eligible DOI count={len(missing)}, unexpected DOI count={len(unexpected)}"
        )

    merged = source.merge(
        mapping[
            [
                "_study_key",
                "_title_key",
                "DOI",
                "Include_In_Final_Corpus",
                "Final_Paper_ID",
            ]
        ],
        on="_study_key",
        how="left",
        validate="one_to_one",
    )
    if merged["Include_In_Final_Corpus"].isna().any():
        raise ValueError("A source DOI is absent from the scoring-order contract")
    title_keys = merged["Title"].map(normalize_title)
    if not title_keys.equals(merged["_title_key"]):
        key_label = "DOI" if use_doi else "title"
        raise ValueError(f"Source title does not match the contract title for its {key_label}")
    if use_doi and not merged["DOI_x"].map(normalize_doi).equals(merged["DOI_y"].map(normalize_doi)):
        raise ValueError("Source DOI does not match the contract DOI for its title")

    result = merged.loc[merged["Include_In_Final_Corpus"]].copy()
    if use_doi:
        result["DOI"] = result["DOI_x"]
        result = result.drop(columns=["DOI_x", "DOI_y"])
    else:
        result["DOI"] = result["DOI"]
    result["Paper_ID"] = pd.to_numeric(result["Final_Paper_ID"], errors="raise").astype(int)
    result = result.drop(columns=["_study_key", "_title_key", "Include_In_Final_Corpus", "Final_Paper_ID"])
    result = result.sort_values("Paper_ID", kind="stable").reset_index(drop=True)
    expected_ids = list(range(1, int(included.sum()) + 1))
    if result["Paper_ID"].tolist() != expected_ids:
        raise ValueError("Remapped table is not contiguous in canonical order")
    return result


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def _load_or_create_form_contract() -> pd.DataFrame:
    if FORM_ORDER_PATH.exists():
        existing = pd.read_csv(FORM_ORDER_PATH)
        required = {"Form_Paper_ID", "Title", "DOI"}
        if not required.issubset(existing.columns):
            raise ValueError(f"Existing scoring-order contract must contain {sorted(required)}")
        # Recompute eligibility and final IDs from the versioned DOI rules on
        # every run; otherwise a previously promoted contract can silently
        # retain stale include/exclude decisions after a rule is corrected.
        return build_form_contract(
            existing[["Form_Paper_ID", "Title", "DOI"]].rename(
                columns={"Form_Paper_ID": "Paper_ID"}
            )
        )
    current = pd.read_csv(FINAL_ORDER_PATH)
    contract = build_form_contract(current)
    _write_csv(FORM_ORDER_PATH, contract)
    return contract


def _update_exclusion_register(contract: pd.DataFrame) -> pd.DataFrame:
    path = REPO / "data" / "post_extraction_exclusions.csv"
    current = pd.read_csv(path)
    for column in ("DOI", "Source_Form_Paper_ID"):
        if column not in current:
            current[column] = ""
    current = current[["Title", "DOI", "Source_Form_Paper_ID", "Exclusion_Category", "Reason"]]
    current["Exclusion_Category"] = current["Exclusion_Category"].map(_normalize_exclusion_category)
    known = {normalize_doi(value) for value in current["DOI"] if normalize_doi(value)}
    additions = []
    for row in contract.itertuples(index=False):
        if _as_bool(row.Include_In_Final_Corpus):
            continue
        doi = normalize_doi(row.DOI)
        if doi in known:
            continue
        additions.append(
            {
                "Title": row.Title,
                "DOI": row.DOI,
                "Source_Form_Paper_ID": int(row.Form_Paper_ID),
                "Exclusion_Category": row.Exclusion_Category,
                "Reason": row.Exclusion_Reason,
            }
        )
    return pd.concat([current, pd.DataFrame(additions)], ignore_index=True)


def finalize() -> dict[str, object]:
    contract = _load_or_create_form_contract()
    data_dir = REPO / "data"
    study_files = [
        data_dir / "data-clean.csv",
        data_dir / "field_characterization_evidence.csv",
        data_dir / "dataset_characterization_evidence.csv",
        data_dir / "tr_criteria_evidence.csv",
    ]
    primary_scope_evidence = data_dir / "primary_sr_scope_evidence.csv"
    if primary_scope_evidence.exists():
        study_files.append(primary_scope_evidence)
    remapped = {
        path: remap_study_table(pd.read_csv(path), contract)
        for path in study_files
    }
    active = contract.loc[contract["Include_In_Final_Corpus"].map(_as_bool)].copy()
    active["Paper_ID"] = pd.to_numeric(active["Final_Paper_ID"], errors="raise").astype(int)
    final_order = active[["Paper_ID", "Title", "DOI"]].reset_index(drop=True)
    exclusions = _update_exclusion_register(contract)

    # All source/contract validation is complete before any canonical files are replaced.
    _write_csv(FORM_ORDER_PATH, contract)
    for path, frame in remapped.items():
        _write_csv(path, frame)
    _write_csv(FINAL_ORDER_PATH, final_order)
    _write_csv(data_dir / "post_extraction_exclusions.csv", exclusions)
    return {
        "scoring_form_studies": int(len(contract)),
        "final_included_studies": int(len(final_order)),
        "post_extraction_exclusions": int(len(exclusions)),
        "new_exclusions": int(len(contract) - len(final_order)),
        "outputs": [str(path.relative_to(REPO)) for path in [FORM_ORDER_PATH, *study_files, FINAL_ORDER_PATH, data_dir / "post_extraction_exclusions.csv"]],
        "private_reviewer_ratings_modified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(finalize(), indent=2))


if __name__ == "__main__":
    main()
