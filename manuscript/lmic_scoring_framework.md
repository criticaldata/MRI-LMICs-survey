# LMIC Relevance Scoring Framework

## Rationale

Despite growing interest in deploying AI tools in low- and middle-income countries, no standardized framework exists for assessing the translational relevance of medical imaging research to resource-constrained settings. Existing quality assessment tools for systematic reviews (e.g., QUADAS-2, PROBAST) evaluate methodological rigor but do not capture whether a study's methods, assumptions, or evaluation conditions are applicable outside high-resource institutions. To address this gap, we developed a purpose-built LMIC Relevance Score as part of our data extraction protocol (checklist item #10). The framework was iteratively refined by the review team and pilot-tested on an initial subset of papers before full deployment.

## Scoring Criteria

Each reviewed study was assigned an integer score from 1 to 5 based on the following definitions:

**Score 1 -- No LMIC relevance.**
The study is conducted entirely in a high-resource context with no discussion of generalizability. Methods assume high-field scanners (3T or above), large computational budgets, or proprietary data and software. No mention of accessibility, cost, or deployment constraints.

**Score 2 -- Limited relevance.**
The study uses standard clinical-field MRI (1.5T) and standard computational infrastructure. There is no explicit discussion of resource constraints, efficiency, or applicability to settings outside well-equipped academic medical centers.

**Score 3 -- Moderate relevance.**
The study acknowledges computational efficiency, model size, or inference speed as design considerations. It may mention potential applicability to resource-limited settings in passing but does not tailor methods or experiments to such environments.

**Score 4 -- High relevance.**
The study explicitly addresses low-field MRI enhancement, lightweight architectures suitable for edge or low-GPU deployment, or techniques that reduce reliance on large paired datasets. Methods are plausibly applicable to LMIC clinical workflows, even if not explicitly tested in such settings.

**Score 5 -- Direct LMIC application.**
Low-field MRI (typically below 1T) is the primary imaging context. The study directly targets LMIC deployment, uses data from low-resource institutions, or evaluates performance under conditions representative of LMIC clinical practice (e.g., Hyperfine 64 mT scanners, limited computational hardware, small or unpaired training sets).

## Application

Two independent reviewers scored each of the 56 included studies. Discrepancies were resolved by consensus discussion. The distribution of scores across the reviewed literature is reported in the Results section.
