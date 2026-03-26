"""
Analysis: Edge Deployment Feasibility

For each paper, flags whether model size and/or inference time information
is reported and whether the reported values fall within the edge-deployment
thresholds proposed in Leo's comment:
  - Model size  < 100 MB (or < 0.1 GB)
  - Inference time < 5 seconds (or < 5000 ms) on CPU

Edge deployment candidates are papers that explicitly address resource
constraints (Resource_Constraints_Addressed == Yes) OR report values that
meet at least one of the above thresholds.
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
from mapper import load_data, get_project_root


# ---------------------------------------------------------------------------
# Helper: extract the first matching snippet (up to 200 chars) from a field
# ---------------------------------------------------------------------------

def _first_snippet(text, pattern, window=200):
    """Return the substring around the first match of *pattern* in *text*.

    Returns an empty string if no match is found.
    """
    if not isinstance(text, str):
        return ""
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if m is None:
        return ""
    start = max(0, m.start() - 40)
    end = min(len(text), start + window)
    return text[start:end].strip()


# ---------------------------------------------------------------------------
# Helper: test whether any numeric value near a unit satisfies a threshold
# ---------------------------------------------------------------------------

def _value_below_threshold(text, unit_pattern, threshold):
    """Return True if at least one numeric value adjacent to *unit_pattern*
    in *text* is <= *threshold*.

    Example:
        _value_below_threshold("model is 45 MB", r"MB", 100)  -> True
    """
    if not isinstance(text, str):
        return False
    # Match patterns like "45 MB", "0.045 GB", "45MB"
    full_pattern = r"(\d+(?:\.\d+)?)\s*" + unit_pattern
    for m in re.finditer(full_pattern, text, flags=re.IGNORECASE):
        try:
            val = float(m.group(1))
            if val <= threshold:
                return True
        except ValueError:
            pass
    return False


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

# Fields to search for model-size and inference-time mentions
_SEARCH_FIELDS = [
    "Architecture_Specifics",
    "Notes_Questions",
    "Performance_Summary",
    "Limitations_Mentioned",
]

# Keywords that indicate a model-size mention
_SIZE_PATTERN = r"MB|GB|\bparam(?:eter)?s?\b|million\s+param"

# Keywords that indicate an inference-time mention
_INFERENCE_PATTERN = r"inference|latency|\bms\b|millisecond|\bsecond[s]?\b|\bCPU\b|real.?time"

# Patterns used to extract numeric values for threshold checks
_MB_PATTERN = r"MB"
_GB_PATTERN = r"GB"
_SEC_PATTERN = r"s(?:ec(?:ond)?s?)?"     # matches s, sec, secs, second, seconds
_MS_PATTERN = r"ms|milliseconds?"

# Threshold values
_SIZE_THRESHOLD_MB = 100.0
_SIZE_THRESHOLD_GB = 0.1
_TIME_THRESHOLD_S = 5.0
_TIME_THRESHOLD_MS = 5000.0

# Patterns for "M parameters" style counts (treat 100 M params ~ small model)
_MPARAM_PATTERN = r"(\d+(?:\.\d+)?)\s*[Mm]\s*(?:param(?:eter)?s?|params?)"
_MPARAM_THRESHOLD = 10.0   # <= 10 M parameters considered small/edge-capable


def _combined_text(row):
    """Concatenate all search fields for a row into one string."""
    parts = []
    for col in _SEARCH_FIELDS:
        val = row.get(col, "")
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return " | ".join(parts)


def _meets_size_threshold(text):
    """True if text mentions a size value that meets the edge threshold."""
    if _value_below_threshold(text, _MB_PATTERN, _SIZE_THRESHOLD_MB):
        return True
    if _value_below_threshold(text, _GB_PATTERN, _SIZE_THRESHOLD_GB):
        return True
    # Check "M parameters" style
    for m in re.finditer(_MPARAM_PATTERN, text, flags=re.IGNORECASE):
        try:
            if float(m.group(1)) <= _MPARAM_THRESHOLD:
                return True
        except ValueError:
            pass
    return False


def _meets_inference_threshold(text):
    """True if text mentions an inference time that meets the edge threshold."""
    if _value_below_threshold(text, _SEC_PATTERN, _TIME_THRESHOLD_S):
        return True
    if _value_below_threshold(text, _MS_PATTERN, _TIME_THRESHOLD_MS):
        return True
    return False


def analyze_edge_deployment():
    df = load_data()

    results = []
    for _, row in df.iterrows():
        combined = _combined_text(row)

        mentions_size = bool(re.search(_SIZE_PATTERN, combined, flags=re.IGNORECASE))
        mentions_inference = bool(re.search(_INFERENCE_PATTERN, combined, flags=re.IGNORECASE))

        size_text = ""
        if mentions_size:
            size_text = _first_snippet(combined, _SIZE_PATTERN)

        inference_text = ""
        if mentions_inference:
            inference_text = _first_snippet(combined, _INFERENCE_PATTERN)

        meets_size = _meets_size_threshold(combined)
        meets_inference = _meets_inference_threshold(combined)

        resource_yes = row.get("Resource_Constraints_Norm", "No") == "Yes"
        edge_candidate = resource_yes or meets_size or meets_inference

        results.append({
            "Paper_ID": row.get("Paper_ID"),
            "Title": row.get("Title"),
            "Year": row.get("Year"),
            "Architecture_Norm": row.get("Architecture_Norm"),
            "LMIC_Score": row.get("LMIC_Score"),
            "Resource_Constraints_Norm": row.get("Resource_Constraints_Norm"),
            "mentions_model_size": mentions_size,
            "mentions_inference_time": mentions_inference,
            "meets_size_threshold": meets_size,
            "meets_inference_threshold": meets_inference,
            "edge_deployment_candidate": edge_candidate,
            "model_size_text": size_text,
            "inference_text": inference_text,
        })

    out_df = pd.DataFrame(results)

    # ---------------------------------------------------------------------------
    # Save CSV
    # ---------------------------------------------------------------------------
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "analysis_edge_deployment.csv"
    out_df.to_csv(out_path, index=False)

    # ---------------------------------------------------------------------------
    # Summary printout
    # ---------------------------------------------------------------------------
    n_total = len(out_df)
    n_size = out_df["mentions_model_size"].sum()
    n_inference = out_df["mentions_inference_time"].sum()
    n_meets_size = out_df["meets_size_threshold"].sum()
    n_meets_inference = out_df["meets_inference_threshold"].sum()
    n_edge = out_df["edge_deployment_candidate"].sum()
    n_resource = (out_df["Resource_Constraints_Norm"] == "Yes").sum()

    print("\n=== Edge Deployment Feasibility Analysis ===\n")
    print(f"  Total papers analyzed                      : {n_total}")
    print(f"  Papers mentioning model size               : {n_size}")
    print(f"  Papers mentioning inference time           : {n_inference}")
    print(f"  Papers meeting size threshold (<100 MB)    : {n_meets_size}")
    print(f"  Papers meeting inference threshold (<5 s)  : {n_meets_inference}")
    print(f"  Edge deployment candidates (any criterion) : {n_edge}")
    print(f"  Papers addressing resource constraints     : {n_resource}")

    # ---------------------------------------------------------------------------
    # Detailed table of edge deployment candidates
    # ---------------------------------------------------------------------------
    candidates = out_df[out_df["edge_deployment_candidate"]].copy()
    candidates = candidates.sort_values(["LMIC_Score", "Year"], ascending=[False, False])

    print(f"\n--- Edge Deployment Candidates (n={len(candidates)}) ---\n")
    col_w = {"Paper_ID": 8, "Year": 4, "Architecture_Norm": 14,
              "LMIC_Score": 5, "Resource_Constraints_Norm": 12}
    header = (
        f"  {'ID':>8}  {'Year':>4}  {'Architecture':<14}  {'LMIC':>5}  "
        f"{'Resource':>12}  {'Size?':>5}  {'Infer?':>6}  Title"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for _, r in candidates.iterrows():
        title_short = str(r["Title"])[:55] + ("..." if len(str(r["Title"])) > 55 else "")
        print(
            f"  {str(r['Paper_ID']):>8}  {str(r['Year']):>4}  "
            f"{str(r['Architecture_Norm']):<14}  {str(r['LMIC_Score']):>5}  "
            f"{'Yes' if r['Resource_Constraints_Norm'] == 'Yes' else 'No':>12}  "
            f"{'Yes' if r['meets_size_threshold'] else 'No':>5}  "
            f"{'Yes' if r['meets_inference_threshold'] else 'No':>6}  "
            f"{title_short}"
        )

    print(f"\n  Saved: {out_path}")
    return out_df


if __name__ == "__main__":
    analyze_edge_deployment()
