# Scientometrics & Geographic Equity Methodology

## Current reproducible MRI adapter

## Public release boundary

The public repository versions only the flat 48-DOI result table
(`tables/mri_scientometric_results.csv`) and its source-coverage table
(`tables/mri_scientometric_source_coverage.csv`). Raw API responses, local
credential files, and internal audit workspaces remain ignored. The public
offline verifier checks this released schema and coverage without querying any
external service.

The authoritative local scientometric workflow has two layers:
`scripts/analysis/mri_scientometric_openalex.py` is the credential-free
baseline, and `scripts/analysis/mri_scientometric_multisource.py` is the
DOI-scoped enrichment adapter. Both adapt the generic scientometric tool's DOI
reconciliation, cached API retrieval, authorship-role extraction, and
coverage-audit logic to the current 48-study MRI corpus.

The baseline run uses the latest `data-clean` worksheet, the supplementary
geographic table, a validated DOI map, OpenAlex, and a cached World Bank
country snapshot. The enrichment run additionally uses DOI-scoped PubMed,
Europe PMC, Crossref, Semantic Scholar, ORCID, Elsevier's abstract endpoint,
IEEE Computer Society CSDL GraphQL metadata, and targeted SerpAPI searches.
The enrichment run reads credentials only at runtime from the generic tool's
`.env`; no credential value is written to an output. Azure is not used. The
generated snapshots are under `analysis/scientometrics/openalex_20260803/`
and `analysis/scientometrics/multisource_20260803/`; each manifest records
input hashes, endpoints, timestamps, raw-response hashes, and coverage.

The older `world_bank_fetcher.py` and `table6_geographic_equity.py` scripts are
kept for historical compatibility. Their outputs should not be mixed with the
current adapter without an explicit source and snapshot audit.

This document outlines the methodology for the geographic equity assessment,
specifically detailing how bibliographic metadata is integrated with
socioeconomic indices to evaluate representation in MRI super-resolution
research.

## 1. External Data Sources & APIs

The current adapter relies on two external snapshots and one local input:

1. **OpenAlex API**: Primary bibliographic database for author, institution, country, and corresponding-role baseline metadata.
2. **World Bank API**: Country income classification, with the raw response cached in `analysis/scientometrics/openalex_20260803/world_bank_countries_raw.json`.
3. **PubMed, Europe PMC, Crossref, Semantic Scholar**: DOI-scoped publication metadata and author affiliations; Europe PMC JATS is parsed for explicit corresponding-author markers when full text is available.
4. **ORCID**: Employment, education, qualification, and DOI-linked work evidence; profile employment is not treated as publication affiliation without supporting evidence.
5. **Elsevier Abstract API and IEEE Computer Society CSDL**: Additional publication-level affiliation metadata for Elsevier and IEEE Computer Society records. IEEE CSDL does not expose the corresponding-author marker.
6. **Targeted SerpAPI/Google**: Used only for DOI-specific correspondence snippets; accepted only when a unique author match and country-code email agree with publication affiliation evidence.
7. **Local DOI map and supplementary geography table**: DOI identity is supplied by the validated local map; the supplementary table is joined by the checked 1..48 sequence and audited by title similarity.

The OpenAlex work-level country and institution counts are derived from
authorship affiliation records when the work-level fields are empty. This
prevents a zero-filled work-level country count from being mistaken for an
absence of international authorship.

## 2. Institutional Equity Classification

The pipeline automatically maps author affiliation countries to the following equity classifications:
- **Global South (Local Research)**: Corresponds to Low-Income (LIC), Lower-Middle-Income (LMIC), and Upper-Middle-Income (UMIC) economies.
- **HIC (High-Income / Parachute Risk)**: High-Income economies. Assessed specifically for 'parachute research' dynamics when papers focus on LMIC problems without local leadership.
- **UNKNOWN (Manual Review)**: Cases where the source geography table or OpenAlex metadata does not resolve a country, income group, or corresponding-author flag. These entries are logged and are not imputed.

### Note on "UNKNOWN" Affiliations
When an affiliation yields an `UNKNOWN` status, the adapter keeps the missing
value and records the reason in
`analysis/scientometrics/openalex_20260803/scientometric_unknown_audit.csv`
and `scientometric_unknown_records.csv`. It does not infer author nationality,
data origin, or corresponding-author status from nearby fields.

## 3. Geographic Equity Analysis

The current OpenAlex adapter integrates these data streams to generate the
descriptive equity outputs. The historical `table6_geographic_equity.py`
module is not the authoritative source for the current snapshot. The current
outputs include:

- **Panel A: Income Group Distribution**: 
  - Absolute count of papers led by corresponding authors from each income level.
  - Percentage representation (Global North vs. Global South).
- **Panel B: LMIC Score by Region**: 
  - The median `LMIC_Score` (1-5 scale) calculated per geographic region.
  - Identification of dominant MRI application areas within those regions.
- **Panel C: Research Gaps Map**: 
  - A matrix computing `countries × application areas`, which identifies specific thematic gaps in underrepresented geographies.

### Generating the current snapshot

The table can be re-generated by running the following command from the repository root:
```bash
python scripts/analysis/mri_scientometric_openalex.py --input-xlsx <latest-extraction.xlsx> --supplementary-docx <geography-table.docx> --doi-map <validated-doi-map.csv> --output-dir analysis/scientometrics/openalex_20260803 --offline
```

**Output location**: `analysis/scientometrics/openalex_20260803/`.
The raw OpenAlex responses, request log, World Bank snapshot, source hashes,
coverage, reconciliation, and unknown audit are retained there.

## 4. Methodological Limitations

It is critical to acknowledge that this geographic equity tracking evaluates **institutional affiliations (metadata)** rather than **on-the-ground deployment**. 

A paper authored by an institution in a UMIC/LMIC does not unequivocally mean the model was clinically deployed or tested in a limited-resource setting. Similarly, HIC authors might successfully deploy systems in LMICs. Consequently, the World Bank metadata provides a proxy for *research leadership and resourcing trends*, but the `LMIC_Score` (derived from manual reading of the study's claims and evaluation) remains the ground truth for intended geographic applicability.

The current multi-source snapshot reports 48 included studies, 48/48
Crossref coverage, 31/48 Europe PMC coverage, 22 applicable Elsevier abstract
responses, 1/12 applicable IEEE CSDL records, and 164/164 ORCID identifier
requests. All 48 first-author countries are resolved; 47 corresponding-author
countries are resolved automatically and one remains unresolved because the
available sources expose author countries (CN and SE) but not the corresponding
author role. These denominators are retained in
`analysis/scientometrics/multisource_20260803/multisource_coverage.csv`;
missing role metadata is not silently converted to an HIC or Global South
category.

### Generating the multi-source enrichment

From the repository root, run:

```bash
python scripts/analysis/mri_scientometric_multisource.py --env-file <generic-tool-.env> --sources pubmed europepmc semantic crossref orcid scopus serpapi elsevier ieee_csdl
```

The command writes only to `analysis/scientometrics/multisource_20260803/`.
It does not modify the canonical extraction table, the manuscript, or GitHub.
