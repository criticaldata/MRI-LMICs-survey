"""Promote current, reproducible statistical outputs to compact tables.

All files written here are aggregate only. Random-forest importances come from
repeated held-out permutations; reviewer agreement is read from the public
aggregate summaries generated from the private workbook.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_required(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required current analysis output is missing: {path}")
    return pd.read_csv(path)


def create_table5() -> None:
    tables = PROJECT_ROOT / "tables"
    rf_dir = PROJECT_ROOT / "analysis" / "review_20260803" / "random_forest_robustness_20260804"

    importance = _read_required(rf_dir / "rf_heldout_permutation_summary.csv")
    importance = importance.sort_values(
        "Permutation_MAE_Increase_Mean", ascending=False
    ).reset_index(drop=True)
    importance.to_csv(tables / "table5a_random_forest_features.csv", index=False)

    mann_whitney = _read_required(tables / "module2_mann_whitney_results.csv")
    chi_square = _read_required(tables / "module2_chi_square_results.csv")
    pd.concat([mann_whitney, chi_square], ignore_index=True, sort=False).to_csv(
        tables / "table5b_mann_whitney_results.csv", index=False
    )

    fleiss = _read_required(tables / "analysis_fleiss_kappa_summary.csv")
    weighted = _read_required(tables / "analysis_weighted_kappa_summary.csv")
    icc = _read_required(tables / "analysis_icc_summary.csv")
    weighted_wide = weighted.pivot(
        index="Analysis", columns="Weighting", values="Weighted_Fleiss_kappa"
    ).rename(columns={"linear": "Weighted_Fleiss_Kappa_Linear", "quadratic": "Weighted_Fleiss_Kappa_Quadratic"})
    agreement = (
        fleiss[["Analysis", "Fleiss_kappa", "Items", "Raters"]]
        .merge(weighted_wide, on="Analysis", validate="one_to_one")
        .merge(
            icc[["Analysis", "ICC_2_1_absolute_agreement", "ICC_2_k_absolute_agreement"]],
            on="Analysis",
            validate="one_to_one",
        )
    )
    agreement.to_csv(tables / "table5c_reviewer_agreement_aggregate.csv", index=False)

    print("Current aggregate statistical tables written.")
    print(f"Random-forest permutation features: {len(importance)}")
    print(f"Mann-Whitney / chi-square rows: {len(mann_whitney) + len(chi_square)}")
    print(f"Reviewer-agreement scales: {len(agreement)}")


if __name__ == "__main__":
    create_table5()
