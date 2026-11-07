# Scientometric Enrichment and Geographic Metadata

## Scope and public outputs

The public flat export, `tables/mri_scientometric_results.csv`, contains the
46-study final eligible corpus. `data/included_study_order.csv` is the
canonical DOI/title order; the export is aligned to it by DOI and title, not by
numeric shifting. Recreate the offline alignment and its manifest with:

```powershell
py -3.12 scripts/analysis/align_mri_scientometric_export.py
```

The companion `tables/mri_scientometric_source_coverage.csv` describes the
earlier API acquisition over the original 48-record scoring form. It is
historical source coverage, not a fresh API-coverage run over the final 46
studies. The export manifest states this denominator explicitly.

The offline alignment does not contact APIs. Optional DOI-scoped enrichment
uses the generic scientometric tool's API logic through
`scripts/analysis/mri_scientometric_multisource.py`; it is a separate networked
acquisition step and is not required to regenerate the published flat table.
Credentials are read at runtime from an externally supplied environment file
and are never part of the repository or its outputs. The complete MRI analysis
pipeline does not call external APIs.

## Sources and field meaning

The enrichment logic combines publication metadata and author-affiliation
evidence from OpenAlex, PubMed, Europe PMC, Crossref, Semantic Scholar, ORCID,
Elsevier, IEEE Computer Society CSDL, and DOI-matched SerpAPI results. Europe
PMC full-text XML is available only for some indexed open-access articles.
Scopus did not provide usable coverage in the recorded acquisition because
access was rejected; it is not treated as a resolved source. The source
coverage CSV keeps provider outcomes separate from analytical results.

Country fields distinguish publication-affiliation evidence from ORCID
employment or education, author names, nationality, and the study's data
collection location. Employment and education are not substituted for a
publication affiliation. Corresponding-author country is recorded only when
the source supports both the author role and the country; a country candidate
for an author is not by itself proof that the author was the corresponding
author. Unresolved or conflicting records remain explicitly unavailable or
unknown.

World Bank income-group labels use the standard codes `HIC` (high income),
`UMC` (upper-middle income), `LMC` (lower-middle income), and `LIC` (low
income). The legacy labels `UMIC` and `LMIC` in the first-author group field
are normalized to `UMC` and `LMC`, respectively. This normalization applies
only to that income-group metadata field; it does not change the distinct
study-level `LMIC_Relevance_Score`.

In the final 46-study export, first-author affiliation groups are `HIC` 26,
`UMC` 8, `LMC` 5, and `UNKNOWN` 7. These describe the available first-author
affiliation metadata, not where MRI data were acquired, who led a clinical
deployment, or whether a model is suitable for an LMIC setting. The separate
LMIC Relevance Score is the study-level measure for that question.

## Reproducible interpretation

The flat export and its source-coverage table are public and aggregate at the
study level. Raw API response caches, credentials, individual reviewer
ratings, and reviewer identities are not public outputs. The offline
scientometric verifier checks row count, canonical DOI/title alignment,
allowed output schema, coverage provenance, and public-release privacy without
making network requests.

Affiliation-based income groups are descriptive proxies for research
affiliation patterns, not evidence of local data acquisition, clinical
validation, deployment, or corresponding-author status. Missing values remain
unknown; they are not imputed from nationality, education, or nearby author
records.
