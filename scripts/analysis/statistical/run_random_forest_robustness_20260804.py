"""Robust supplementary analysis for the MRI-LMICs Random Forest model.

This script does not optimize a result on the same 48 studies. It uses a
pre-specified constrained forest, repeated out-of-sample validation, a mean
baseline, and a regularized ordinal-logistic benchmark. Feature uncertainty is
reported with bootstrap percentile intervals and held-out permutation scores.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import mord
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.optimize import OptimizeWarning
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from run_random_forest_reanalysis_20260804 import (
    FEATURES,
    LMIC_SCORE_MAP,
    architecture,
    clinical_validation,
    code_available,
    dataset_type,
    field_type,
    low_field_mentioned,
    psnr_reported,
)


REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "data" / "data-clean.csv"
OUTPUT = REPO / "analysis" / "review_20260803" / "random_forest_robustness_20260804"
SEED = 42
SPLITS = 5
REPEATS = 10
BOOTSTRAPS = 200


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_input() -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame]:
    df = pd.read_csv(SOURCE, encoding="utf-8-sig").dropna(subset=["Title"]).copy()
    df = df[df["Title"].astype(str).str.strip().ne("")].copy()
    df["LMIC_Score_Numeric"] = pd.to_numeric(
        df["LMIC_Relevance_Score"].astype(str).map(LMIC_SCORE_MAP).fillna(df["LMIC_Relevance_Score"]),
        errors="coerce",
    )
    df = df[df["LMIC_Score_Numeric"].between(1, 5)].copy()
    x = pd.DataFrame(index=df.index)
    arch = df["AI_Architecture"].map(architecture)
    x["Is_CNN"] = (arch == "CNN").astype(int)
    x["Is_GAN"] = (arch == "GAN").astype(int)
    x["Is_UNet"] = (arch == "U-Net").astype(int)
    x["Is_Transformer"] = (arch == "Transformer").astype(int)
    x["Is_Clinical_Data"] = (df["Dataset_Type"].map(dataset_type) == "Clinical").astype(int)
    x["Code_Available"] = df["Code_Available"].map(code_available)
    fields = df["Field_Strength_Type"].map(field_type)
    x["Is_LowField_Hardware"] = fields.isin(["Low_Field", "Mixed"]).astype(int)
    x["Low_Field_Mentioned"] = df["Low_Field_Mentioned"].map(low_field_mentioned)
    x["Has_Clinical_Validation"] = df["Clinical_Validation_Type"].map(clinical_validation)
    x["Has_PSNR"] = df["PSNR_Value"].map(psnr_reported)
    identifiers = df[["Paper_ID", "Title", "LMIC_Score_Numeric"]].reset_index(drop=True)
    return x.reset_index(drop=True), df["LMIC_Score_Numeric"].to_numpy(dtype=float), identifiers


def constrained_forest() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=400,
        max_depth=3,
        min_samples_split=6,
        min_samples_leaf=4,
        max_features=0.7,
        random_state=SEED,
        n_jobs=-1,
    )


def ordinal_model() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("ordinal", mord.LogisticIT(alpha=1.0)),
    ])


def fit_ordinal_model(features: pd.DataFrame, target: np.ndarray) -> Pipeline:
    """Fit the ordinal benchmark while suppressing mord's known SciPy option warning."""
    model = ordinal_model()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Unknown solver options: disp",
            category=OptimizeWarning,
            module=r"mord\.threshold_based",
        )
        model.fit(features, target.astype(int))
    return model


def ridge_model() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("ridge", Ridge(alpha=10.0)),
    ])


def evaluate(x: pd.DataFrame, y: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    splitter = RepeatedKFold(n_splits=SPLITS, n_repeats=REPEATS, random_state=SEED)
    specs = {
        "Mean baseline": DummyRegressor(strategy="mean"),
        "Constrained Random Forest": constrained_forest(),
        "Regularized ordinal logistic": ordinal_model(),
        "Regularized ridge benchmark": ridge_model(),
    }
    scores = []
    permutation_rows = []
    for split_number, (train_idx, test_idx) in enumerate(splitter.split(x), start=1):
        x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        for name, estimator in specs.items():
            if name == "Regularized ordinal logistic":
                estimator = fit_ordinal_model(x_train, y_train)
            else:
                estimator.fit(x_train, y_train)
            prediction = np.asarray(estimator.predict(x_test), dtype=float)
            scores.append({
                "Split": split_number,
                "Model": name,
                "MAE": float(mean_absolute_error(y_test, prediction)),
                "R2": float(r2_score(y_test, prediction)),
                "N_Train": int(len(train_idx)),
                "N_Test": int(len(test_idx)),
            })
        forest = constrained_forest().fit(x_train, y_train)
        perm = permutation_importance(
            forest,
            x_test,
            y_test,
            scoring="neg_mean_absolute_error",
            n_repeats=10,
            random_state=SEED + split_number,
            n_jobs=-1,
        )
        for feature, value in zip(FEATURES, perm.importances_mean):
            permutation_rows.append({"Split": split_number, "Feature": feature, "MAE_Increase_On_Permutation": float(value)})
    return pd.DataFrame(scores), pd.DataFrame(permutation_rows)


def bootstrap_importance(x: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    values = []
    for iteration in range(BOOTSTRAPS):
        indices = rng.integers(0, len(x), size=len(x))
        model = constrained_forest()
        model.set_params(random_state=SEED + iteration)
        model.fit(x.iloc[indices], y[indices])
        values.append(model.feature_importances_)
    frame = pd.DataFrame(values, columns=FEATURES)
    return pd.DataFrame({
        "Feature": FEATURES,
        "Bootstrap_Mean_Importance": frame.mean().to_numpy(),
        "Bootstrap_CI_2_5": frame.quantile(0.025).to_numpy(),
        "Bootstrap_CI_97_5": frame.quantile(0.975).to_numpy(),
        "Bootstrap_Replicates": BOOTSTRAPS,
    }).sort_values("Bootstrap_Mean_Importance", ascending=False, kind="stable").reset_index(drop=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    x, y, identifiers = make_input()
    split_scores, permutation = evaluate(x, y)
    bootstrap = bootstrap_importance(x, y)
    summary = (
        split_scores.groupby("Model", as_index=False)
        .agg(MAE_Mean=("MAE", "mean"), MAE_SD=("MAE", "std"), R2_Mean=("R2", "mean"), R2_SD=("R2", "std"), Splits=("Split", "count"))
        .sort_values("MAE_Mean", kind="stable")
    )
    baseline_mae = split_scores.loc[split_scores["Model"] == "Mean baseline", ["Split", "MAE"]].rename(columns={"MAE": "Baseline_MAE"})
    forest_mae = split_scores.loc[split_scores["Model"] == "Constrained Random Forest", ["Split", "MAE"]].rename(columns={"MAE": "Forest_MAE"})
    paired = baseline_mae.merge(forest_mae, on="Split", validate="one_to_one")
    forest_delta = {
        "Measure": "Constrained RF MAE improvement versus mean baseline",
        "Mean_Improvement": float((paired["Baseline_MAE"] - paired["Forest_MAE"]).mean()),
        "Median_Improvement": float((paired["Baseline_MAE"] - paired["Forest_MAE"]).median()),
        "Positive_Splits": int((paired["Baseline_MAE"] > paired["Forest_MAE"]).sum()),
        "Total_Splits": int(len(paired)),
    }
    permutation_summary = (
        permutation.groupby("Feature", as_index=False)
        .agg(Permutation_MAE_Increase_Mean=("MAE_Increase_On_Permutation", "mean"), Permutation_MAE_Increase_SD=("MAE_Increase_On_Permutation", "std"), Splits=("Split", "count"))
        .sort_values("Permutation_MAE_Increase_Mean", ascending=False, kind="stable")
    )
    apparent = constrained_forest().fit(x, y)
    apparent_r2 = float(apparent.score(x, y))

    identifiers.to_csv(OUTPUT / "rf_robustness_model_input.csv", index=False, encoding="utf-8")
    split_scores.to_csv(OUTPUT / "rf_repeated_cv_scores.csv", index=False, encoding="utf-8")
    summary.to_csv(OUTPUT / "rf_repeated_cv_summary.csv", index=False, encoding="utf-8")
    pd.DataFrame([forest_delta]).to_csv(OUTPUT / "rf_vs_baseline.csv", index=False, encoding="utf-8")
    permutation.to_csv(OUTPUT / "rf_heldout_permutation_splits.csv", index=False, encoding="utf-8")
    permutation_summary.to_csv(OUTPUT / "rf_heldout_permutation_summary.csv", index=False, encoding="utf-8")
    bootstrap.to_csv(OUTPUT / "rf_bootstrap_importance_ci.csv", index=False, encoding="utf-8")
    lock = subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, capture_output=True, text=True)
    (OUTPUT / "requirements-lock.txt").write_text(lock.stdout, encoding="utf-8")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Supplementary robustness analysis. Does not support causal interpretation or model deployment.",
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "n_studies": int(len(x)),
        "features": FEATURES,
        "validation": {"scheme": "RepeatedKFold", "splits": SPLITS, "repeats": REPEATS, "total_holdout_splits": SPLITS * REPEATS, "seed": SEED},
        "constrained_forest": {"n_estimators": 400, "max_depth": 3, "min_samples_split": 6, "min_samples_leaf": 4, "max_features": 0.7},
        "bootstrap": {"replicates": BOOTSTRAPS, "seed": SEED},
        "apparent_train_r2_constrained_forest": apparent_r2,
        "software": {"python": sys.version, "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "mord": mord.__version__},
        "outputs": {path.name: sha256(path) for path in OUTPUT.iterdir() if path.is_file() and path.name != "rf_robustness_manifest.json"},
    }
    (OUTPUT / "rf_robustness_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary.to_dict(orient="records"), "forest_baseline_comparison": forest_delta, "apparent_train_r2": apparent_r2, "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
