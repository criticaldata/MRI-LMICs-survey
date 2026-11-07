# Condition-specific performance metric extraction

## What is selected

`data/performance_metric_evidence.csv` freezes source-checked proposed-model
results keyed by normalized DOI, metric, dataset, model, and condition. The
`Is_Primary` flag supplies exactly one scalar per DOI/metric for existing
plots and tables. No maximum, prose order, or study-number lookup chooses a
reviewed result. These are **retrospective extraction decisions**, not
prespecified author endpoints or a preregistered review rule.

| Canonical study / DOI | Source and condition | Proposed result | Scalar primary |
| --- | --- | --- | --- |
| Paper_ID 24 / 10.1109/tmi.2020.2974858 | Table III, PDF p10, C-PRO, IXI, 4x T2 SR with HR PD reference | PSNR 35.140 dB; SSIM .961 | Yes |
| Same DOI | Table III, PDF p10, C-PRO, NAMIC, 4x T2 SR with HR T1 reference | PSNR 30.942 dB; SSIM .953 | No; separate dataset evidence retained |
| Paper_ID 39 (scoring form 42) / 10.1109/icmipe53131.2021.9698880 | Table I, PDF p4, Ours/SMIR, HCP T1, radial k-space sampling 10/20/30/40/50% | SSIM .72/.86/.87/.89/.91 | 20%: .86 |

For C-PRO, use the proposed progressive model in the main Table III, with IXI
as the representative scalar dataset and NAMIC retained as a distinct result.
This is a review-level scalarization choice: Table III does not establish IXI
as a prespecified primary endpoint. Do not average the datasets or take the
maximum across all experiments. The IXI 4xLR baseline (27.151 dB/.793) is not a
proposed-model result. The discussion's loss-function experiment
(38.513 dB/.976, also PDF p10) is not a replacement for the requested main
Table III condition. Table III reports means with 95% confidence intervals;
the CSV records the means only.

For SMIR, Section IV.B on PDF p4 is specifically devoted to reconstruction at
20% sampling; Figure 4 on PDF p5 shows that comparison and its caption confirms
the 20% condition. This supports selecting .86 as a representative scalar,
not treating 20% as the paper's only or formally primary experiment. The full
condition series remains in the CSV, with a range of .72-.91. Do not choose
.91 solely because it is highest or interpret `10%` as SSIM=10. PSNR is not
reported (the paper evaluates SSIM and MAE); an explicit missing-PSNR evidence
row prevents substituting either MAE or a sampling ratio.

Source check: 2026-11-03, supplied local PDFs reviewed by text extraction and
rendered Table III / Table I pages. `Source_File` stores only the source
basename, not a private absolute path. PDFs, raw ratings, and credentials are
not added to the repository. Source values are reported evidence, not newly
recomputed experimental performance.

## Integration and safeguards

`scripts/metric_extraction.py` reads and validates the evidence.
`scripts/figures/mapper.py::load_data` applies it to derived numeric columns.
The master CSV and its `PSNR_Value` / `SSIM_Value` narrative fields are not
rewritten. Existing whitespace normalization remains unchanged.

The DOI matcher handles case, surrounding whitespace, `doi:`, and
`https://doi.org/` / `https://dx.doi.org/` prefixes. `Paper_ID` and `Title` in
the evidence are contextual identifiers for this corpus, not join keys.
Reordering rows or changing a paper number cannot swap results between DOIs.
Missing evidence files, malformed values/status, duplicate conditions,
baseline/ablation roles, or zero/multiple primary rows raise errors rather
than silently falling back.

For each metric, the loader also exposes `Selection_Method`, `Selection_Rule`,
`Primary_Condition`, `Dataset`, `Model`, `Evidence_Source`, `Evidence_Min`, and
`Evidence_Max` (prefixed `PSNR_` or `SSIM_`). Min/max cover retained reported
conditions; they are not confidence intervals and must not replace the
condition rows for interpretation.

Unreviewed DOIs retain an explicitly labelled `free_text_fallback`: the first
plausible metric-specific value, excluding percentage labels. A raw range
such as `26.53-29.25 dB` still yields 26.53 for legacy scalar consumers, not
29.25 or a preceding sampling percentage. Its full range stays in the raw
text; no evidence range is invented for an unreviewed study. SSIM is bounded
to [0, 1]. This fallback cannot establish which model or experiment a number
belongs to. Add reviewed keyed evidence to resolve further ambiguous studies;
do not present this two-study correction as a full-corpus source audit.

## Regression verification

Use the existing reproducible environment from the repository root:

```powershell
python -m pytest tests/analysis/test_metric_evidence_selection.py -q
```

Before implementation, the new tests demonstrated selection of 27.15/.793
for C-PRO, missing SMIR SSIM, 20 instead of the 26.53 range endpoint, and
selection of 38.513 after ablation-first reordering. Tests also cover all
retained conditions, visible provenance, DOI rather than positional matching,
raw-field preservation, sentence punctuation, percentage labels, missing
metrics, and invalid evidence rejection.

The full reproduction pipeline regenerates the performance figures and
reporting profiles using these same derived metric values. The evidence CSV
is versioned and required in a fresh checkout.
