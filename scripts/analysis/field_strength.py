"""The one field-strength taxonomy used by every part of the pipeline.

The manuscript states a single schema: Low-field below 1.5 T (including a
low-field acquisition mapped to a standard- or high-field target), Standard-field
1.5 to 3 T, High-field above 3 T, Mixed for co-equal arms across tiers, and Not
specified. Three modules used to carry their own copy of this logic and
disagreed, which is how a figure panel once contradicted the tables. Import from
here instead of writing another one.
"""

from __future__ import annotations

import re

# Exact labels as they appear in data/data-clean.csv. The curated reading always
# wins, because a raw label alone cannot say whether two field strengths are
# co-equal arms (Mixed) or a source-to-target mapping (Low-field).
CURATED_LABELS = {
    "Not_specified": "Not specified",
    "Standard-field": "Standard-field",
    "standard field": "Standard-field",
    "3T MRI": "Standard-field",
    "1.5 and 3T MRI": "Standard-field",
    "1.5T and 3T MRI scanners": "Standard-field",
    "1.5T and 3T": "Standard-field",
    "Low-field": "Low-field",
    "Low-Field MRI": "Low-field",
    "Low-Field": "Low-field",
    "Low_field (0.1T)": "Low-field",
    "Portable Ultra-Low Field (0.064 Tesla)": "Low-field",
    "Ultra-low-field (64 mT / 0.064 T) vs. High-field (3.0 T)": "Low-field",
    "Low field (64 mT) and Standard field (3 T)": "Low-field",
    "Low-field (0.4T) + High-field reference (3T)": "Low-field",
    "Mixed (0.36 T and 1.5 T)": "Mixed",
    "Mixed": "Mixed",
    "High-field": "High-field",
}

CATEGORIES = ("Low-field", "Standard-field", "High-field", "Mixed", "Not specified")

# Underscore spelling used by the older statistical modules.
LEGACY = {
    "Low-field": "Low_Field",
    "Standard-field": "Standard_Field",
    "High-field": "High_Field",
    "Mixed": "Mixed",
    "Not specified": "Not_Specified",
}

_MT = re.compile(r"\b\d+(?:\.\d+)?\s*mt\b|\b0\.\d+\s*t\b")
_LOW = re.compile(r"low[ _-]?field|ultra[ _-]?low")
_STANDARD = re.compile(r"standard|1\.5\s*t|\b3\s*t\b|high[ -]?field")
_HIGH = re.compile(r"\b7\s*t\b|\b9\.4\s*t\b")


def normalize(value: object) -> str:
    """Map a raw Field_Strength_Type label to one of CATEGORIES."""
    if value is None:
        return "Not specified"
    raw = str(value).strip()
    if raw in CURATED_LABELS:
        return CURATED_LABELS[raw]
    text = " ".join(raw.split()).casefold()
    if not text or text in {"not reported", "not_specified", "nan", "none"}:
        return "Not specified"
    has_low = bool(_LOW.search(text) or _MT.search(text))
    has_standard = bool(_STANDARD.search(text))
    if has_low and has_standard:
        return "Mixed"
    if has_low:
        return "Low-field"
    if "high-field" in text or _HIGH.search(text):
        return "High-field"
    if has_standard:
        return "Standard-field"
    return "Unknown"


def normalize_legacy(value: object) -> str:
    """Same taxonomy in the underscore spelling the statistical modules use."""
    return LEGACY.get(normalize(value), "Not_Specified")
