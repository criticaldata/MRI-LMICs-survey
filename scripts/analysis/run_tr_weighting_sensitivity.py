"""Sensitivity analysis for alternative Translational Readiness (TR) weights.

The manuscript's equal-weight TR score is the primary definition. This script
tests whether descriptive conclusions and the exploratory LMIC--TR association
materially change under pre-specified alternative weight sets. Scores are
rescaled to 0--5 for comparability; no scheme is selected because it produces
the most favourable result.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from review_metrics import PROJECT_ROOT, build_analysis, load_data, spearman_permutation


OUTPUT = PROJECT_ROOT / "analysis" / "review_20260803" / "tr_weighting_sensitivity_20260804"
PROMOTED = PROJECT_ROOT / "tables" / "analysis_tr_weighting_sensitivity.csv"
CRITERIA = [
    "TR_LowFieldDomain",
    "TR_OpenScience",
    "TR_ClinicalEvaluation",
    "TR_HardwareAwareness",
    "TR_DataDiversity",
]
SCHEMES = {
    "Equal weights (primary)": [1, 1, 1, 1, 1],
    "Clinical evaluation emphasis": [1, 1, 2, 1, 1],
    "Low-resource deployment emphasis": [2, 1, 1, 2, 2],
    "Evidence and deployment emphasis": [2, 2, 2, 1, 2],
}
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 42


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bootstrap_spearman_ci(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """Return a percentile bootstrap CI without selecting a favourable scheme."""
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rho_values = []
    for _ in range(BOOTSTRAP_REPLICATES):
        indices = rng.integers(0, len(x_values), size=len(x_values))
        rho = spearmanr(x_values[indices], y_values[indices]).statistic
        if np.isfinite(rho):
            rho_values.append(float(rho))
    if not rho_values:
        return float("nan"), float("nan")
    return tuple(float(value) for value in np.percentile(rho_values, [2.5, 97.5]))


def primary_leave_one_out(x: pd.Series, y: pd.Series, paper_ids: pd.Series) -> pd.DataFrame:
    """Assess whether the primary equal-weight association is single-study driven."""
    rows = []
    for index, paper_id in enumerate(paper_ids):
        mask = np.ones(len(x), dtype=bool)
        mask[index] = False
        rho = spearmanr(np.asarray(x)[mask], np.asarray(y)[mask]).statistic
        rows.append({"Omitted_Paper_ID": int(paper_id), "N": int(mask.sum()), "LMIC_TR_Spearman_Rho": float(rho)})
    return pd.DataFrame(rows).sort_values("Omitted_Paper_ID")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = PROJECT_ROOT / "data" / "data-clean.csv"
    derived = build_analysis(load_data(source))["derived"].copy()
    primary = derived[CRITERIA].sum(axis=1).astype(float)
    study = derived[["Paper_ID", "Title", "LMIC_Score", *CRITERIA]].copy()
    summary_rows = []
    primary_influence = primary_leave_one_out(derived["LMIC_Score"], primary, derived["Paper_ID"])
    for name, weights in SCHEMES.items():
        raw = derived[CRITERIA].mul(weights, axis=1).sum(axis=1).astype(float)
        score = raw / sum(weights) * 5.0
        column = "TR_" + "_".join(word.replace("-", "") for word in name.replace("(", "").replace(")", "").split())
        study[column] = score
        corr = spearman_permutation(derived["LMIC_Score"], score, permutations=10000, seed=42)
        bootstrap_low, bootstrap_high = bootstrap_spearman_ci(derived["LMIC_Score"], score)
        rank_rho = float(primary.rank(method="average").corr(score.rank(method="average")))
        summary_rows.append({
            "Scheme": name,
            "Weights": "; ".join(f"{criterion.replace('TR_', '')}={weight}" for criterion, weight in zip(CRITERIA, weights)),
            "N": int(len(score)),
            "Mean_TR_0_to_5": float(score.mean()),
            "Median_TR_0_to_5": float(score.median()),
            "Min_TR_0_to_5": float(score.min()),
            "Max_TR_0_to_5": float(score.max()),
            "Rank_Spearman_vs_Primary_Equal": rank_rho,
            "LMIC_TR_Spearman_Rho": corr["rho"],
            "LMIC_TR_Permutation_P": corr["p_permutation"],
            "LMIC_TR_Bootstrap_CI_2_5": bootstrap_low,
            "LMIC_TR_Bootstrap_CI_97_5": bootstrap_high,
            "Bootstrap_Replicates": BOOTSTRAP_REPLICATES,
            "Bootstrap_Seed": BOOTSTRAP_SEED,
            "Permutations": corr["permutations"],
            "Seed": corr["seed"],
        })
    summary = pd.DataFrame(summary_rows)
    study.to_csv(OUTPUT / "tr_weighting_study_scores.csv", index=False, encoding="utf-8")
    summary.to_csv(OUTPUT / "analysis_tr_weighting_sensitivity.csv", index=False, encoding="utf-8")
    primary_influence.to_csv(OUTPUT / "analysis_tr_primary_leave_one_out.csv", index=False, encoding="utf-8")
    summary.to_csv(PROMOTED, index=False, encoding="utf-8")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Reviewer-requested sensitivity analysis of alternative TR weighting schemes.",
        "primary_definition": "Equal weights across the five revised manuscript TR criteria.",
        "criteria": CRITERIA,
        "schemes": SCHEMES,
        "score_rescaling": "weighted sum divided by sum of weights and multiplied by 5",
        "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": BOOTSTRAP_SEED, "interval": "percentile 95% CI for Spearman rho"},
        "influence_analysis": "leave-one-out Spearman rho for the primary equal-weight score",
        "source": str(source),
        "source_sha256": sha256(source),
        "outputs": {
            "summary": str(OUTPUT / "analysis_tr_weighting_sensitivity.csv"),
            "study_scores": str(OUTPUT / "tr_weighting_study_scores.csv"),
            "primary_leave_one_out": str(OUTPUT / "analysis_tr_primary_leave_one_out.csv"),
            "promoted_summary": str(PROMOTED),
        },
        "interpretation": "Exploratory robustness analysis; rank stability, bootstrap uncertainty, and leave-one-out influence are reported without selecting a preferred alternative scheme.",
    }
    (OUTPUT / "tr_weighting_sensitivity_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
