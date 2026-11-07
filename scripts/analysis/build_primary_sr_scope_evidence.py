"""Build the reproducible study-level scope map for the SR-primary sensitivity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "figures"))
from mapper import load_data, normalize_primary_focus  # noqa: E402


OUTPUT = REPO / "data" / "primary_sr_scope_evidence.csv"
SPATIAL_SR_FOCI = {"Pure SR", "SR + Denoising", "SR + Other"}
PURE_OR_DENOISING_FOCI = {"Pure SR", "SR + Denoising"}

# These two records were labelled as combined denoising/SR in the extraction,
# but their full text does not describe a lower-resolution input mapped to a
# higher-spatial-resolution output. They remain eligible in the broad corpus.
NON_SPATIAL_ENHANCEMENT = {
    "10.1016/j.mri.2021.10.038": (
        "Deep-learning MR reconstruction and reader-based enhancement are evaluated; "
        "the article does not report a low-to-high spatial-resolution mapping.",
        "Abstract and Methods",
    ),
    "10.1109/ist50367.2021.9651441": (
        "Low-field denoising and artifact correction are described, without a reported "
        "spatial-upsampling task or higher-resolution output.",
        "Abstract and Methods",
    ),
}


def build_scope_table(data: pd.DataFrame | None = None) -> pd.DataFrame:
    source = load_data() if data is None else data.copy()
    rows: list[dict[str, object]] = []
    for record in source.itertuples(index=False):
        doi = str(record.DOI).strip().casefold()
        raw_focus = str(record.Primary_Focus)
        normalized = normalize_primary_focus(raw_focus)
        exception = NON_SPATIAL_ENHANCEMENT.get(doi)
        corrected = "Other" if exception else normalized
        include_strict = corrected in SPATIAL_SR_FOCI
        include_pure = corrected in PURE_OR_DENOISING_FOCI
        if exception:
            rationale, evidence_section = exception
            basis = "Full-text scope correction"
        elif include_strict:
            rationale = (
                f"The extracted primary-focus category is {normalized}; included in the "
                "SR-primary sensitivity cohort under the stated category rule."
            )
            evidence_section = "Primary_Focus extraction field"
            basis = "Structured study-characteristics field"
        else:
            rationale = (
                f"The extracted primary-focus category is {normalized}; the study remains "
                "in the broad MRI corpus but is outside the SR-primary sensitivity cohort."
            )
            evidence_section = "Primary_Focus extraction field"
            basis = "Structured study-characteristics field"
        rows.append(
            {
                "Paper_ID": int(record.Paper_ID),
                "DOI": doi,
                "Title": str(record.Title),
                "Primary_Focus_Source": raw_focus,
                "Primary_Focus_Corrected": corrected,
                "Primary_SR_Sensitivity_Eligible": "Yes" if include_strict else "No",
                "Pure_or_Denoising_SR_Eligible": "Yes" if include_pure else "No",
                "Classification_Basis": basis,
                "Evidence_Section": evidence_section,
                "Scope_Rationale": rationale,
            }
        )
    result = pd.DataFrame(rows)
    if result["Paper_ID"].tolist() != list(range(1, len(result) + 1)):
        raise ValueError("Scope evidence must follow the contiguous final corpus order")
    if result["DOI"].duplicated().any() or result["Title"].duplicated().any():
        raise ValueError("Scope evidence DOI and title identities must be unique")
    return result


def main() -> None:
    table = build_scope_table()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUTPUT, index=False, encoding="utf-8", lineterminator="\n")
    strict = int(table["Primary_SR_Sensitivity_Eligible"].eq("Yes").sum())
    pure = int(table["Pure_or_Denoising_SR_Eligible"].eq("Yes").sum())
    print(
        json.dumps(
            {
                "included_studies": len(table),
                "sr_primary_sensitivity_n": strict,
                "pure_or_denoising_sr_n": pure,
                "full_text_scope_corrections": len(NON_SPATIAL_ENHANCEMENT),
                "output": str(OUTPUT.relative_to(REPO)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
