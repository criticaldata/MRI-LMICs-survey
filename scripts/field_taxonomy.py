"""Shared, conservative MRI field-strength taxonomy.

Numeric classes are assigned only when a field strength is explicitly reported.
Generic labels such as "low-field" remain separate from the numeric bins.
Input and target field strengths are stored and analyzed independently in the
field-characterization evidence table.
"""

from __future__ import annotations

import math
import re


FIELD_CATEGORY_ORDER = [
    "Ultra-low-field (<0.05 T)",
    "Low-field (0.05-0.5 T)",
    "Intermediate-field (>0.5-<1.5 T)",
    "Standard-field (1.5-3 T)",
    "High-field (>3 T)",
    "Ultra-low-field (strength unspecified)",
    "Low-field (threshold unspecified)",
    "Standard-field (strength unspecified)",
    "High-field (threshold unspecified)",
    "Mixed",
    "Not specified",
    "Not reported",
    "Unknown",
]

NUMERIC_FIELD_CATEGORIES = set(FIELD_CATEGORY_ORDER[:5])

_FIELD_TOKEN = re.compile(
    r"(?<![\w.])(?P<value>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>millitesla|mT|tesla|T)\b",
    flags=re.IGNORECASE,
)
_SHARED_UNIT_PAIR = re.compile(
    r"(?<![\w.])(?P<first>\d+(?:[.,]\d+)?)\s*(?:and|&)\s*"
    r"(?P<second>\d+(?:[.,]\d+)?)\s*(?P<unit>millitesla|mT|tesla|T)\b",
    flags=re.IGNORECASE,
)
_FIELD_DESCRIPTOR = re.compile(
    r"(?P<descriptor>ultra[ -]?low(?:[ -]?field)?|low[ -]?field|"
    r"standard[ -]?field|high[ -]?field)",
    flags=re.IGNORECASE,
)


def _field_class_from_tesla(value: float) -> str:
    if value < 0.05:
        return "Ultra-low-field (<0.05 T)"
    if value <= 0.5:
        return "Low-field (0.05-0.5 T)"
    if value < 1.5:
        return "Intermediate-field (>0.5-<1.5 T)"
    if value <= 3.0:
        return "Standard-field (1.5-3 T)"
    return "High-field (>3 T)"


def _to_tesla(value: str, unit: str) -> float:
    numeric = float(value.replace(",", "."))
    if unit.casefold() in {"mt", "millitesla"}:
        return numeric / 1000.0
    return numeric


def reported_field_strengths_tesla(value: object) -> list[float]:
    """Return only field strengths explicitly written with T or mT units."""
    text = " ".join(str(value).strip().casefold().replace(",", ".").split())
    values: list[float] = []
    for match in _SHARED_UNIT_PAIR.finditer(text):
        unit = match.group("unit")
        values.extend(
            [
                _to_tesla(match.group("first"), unit),
                _to_tesla(match.group("second"), unit),
            ]
        )
    remaining = _SHARED_UNIT_PAIR.sub(" ", text)
    values.extend(
        _to_tesla(match.group("value"), match.group("unit"))
        for match in _FIELD_TOKEN.finditer(remaining)
    )
    return values


def has_reported_low_field_strength(value: object) -> bool:
    """Whether a numeric field in the text falls within 0.05-0.5 T."""
    return "Low-field (0.05-0.5 T)" in reported_field_categories(value)


def reported_field_categories(value: object) -> set[str]:
    """Return numeric field bins explicitly evidenced in the raw text."""
    return {
        _field_class_from_tesla(field_t)
        for field_t in reported_field_strengths_tesla(value)
    }


def normalize_field_category(value: object) -> str:
    """Map a reported field label to the shared category without guessing."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "Not specified"
    except (TypeError, ValueError):
        pass

    text = " ".join(str(value).strip().casefold().replace("_", " ").split())
    if not text or text in {"nan", "none", "<na>", "not specified", "not specified."}:
        return "Not specified"
    if text in {"not reported", "not reported."}:
        return "Not reported"
    if text in {"unknown", "unclear"}:
        return "Unknown"
    if re.search(r"\bmixed\b", text):
        return "Mixed"

    numeric_categories = reported_field_categories(text)

    unspecified_descriptors: set[str] = set()
    for match in _FIELD_DESCRIPTOR.finditer(text):
        nearby = text[max(0, match.start() - 24) : match.end() + 40]
        if _FIELD_TOKEN.search(nearby) or _SHARED_UNIT_PAIR.search(nearby):
            continue
        descriptor = match.group("descriptor").replace(" ", "-")
        if descriptor.startswith("ultra"):
            unspecified_descriptors.add("Ultra-low-field (strength unspecified)")
        elif descriptor.startswith("low"):
            unspecified_descriptors.add("Low-field (threshold unspecified)")
        elif descriptor.startswith("standard"):
            unspecified_descriptors.add("Standard-field (strength unspecified)")
        else:
            unspecified_descriptors.add("High-field (threshold unspecified)")

    all_classes = numeric_categories | unspecified_descriptors
    if len(all_classes) > 1:
        return "Mixed"
    if numeric_categories:
        return next(iter(numeric_categories))
    if unspecified_descriptors:
        return next(iter(unspecified_descriptors))
    return "Unknown"
