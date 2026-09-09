"""Run a reproducible, isolated Random Forest reanalysis of the current 48-study corpus.

This is a secondary exploratory analysis reconstructed from the legacy
``REVIEWER SECTION`` Random Forest logic.  It deliberately writes to a dated
subdirectory and does not overwrite the legacy 65-row/43-study artifacts.
It is not the Spearman LMIC--TR analysis requested by the current reviewers.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict


REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "data" / "data-clean.csv"
OUTPUT = REPO / "analysis" / "review_20260803" / "random_forest_reanalysis_20260804"
RANDOM_SEED = 42
FEATURES = [
    "Is_CNN",
    "Is_GAN",
    "Is_UNet",
    "Is_Transformer",
    "Is_Clinical_Data",
    "Code_Available",
    "Is_LowField_Hardware",
    "Low_Field_Mentioned",
    "Has_Clinical_Validation",
    "Has_PSNR",
]
PRIVATE_OR_NONANALYTIC_SOURCE_COLUMNS = {
    "Assigned_Reviewer",
    "Reviewer_Name",
    "Notes_Questions",
}
LMIC_SCORE_MAP = {
    "1.0": 1, "2.0": 2, "3.0": 3, "4.0": 4, "5.0": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "High": 4, "Medium": 3, "Moderate": 3, "medium": 3,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def architecture(value: object) -> str:
    value = text(value).lower()
    if "gan" in value:
        return "GAN"
    if "transformer" in value:
        return "Transformer"
    if "u-net" in value or "unet" in value:
        return "U-Net"
    if "cnn" in value or "srcnn" in value or "srdensenet" in value:
        return "CNN"
    return "Other"


def dataset_type(value: object) -> str:
    value = text(value).lower()
    if "clinical" in value:
        return "Clinical"
    return "Other"


def field_type(value: object) -> str:
    value = text(value).lower()
    if "low" in value:
        return "Low_Field"
    if "mixed" in value:
        return "Mixed"
    return "Other"


def code_available(value: object) -> int:
    return int(text(value).casefold() in {"yes", "true", "1", "upon_request"})


def low_field_mentioned(value: object) -> int:
    return int(text(value).casefold() in {"yes", "true", "1"})


def clinical_validation(value: object) -> int:
    return int(text(value).casefold() not in {"", "none", "n/a", "na", "not reported"})


def psnr_reported(value: object) -> int:
    return int(text(value).casefold() not in {"", "none", "n/a", "na", "not reported", "not reported."})


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SOURCE, encoding="utf-8-sig")
    initial_rows = len(df)
    df = df.dropna(subset=["Title"]).copy()
    df = df[df["Title"].astype(str).str.strip().ne("")].copy()
    df["LMIC_Relevance_Score_Numeric"] = pd.to_numeric(
        df["LMIC_Relevance_Score"].astype(str).map(LMIC_SCORE_MAP).fillna(df["LMIC_Relevance_Score"]),
        errors="coerce",
    )
    df = df[df["LMIC_Relevance_Score_Numeric"].between(1, 5)].copy()

    model_input = pd.DataFrame(index=df.index)
    arch = df["AI_Architecture"].map(architecture)
    model_input["Is_CNN"] = (arch == "CNN").astype(int)
    model_input["Is_GAN"] = (arch == "GAN").astype(int)
    model_input["Is_UNet"] = (arch == "U-Net").astype(int)
    model_input["Is_Transformer"] = (arch == "Transformer").astype(int)
    model_input["Is_Clinical_Data"] = (df["Dataset_Type"].map(dataset_type) == "Clinical").astype(int)
    model_input["Code_Available"] = df["Code_Available"].map(code_available)
    fields = df["Field_Strength_Type"].map(field_type)
    model_input["Is_LowField_Hardware"] = fields.isin(["Low_Field", "Mixed"]).astype(int)
    model_input["Low_Field_Mentioned"] = df["Low_Field_Mentioned"].map(low_field_mentioned)
    model_input["Has_Clinical_Validation"] = df["Clinical_Validation_Type"].map(clinical_validation)
    model_input["Has_PSNR"] = df["PSNR_Value"].map(psnr_reported)
    y = df["LMIC_Relevance_Score_Numeric"].to_numpy()

    model = RandomForestRegressor(
        n_estimators=500,
        max_depth=None,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    loo = LeaveOneOut()
    predictions = cross_val_predict(model, model_input, y, cv=loo)
    loo_absolute_errors = np.abs(y - predictions)
    model.fit(model_input, y)
    train_predictions = model.predict(model_input)

    metrics = {
        "Analysis": "Random Forest feature importance (exploratory; legacy logic reconstructed)",
        "Corpus": "Current canonical 48-study data-clean.csv",
        "Initial_Rows": initial_rows,
        "Included_Rows": int(len(df)),
        "Features": len(FEATURES),
        "Random_Seed": RANDOM_SEED,
        "Estimators": 500,
        "Min_Samples_Split": 3,
        "Min_Samples_Leaf": 2,
        "LOO_CV_MAE": float(loo_absolute_errors.mean()),
        "LOO_CV_MAE_STD": float(loo_absolute_errors.std()),
        "LOO_CV_R2": float(r2_score(y, predictions)),
        "Train_R2": float(r2_score(y, train_predictions)),
        "Train_MAE": float(mean_absolute_error(y, train_predictions)),
        "Train_RMSE": float(np.sqrt(mean_squared_error(y, train_predictions))),
    }
    importance = pd.DataFrame({"Feature": FEATURES, "Importance": model.feature_importances_})
    importance = importance.sort_values("Importance", ascending=False, kind="stable").reset_index(drop=True)
    importance.insert(0, "Rank", np.arange(1, len(importance) + 1))

    cleaned = df[["Paper_ID", "URL", "Title", "LMIC_Relevance_Score_Numeric"]].copy()
    cleaned = pd.concat([cleaned.reset_index(drop=True), model_input.reset_index(drop=True)], axis=1)
    extraction_columns = [
        column for column in df.columns
        if column not in PRIVATE_OR_NONANALYTIC_SOURCE_COLUMNS and column != "LMIC_Relevance_Score_Numeric"
    ]
    extraction = df[extraction_columns].copy().fillna("Not available")
    extraction = extraction.replace(r"^\s*$", "Not available", regex=True)
    pd.DataFrame([metrics]).to_csv(OUTPUT / "random_forest_metrics.csv", index=False, encoding="utf-8")
    importance.to_csv(OUTPUT / "random_forest_feature_importance.csv", index=False, encoding="utf-8")
    cleaned.to_csv(OUTPUT / "random_forest_model_input.csv", index=False, encoding="utf-8")
    extraction.to_csv(OUTPUT / "original_extraction_analysis_table.csv", index=False, encoding="utf-8")

    chart = importance.sort_values("Importance", ascending=True)
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.barh(chart["Feature"].str.replace("_", " "), chart["Importance"], color="#2F75B5")
    axis.set_xlabel("Feature importance (mean decrease in impurity)")
    axis.set_title(f"Exploratory Random Forest feature importance (n={len(df)})")
    for index, value in enumerate(chart["Importance"]):
        axis.text(value + 0.003, index, f"{value:.3f}", va="center", fontsize=9)
    axis.set_xlim(0, float(chart["Importance"].max()) * 1.18)
    figure.tight_layout()
    figure.savefig(OUTPUT / "random_forest_feature_importance.png", dpi=300)
    plt.close(figure)

    lock = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        check=True,
        capture_output=True,
        text=True,
    )
    (OUTPUT / "requirements-lock.txt").write_text(lock.stdout, encoding="utf-8")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Exploratory reconstruction of the legacy Random Forest analysis; not a current Reviewer 1/2 required analysis.",
        "source_file": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "row_count": int(len(df)),
        "feature_columns": FEATURES,
        "parameters": {key: metrics[key] for key in ["Random_Seed", "Estimators", "Min_Samples_Split", "Min_Samples_Leaf"]},
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "outputs": {
            path.name: sha256(path)
            for path in OUTPUT.iterdir()
            if path.is_file()
            and path.suffix.casefold() != ".xlsx"
            and path.name != "random_forest_reanalysis_manifest.json"
        },
        "known_difference_from_legacy": "Uses the current 48-study canonical corpus rather than the historical 65-row/43-study filtered file; rank is calculated after sorting.",
    }
    (OUTPUT / "random_forest_reanalysis_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(OUTPUT), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
