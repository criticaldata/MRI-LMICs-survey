"""Metric-aware fallback parsing and validated, DOI-keyed result selection."""

from pathlib import Path
import re

import numpy as np
import pandas as pd


def normalize_doi(value):
    """Normalize DOI case and common resolver prefixes, not study row numbers."""
    if pd.isna(value):
        return ""
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "",
                  str(value).strip(), flags=re.IGNORECASE).strip().casefold()


def parse_metric_value(value, metric=None):
    """Legacy first-plausible-value fallback, excluding percentage labels.

    This does not infer proposed models or choose between experiments. Those
    decisions require keyed source evidence, not prose order or maximization.
    """
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text.casefold().startswith(("not reported", "n/a", "reported",
                                   "not explicitly reported", "uses", "paper uses")):
        return np.nan
    # Remove complete labels first; otherwise '20%' can become PSNR=20.
    text = re.sub(r"(?:\d+(?:\.\d+)?|\.\d+)\s*(?:%|percent\b)", " ",
                  text, flags=re.IGNORECASE)
    for match in re.finditer(r"(?<![\w.])(?:\d+\.\d+|\.\d+|\d+)(?!\w|\.\d)", text):
        number = float(match.group())
        plausible = (0 <= number <= 1) if metric == "SSIM" else (10 <= number <= 80)
        if metric is None:
            plausible = 10 <= number <= 80 or 0.4 <= number <= 1
        if plausible:
            return number
    return np.nan


def load_metric_evidence(path=None):
    """Read frozen conditions; reject ambiguous primary choices or bad values."""
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "performance_metric_evidence.csv"
    evidence = pd.read_csv(path)
    required = {
        "DOI", "Paper_ID", "Title", "Metric", "Model", "Dataset", "Condition",
        "Value", "Unit", "Is_Primary", "Result_Role", "Evidence_Status",
        "PDF_Page", "Source_Location", "Source_File", "Selection_Rule",
    }
    missing = required.difference(evidence.columns)
    if missing:
        raise ValueError("Metric evidence missing columns: " + ", ".join(sorted(missing)))
    if evidence.empty:
        raise ValueError("Metric evidence must not be empty")
    for column in required - {"Value"}:
        if evidence[column].isna().any() or evidence[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Metric evidence has empty {column}")
    evidence = evidence.copy()
    evidence["DOI"] = evidence["DOI"].map(normalize_doi)
    if not evidence["DOI"].str.match(r"^10\.\d{4,9}/\S+$").all():
        raise ValueError("Metric evidence contains invalid DOI")
    primary = evidence["Is_Primary"].astype(str).str.casefold()
    if not primary.isin(["true", "false"]).all():
        raise ValueError("Metric evidence Is_Primary must be true or false")
    evidence["Is_Primary"] = primary.eq("true")
    if not evidence["Metric"].isin(["PSNR", "SSIM"]).all():
        raise ValueError("Metric evidence contains unsupported metric")
    if not evidence["Result_Role"].eq("proposed_main").all():
        raise ValueError("Metric evidence must select proposed_main results, not baselines or ablations")
    if not evidence["Evidence_Status"].isin(["reported", "not_reported"]).all():
        raise ValueError("Metric evidence contains unsupported evidence status")
    for metric, unit in (("PSNR", "dB"), ("SSIM", "unitless")):
        if not evidence.loc[evidence["Metric"].eq(metric), "Unit"].eq(unit).all():
            raise ValueError(f"Metric evidence has wrong unit for {metric}")
    evidence["Value"] = pd.to_numeric(evidence["Value"], errors="raise")
    reported = evidence["Evidence_Status"].eq("reported")
    if evidence.loc[reported, "Value"].isna().any() or evidence.loc[~reported, "Value"].notna().any():
        raise ValueError("Metric evidence value conflicts with reported status")
    values = evidence.loc[reported, "Value"]
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Metric evidence has non-finite or negative value")
    if (evidence.loc[evidence["Metric"].eq("SSIM"), "Value"].dropna() > 1).any():
        raise ValueError("Metric evidence SSIM must be in [0, 1]")
    if evidence.duplicated(["DOI", "Metric", "Dataset", "Model", "Condition"]).any():
        raise ValueError("Metric evidence contains duplicate condition keys")
    if not evidence.groupby(["DOI", "Metric"])["Is_Primary"].sum().eq(1).all():
        raise ValueError("Metric evidence requires exactly one primary per DOI and metric")
    return evidence


def apply_metric_evidence(frame, evidence_path=None):
    """Add numeric metrics and provenance without changing raw extraction text.

    Unreviewed studies retain explicitly labelled fallback scalars. Evidence
    minima/maxima describe retained conditions, not confidence intervals.
    """
    evidence = load_metric_evidence(evidence_path)
    result = frame.copy()
    dois = result["DOI"].map(normalize_doi)
    for metric in ("PSNR", "SSIM"):
        result[f"{metric}_Numeric"] = result[f"{metric}_Value"].map(
            lambda value: parse_metric_value(value, metric)
        )
        result[f"{metric}_Selection_Method"] = "free_text_fallback"
        result[f"{metric}_Selection_Rule"] = (
            "Unverified first plausible metric value excluding percentages; not a model-selection rule"
        )
        for suffix in ("Primary_Condition", "Dataset", "Model", "Evidence_Source"):
            result[f"{metric}_{suffix}"] = ""
        for suffix in ("Evidence_Min", "Evidence_Max"):
            result[f"{metric}_{suffix}"] = np.nan
    for (doi, metric), conditions in evidence.groupby(["DOI", "Metric"], sort=False):
        mask = dois.eq(doi)
        if not mask.any():
            continue
        primary = conditions.loc[conditions["Is_Primary"]].iloc[0]
        updates = {
            "Numeric": primary["Value"],
            "Selection_Method": "doi_keyed_evidence",
            "Selection_Rule": primary["Selection_Rule"],
            "Primary_Condition": primary["Condition"],
            "Dataset": primary["Dataset"],
            "Model": primary["Model"],
            "Evidence_Source": f'{primary["Source_Location"]}; PDF p{primary["PDF_Page"]}',
            "Evidence_Min": conditions["Value"].min(),
            "Evidence_Max": conditions["Value"].max(),
        }
        for suffix, value in updates.items():
            result.loc[mask, f"{metric}_{suffix}"] = value
    return result
