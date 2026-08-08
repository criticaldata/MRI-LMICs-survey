# Public Release Audit — 2026-08-08

## Scope

This release contains the anonymized 48-study corpus, current analysis code,
regenerated tables and figures, public scientometric results, source coverage,
and offline verification tests.

## Deliberately excluded

- reviewer names and reviewer assignments;
- individual reviewer ratings and pending Fleiss kappa inputs;
- historical 10-study / 2-rater calibration outputs;
- local API credentials, `.env` files, and raw provider-response caches;
- internal screening, provenance, and reviewer-workbook artifacts.

## Automated checks

- Public corpus: 48 rows; reviewer identity columns absent.
- Core reproducibility verifier: PASS.
- Public scientometric release audit: PASS (48 unique DOI rows, explicit
  missing-value labels, no methodology or reviewer fields, and structured
  source coverage).
- Test suite: 37 passed.

## Reproduction entry point

Run the public pipeline from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/analysis/run_full_reproducibility_pipeline.ps1 -RunDate 20260808
```

The pipeline is offline and does not query APIs or publish changes. The final
Fleiss kappa calculation remains intentionally pending until complete
independent ratings are received.
