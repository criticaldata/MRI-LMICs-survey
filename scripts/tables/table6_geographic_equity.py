"""Generate aggregate geography summaries from publication-affiliation evidence.

Use the multi-source, affiliation-based country resolution in the scientometric
export. Do not fall back to the earlier OpenAlex-only group field: it labels
resolvable affiliations as UNKNOWN. Unresolved or multi-country income groups
remain "Not available" rather than being imputed.
"""

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "figures"))
from mapper import get_project_root, load_data


def create_table6() -> None:
    root = get_project_root()
    tables = root / "tables"
    data = load_data()
    scientometric = pd.read_csv(tables / "mri_scientometric_results.csv", dtype=str)
    if len(data) != 45 or len(scientometric) != 45:
        raise ValueError("Geographic summaries require the final 45-study corpus")
    if not data["Title"].astype(str).tolist() == scientometric["Title"].astype(str).tolist():
        raise ValueError("Scientometric rows do not match the canonical study order")

    group_column = "Suggested_First_WB_Group"
    if group_column not in scientometric.columns:
        raise ValueError(f"Scientometric export is missing {group_column}")
    groups = scientometric[group_column].fillna("Not available").replace(
        {"": "Not available", "UNKNOWN": "Not available"}
    )
    allowed_groups = {"HIC", "UMC", "LMC", "Not available"}
    unexpected_groups = set(groups) - allowed_groups
    if unexpected_groups:
        raise ValueError(f"Unexpected first-author income groups: {sorted(unexpected_groups)}")
    income = groups.value_counts(dropna=False).rename_axis("First_Author_WB_Group").reset_index(name="Studies")
    income = income.set_index("First_Author_WB_Group").reindex(
        ["HIC", "UMC", "LMC", "Not available"], fill_value=0
    ).rename_axis("First_Author_WB_Group").reset_index()
    income["Percentage"] = (income["Studies"] / len(scientometric) * 100).round(1)
    income.to_csv(tables / "table6a_income_distribution.csv", index=False)

    by_application = data.groupby("Application_Norm", dropna=False)["LMIC_Score"].agg(
        Studies="count", Mean="mean", Median="median", SD="std"
    ).round(2).reset_index()
    by_application.to_csv(tables / "table6b_lmic_by_application.csv", index=False)

    field = data["Field_Strength_Type"].fillna("").astype(str).str.casefold()
    high_relevance = pd.to_numeric(data["LMIC_Score"], errors="coerce").ge(4)
    summary = pd.DataFrame(
        [
            {"Measure": "Included studies", "N": len(data)},
            {"Measure": "First-author income group not available", "N": int(groups.eq("Not available").sum())},
            {"Measure": "LMIC Relevance Score 4-5", "N": int(high_relevance.sum())},
            {"Measure": "Low-field MRI recorded in extraction", "N": int(field.str.contains("low", regex=False).sum())},
        ]
    )
    summary.to_csv(tables / "table6c_geographic_summary.csv", index=False)

    print("Aggregate geographic tables written from the final 45-study export.")
    print(income.to_string(index=False))


if __name__ == "__main__":
    create_table6()
