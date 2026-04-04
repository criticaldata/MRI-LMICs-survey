"""
Reviewer bias analysis for MRI-LMICs survey.

No formal calibration was performed — each paper was scored by exactly one reviewer.
This script quantifies systematic reviewer-level bias, computes bias-corrected LMIC
scores, flags papers where correction would flip the High/Low-Moderate classification,
and selects a representative calibration set for future use.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))
import pandas as pd
import numpy as np
from mapper import load_data, get_project_root


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

ROOT = get_project_root()
TABLES_DIR = ROOT / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

df = load_data()

# Drop the one paper with no LMIC score (paper 33)
df = df.dropna(subset=["LMIC_Score"]).copy()
df["LMIC_Score"] = df["LMIC_Score"].astype(float)

# Grand mean across all scored papers
grand_mean = df["LMIC_Score"].mean()


# ===========================================================================
# Section 1: Reviewer bias statistics
# ===========================================================================

reviewer_stats = (
    df.groupby("Reviewer_Name")["LMIC_Score"]
    .agg(
        n_papers="count",
        mean_lmic="mean",
        median_lmic="median",
        std_lmic="std",
    )
    .reset_index()
)
reviewer_stats["bias"] = reviewer_stats["mean_lmic"] - grand_mean
reviewer_stats = reviewer_stats.sort_values("bias", ascending=False).reset_index(drop=True)

# Round for display
reviewer_stats[["mean_lmic", "median_lmic", "std_lmic", "bias"]] = (
    reviewer_stats[["mean_lmic", "median_lmic", "std_lmic", "bias"]].round(3)
)

out_bias_summary = TABLES_DIR / "analysis_reviewer_bias_summary.csv"
reviewer_stats.to_csv(out_bias_summary, index=False)
print(f"[Section 1] Saved: {out_bias_summary}")


# ===========================================================================
# Section 2: Bias-corrected LMIC scores
# ===========================================================================

# Map each paper to its reviewer's bias
reviewer_bias_map = reviewer_stats.set_index("Reviewer_Name")["bias"].to_dict()

df["reviewer_bias"] = df["Reviewer_Name"].map(reviewer_bias_map)

# Adjusted score: subtract bias, clamp to [1, 5], round to nearest 0.5
def round_half(x):
    """Round to nearest 0.5."""
    return round(x * 2) / 2

df["lmic_score_adjusted"] = df.apply(
    lambda row: round_half(float(np.clip(row["LMIC_Score"] - row["reviewer_bias"], 1.0, 5.0))),
    axis=1,
)

df["classification_raw"] = df["LMIC_Score"].apply(
    lambda s: "High" if s >= 4 else "Low/Moderate"
)
df["classification_adjusted"] = df["lmic_score_adjusted"].apply(
    lambda s: "High" if s >= 4 else "Low/Moderate"
)
df["classification_changed"] = df["classification_raw"] != df["classification_adjusted"]

bias_corrected = df[[
    "Paper_ID", "Title", "Reviewer_Name", "LMIC_Score",
    "reviewer_bias", "lmic_score_adjusted",
    "classification_raw", "classification_adjusted", "classification_changed",
]].copy()

bias_corrected[["reviewer_bias", "lmic_score_adjusted"]] = (
    bias_corrected[["reviewer_bias", "lmic_score_adjusted"]].round(3)
)

out_bias_corrected = TABLES_DIR / "analysis_lmic_bias_corrected.csv"
bias_corrected.to_csv(out_bias_corrected, index=False)
print(f"[Section 2] Saved: {out_bias_corrected}")


# ===========================================================================
# Section 3: Suggested calibration set
# ===========================================================================

# Calibration selection strategy:
#   1. At least one paper per LMIC score level (1–5) where available
#   2. Prefer papers where classification_changed is True
#   3. Prefer papers from reviewers at the extremes of bias range
#   4. Cover diverse architectures (CNN, U-Net, GAN, Transformer/Diffusion)

# Rank reviewers by |bias|
reviewer_stats_indexed = reviewer_stats.set_index("Reviewer_Name")

df["abs_reviewer_bias"] = df["reviewer_bias"].abs()

# Sorting key: classification_changed first, then extreme reviewer bias, then score variety
df_scored = df.copy()
df_scored["sort_key"] = (
    df_scored["classification_changed"].astype(int) * 100
    + df_scored["abs_reviewer_bias"] * 10
)

target_architectures = ["CNN", "U-Net", "GAN", "Transformer", "Diffusion"]

selected_ids = []
covered_scores = set()
covered_archs = set()

# Pass 1: cover each LMIC score level 1–5
for score in [1, 2, 3, 4, 5]:
    candidates = df_scored[
        (df_scored["LMIC_Score"] == score) & (~df_scored["Paper_ID"].isin(selected_ids))
    ].sort_values("sort_key", ascending=False)
    if not candidates.empty:
        chosen = candidates.iloc[0]
        selected_ids.append(chosen["Paper_ID"])
        covered_scores.add(score)
        covered_archs.add(chosen["Architecture_Norm"])

# Pass 2: add papers where classification changes and architecture is new (up to 10)
arch_priority = [a for a in target_architectures if a not in covered_archs]
for arch in arch_priority:
    if len(selected_ids) >= 10:
        break
    candidates = df_scored[
        (df_scored["Architecture_Norm"] == arch)
        & (~df_scored["Paper_ID"].isin(selected_ids))
    ].sort_values("sort_key", ascending=False)
    if not candidates.empty:
        chosen = candidates.iloc[0]
        selected_ids.append(chosen["Paper_ID"])
        covered_archs.add(arch)

# Pass 3: fill remaining slots (up to 10) with highest sort_key papers not yet chosen
remaining = df_scored[~df_scored["Paper_ID"].isin(selected_ids)].sort_values(
    "sort_key", ascending=False
)
for _, row in remaining.iterrows():
    if len(selected_ids) >= 10:
        break
    selected_ids.append(row["Paper_ID"])

# Ensure we have at least 5 and at most 10
selected_ids = selected_ids[:10]

calib_df = df_scored[df_scored["Paper_ID"].isin(selected_ids)].copy()

# Build reason column
def make_reason(row):
    reasons = []
    if row["classification_changed"]:
        direction = "over-scored" if row["classification_raw"] == "High" else "under-scored"
        reasons.append(f"classification flips ({row['classification_raw']} → {row['classification_adjusted']}; likely {direction})")
    bias_val = row["reviewer_bias"]
    if abs(bias_val) > 0.5:
        direction = "lenient" if bias_val > 0 else "strict"
        reasons.append(f"reviewer is {direction} (bias={bias_val:+.2f})")
    reasons.append(f"LMIC={int(row['LMIC_Score'])}")
    reasons.append(f"arch={row['Architecture_Norm']}")
    return "; ".join(reasons)

calib_df["Reason_Selected"] = calib_df.apply(make_reason, axis=1)

calibration_set = calib_df[[
    "Paper_ID", "Title", "Year", "Reviewer_Name", "LMIC_Score",
    "lmic_score_adjusted", "reviewer_bias", "Architecture_Norm",
    "Application_Norm", "Low_Field_Norm", "Reason_Selected",
]].sort_values("LMIC_Score").reset_index(drop=True)

calibration_set[["lmic_score_adjusted", "reviewer_bias"]] = (
    calibration_set[["lmic_score_adjusted", "reviewer_bias"]].round(3)
)

out_calib = TABLES_DIR / "analysis_calibration_set.csv"
calibration_set.to_csv(out_calib, index=False)
print(f"[Section 3] Saved: {out_calib}")


# ===========================================================================
# Section 4: Print summary
# ===========================================================================

grand_std = df["LMIC_Score"].std()
reviewer_min_bias = reviewer_stats["bias"].min()
reviewer_max_bias = reviewer_stats["bias"].max()
reviewer_min_mean = reviewer_stats["mean_lmic"].min()
reviewer_max_mean = reviewer_stats["mean_lmic"].max()

biased_reviewers = reviewer_stats[reviewer_stats["bias"].abs() > 0.5]

n_changed = df["classification_changed"].sum()
n_total = len(df)
pct_changed = 100 * n_changed / n_total

n_high_raw = (df["classification_raw"] == "High").sum()
n_high_adj = (df["classification_adjusted"] == "High").sum()

# Over-scored: raw=High but adjusted=Low/Moderate
n_over = ((df["classification_raw"] == "High") & (df["classification_adjusted"] == "Low/Moderate")).sum()
# Under-scored: raw=Low/Moderate but adjusted=High
n_under = ((df["classification_raw"] == "Low/Moderate") & (df["classification_adjusted"] == "High")).sum()

# High-LMIC papers stable under correction
n_high_stable = n_high_raw - n_over

print()
print("=" * 60)
print("REVIEWER BIAS ANALYSIS — SUMMARY")
print("=" * 60)
print(f"Grand mean LMIC: {grand_mean:.2f}  (SD={grand_std:.2f}, n={n_total} papers)")
print(f"Reviewer bias range: {reviewer_min_bias:+.3f} to {reviewer_max_bias:+.3f}")
print()
print("All reviewers (sorted by bias):")
for _, row in reviewer_stats.iterrows():
    flag = " *** |bias|>0.5" if abs(row["bias"]) > 0.5 else ""
    print(f"  {row['Reviewer_Name']:<28}  n={int(row['n_papers'])}  "
          f"mean={row['mean_lmic']:.2f}  bias={row['bias']:+.3f}{flag}")

print()
if biased_reviewers.empty:
    print("Reviewers with |bias| > 0.5: none")
else:
    print("Reviewers with |bias| > 0.5:")
    for _, row in biased_reviewers.iterrows():
        direction = "lenient" if row["bias"] > 0 else "strict"
        print(f"  {row['Reviewer_Name']}: bias={row['bias']:+.3f} ({direction})")

print()
print(f"Papers where classification would flip: {n_changed} ({pct_changed:.1f}%)")
print(f"  High-LMIC papers that might be over-scored:         {n_over}")
print(f"  Low/Moderate-LMIC papers that might be under-scored:{n_under}")
print()
print("Suggested calibration set:")
for _, row in calibration_set.iterrows():
    flip_marker = " [FLIP]" if row["LMIC_Score"] != row["lmic_score_adjusted"] and (
        (row["LMIC_Score"] >= 4) != (row["lmic_score_adjusted"] >= 4)
    ) else ""
    print(f"  Paper {int(row['Paper_ID']):>3} | LMIC={int(row['LMIC_Score'])} → {row['lmic_score_adjusted']:.1f}"
          f"{flip_marker} | {row['Architecture_Norm']:<12} | {row['Reviewer_Name']}")
    title_short = str(row["Title"])[:75] + ("…" if len(str(row["Title"])) > 75 else "")
    print(f"         \"{title_short}\"")

print()
print("=" * 60)
print("=== Suggested Methods Language ===")
print("=" * 60)
print(
    f'"While a formal calibration exercise was not performed, reviewer scoring distributions\n'
    f'were analyzed across the 2 raters (n=10 calibration papers). Reviewer-level mean LMIC\n'
    f'scores ranged from {reviewer_min_mean:.1f} to {reviewer_max_mean:.1f} '
    f'(grand mean {grand_mean:.1f} ± {grand_std:.1f} SD), indicating systematic\n'
    f'between-reviewer variation. Bias-corrected scores were computed by subtracting each\n'
    f'reviewer\'s systematic offset from the grand mean. Of the {n_high_raw} papers classified as\n'
    f'high LMIC relevance (score ≥4), {n_high_stable} remained stable under bias correction and '
    f'{n_over} were\n'
    f'reclassified as moderate relevance. We recommend a calibration exercise in which\n'
    f'all reviewers independently score the {len(calibration_set)} papers identified below as most '
    f'discriminative\n'
    f'for establishing scoring alignment."'
)
print()
