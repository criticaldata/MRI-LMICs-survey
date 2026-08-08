# Local Validation Report - 2026-08-08

## Scope

This validation covers the corrected public MRI-LMICs reproducibility package.
It does not query external APIs or calculate final Fleiss' kappa.

## Fresh verification evidence

- An isolated Python 3.12 environment was created from `requirements-reproducible-review.txt`.
- `pip check`: no broken requirements.
- `python scripts/analysis/verify_reproducibility.py`: PASS.
- `python scripts/analysis/verify_mri_scientometric_reproducibility.py --public-release`: PASS (four public-release checks).
- `python -m pytest -q`: 37 passed.
- `git diff --check`: PASS.

## Validated reviewer-correction outputs

- Screening: 183 records, 48 included, 135 excluded.
- Quality: mean 4.1458/9, sample SD 1.1848.
- Code: 6 public and 2 available on request.
- Resource constraints: 33/48 explicitly evidenced.
- TR weighting: four prespecified schemes, 10,000 permutations, seed 42.
- Ground-truth audit: 20 studies reporting PSNR or SSIM; unsupported fields remain `Not reported` rather than inferred.
- Temporal analysis: 2020-2024 is primary; 2025 is separate and labelled preliminary/incomplete.
- Random Forest robustness: 50 repeated held-out splits per model; supplementary and exploratory only.
- Fleiss' kappa: pending until independent ratings for all 48 included studies are received from all 11 reviewers.

## Artifact status

The old 10-study/two-rater calibration result is private historical provenance.
It is not an active public table or a final IRR result. The public corpus
contains no reviewer identities, assignments, or individual ratings.
