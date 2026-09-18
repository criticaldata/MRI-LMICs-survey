"""Validate and merge independent reviewer workbooks without calculating kappa.

The validator expects one private workbook per reviewer, each containing all
48 rows in the ``LMIC_Score`` sheet. It writes a long-format table and a
wide-format matrix for the later Fleiss-kappa step, but deliberately stops
before calculating agreement.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]


def read_one(path: Path, reviewer_id: str) -> pd.DataFrame:
    if path.suffix.casefold() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(path, sheet_name="LMIC_Score", header=3)
    else:
        frame = pd.read_csv(path)
    required = {"Paper_ID", "LMIC_Relevance_Score_1_to_5"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    result = frame[["Paper_ID", "LMIC_Relevance_Score_1_to_5"]].copy()
    result["Paper_ID"] = pd.to_numeric(result["Paper_ID"], errors="raise").astype(int)
    result["Reviewer_ID"] = reviewer_id
    result["Source_File"] = path.name
    result["Score"] = pd.to_numeric(result["LMIC_Relevance_Score_1_to_5"], errors="coerce")
    return result[["Paper_ID", "Reviewer_ID", "Score", "Source_File"]]


def validate(input_dir: Path, output_dir: Path, allow_blank: bool = False) -> dict:
    files = sorted(
        path for path in input_dir.iterdir()
        if path.suffix.casefold() in {".xlsx", ".xlsm", ".csv"}
        and not path.name.startswith("~$")
    )
    if not files:
        raise FileNotFoundError(f"No reviewer workbooks/CSVs found in {input_dir}")

    canonical = pd.read_csv(REPO / "data" / "data-clean.csv")
    expected_ids = set(pd.to_numeric(canonical["Paper_ID"], errors="raise").astype(int))
    frames = []
    for path in files:
        reviewer_id = path.stem
        frame = read_one(path, reviewer_id)
        if frame["Paper_ID"].duplicated().any():
            raise ValueError(f"{path.name} contains duplicate Paper_ID values")
        if set(frame["Paper_ID"]) != expected_ids:
            raise ValueError(f"{path.name} Paper_ID set does not match the frozen 48-study set")
        if not allow_blank and frame["Score"].isna().any():
            raise ValueError(f"{path.name} contains blank LMIC scores")
        invalid = frame["Score"].dropna().loc[~frame["Score"].dropna().between(1, 5)]
        if not invalid.empty:
            raise ValueError(f"{path.name} contains scores outside 1..5: {invalid.tolist()}")
        frames.append(frame)

    long = pd.concat(frames, ignore_index=True)
    if long.duplicated(["Paper_ID", "Reviewer_ID"]).any():
        raise ValueError("The merged rating table contains duplicate Paper_ID/reviewer pairs")
    wide = long.pivot(index="Paper_ID", columns="Reviewer_ID", values="Score").reset_index()
    wide = wide.sort_values("Paper_ID")
    reviewer_columns = [column for column in wide.columns if column != "Paper_ID"]
    missing_cells = int(wide[reviewer_columns].isna().sum().sum())

    output_dir.mkdir(parents=True, exist_ok=True)
    long.to_csv(output_dir / "reviewer_ratings_long.csv", index=False, encoding="utf-8")
    wide.to_csv(output_dir / "reviewer_ratings_wide.csv", index=False, encoding="utf-8")
    manifest = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer_files": [path.name for path in files],
        "reviewer_count": len(reviewer_columns),
        "papers": len(expected_ids),
        "ratings_expected": len(expected_ids) * len(reviewer_columns),
        "ratings_present": int(long["Score"].notna().sum()),
        "missing_cells": missing_cells,
        "complete_for_full_irr": bool(len(reviewer_columns) == 11 and missing_cells == 0),
        "fleiss_kappa_calculated": False,
        "status": "READY_FOR_FLEISS_KAPPA" if len(reviewer_columns) == 11 and missing_cells == 0 else "INCOMPLETE",
    }
    (output_dir / "reviewer_ratings_validation.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "analysis" / "reproducibility" / "reviewer_ratings",
    )
    parser.add_argument("--allow-blank", action="store_true")
    args = parser.parse_args()
    result = validate(args.input_dir.resolve(), args.output_dir.resolve(), args.allow_blank)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
