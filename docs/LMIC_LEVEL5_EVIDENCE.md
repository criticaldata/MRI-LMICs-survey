# Publication evidence for LMIC Relevance Level 5

The final scientific corpus contains 45 DOI-keyed studies. The original
48-record scoring form and independent author ratings are separate: this
revision does not rescore any author rating or change agreement estimates.

Level 5 is the highest tier of the existing rubric. Any one of the following
qualifies: documented acquisition in an LMIC setting; at least one coauthor
with a publication affiliation in an LMIC; or clinical validation on a
portable or point-of-care MRI system. Affiliation is not nationality,
acquisition geography, or evidence of successful clinical deployment.

All 45 bylines were checked against the publication PDF or DOI-matched
publication affiliation metadata where the local copy did not provide the
byline detail. Country groups use the frozen World Bank API snapshot dated
2026-08-03: low-income (LIC), lower-middle-income (LMC), and
upper-middle-income (UMC) qualify; high-income (HIC) does not. These are the
snapshot classifications, not a reconstruction of each publication year's
income tier. The snapshot retains its URL and raw-response SHA-256.
Publication affiliation evidence is separate from the bibliometric
candidate fields obtained from external indices.

- `data/publication_affiliation_evidence.csv`: title, DOI, all affiliation
  countries, first-author affiliation country, source locator, supporting
  excerpt or paraphrase, and source hash where available.
- `data/lmic_relevance_evidence.csv`: original score, lower-tier fallback,
  three Level 5 decision branches, and supporting evidence. A branch can
  remain unclear or not further assessed where another branch qualifies.
  Unclear evidence never grants Level 5. This is a targeted Level 5
  reconciliation, not a fresh adjudication of every lower-level criterion.
- `scripts/analysis/apply_lmic_relevance_evidence.py`: fail-closed
  application of the frozen evidence to the public derivative. It preserves
  the normalized original score and original justification; it does not
  modify the original extraction workbook.

The reconciled Level 5 count is 23/45: 21 supported by publication
coauthorship, plus two with documented portable clinical validation without
LMIC coauthorship. Two previous Level 5 records without affirmative
evidence in any branch were reclassified to Level 4 based on their
documented low-field technical experiments. In addition to the score table,
the change affects score-dependent descriptive, correlation, and exploratory
prediction outputs. It does not alter the TR criterion values or historical
agreement exercise.
