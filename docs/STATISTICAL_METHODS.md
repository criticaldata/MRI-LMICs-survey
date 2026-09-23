# Statistical Methods and Current Results

## Analysis population

All 11 authors independently scored the 48 candidate records on LMIC Relevance and Translational Readiness. Three records were excluded from the final scientific synthesis after DOI/title and eligibility adjudication: an earlier LowGAN preprint duplicated by the retained peer-reviewed article, a generic natural-image enhancement paper with no MRI experiment, and a study whose Methods explicitly state that its method does not use deep learning. The final analytic corpus is 45 studies. Reliability estimates use all 48 scored records because they describe the completed scoring exercise; substantive analyses use the 45 eligible studies. The private workbook is checked against the original 48-record scoring order. See `data/reviewer_scoring_order.csv` and `data/post_extraction_exclusions.csv`.

## Random-forest robustness analysis

This is a supplementary, exploratory ordinal prediction analysis—not a causal or deployable model. It uses a constrained Random Forest, 50 held-out splits from repeated 5-fold cross-validation (10 repeats), a mean baseline, regularized ridge and ordinal-logistic benchmarks, held-out permutation importance, and 200 bootstrap resamples; the fixed seed is 42. On the 45-study corpus, mean held-out MAE is 0.679 (SD 0.175) and mean held-out R² is 0.031 (SD 0.283), compared with MAE 0.782 for the mean baseline. The forest has lower MAE than the baseline in 44 of 50 paired splits. The field-strength feature is positive only when a numeric 0.05-0.5 T field is explicitly reported; generic labels are not treated as measurements. The variation and small corpus limit predictive interpretation. These results do not establish causal effects, feature importance outside this dataset, or deployment readiness.

The aggregate comparison is versioned in `tables/analysis_random_forest_robustness_summary.csv`. Detailed split scores, permutation results, bootstrap intervals, runtime lock, and hashes are generated under `analysis/review_20260803/random_forest_robustness_20260804/` and are local reproducibility outputs rather than individual-rating data.

## Reporting-pattern tests

Mann–Whitney U tests compare LMIC score distributions for studies with versus without parseable PSNR or SSIM. Categorical associations use chi-square or Fisher's exact tests as appropriate; multiplicity-adjusted q-values are retained where multiple hypotheses are tested. These analyses are descriptive/exploratory and do not establish that reporting missingness is random. Current results are in `tables/table5b_mann_whitney_results.csv` and the associated analysis outputs.

## Inter-rater agreement

Each of the 11 authors scored all 48 form records. Standard nominal Fleiss' κ is the prespecified primary multi-rater statistic and is calculated over all 48 scored candidates, including three records later excluded from the scientific synthesis. This estimates agreement for the full scoring task. Scientific outcomes and correlations are calculated over the 45 eligible studies.

| Score | Studies | Fleiss' κ | Observed agreement |
|---|---:|---:|---:|
| LMIC Relevance (1–5) | 48 | 0.505 | 0.648 |
| Translational Readiness (0–5) | 48 | 0.223 | 0.451 |

The historical κ=0.728 from 10 papers and two reviewers is not the full-pool reliability estimate and is not used as the primary result. The individual-rating workbook remains private; the runners read it externally and write aggregate outputs only.

### Ordinal-weighted agreement

Generalized multi-rater weighted Fleiss estimates are supplementary. Linear and quadratic weights give:

| Score | Linear κ | Quadratic κ |
|---|---:|---:|
| LMIC Relevance | 0.528 | 0.544 |
| Translational Readiness | 0.393 | 0.559 |

Pairwise weighted Cohen summaries across 55 reviewer pairs are descriptive and are not a second multi-rater Fleiss statistic. Weighting gives partial credit to near-category disagreements; it does not replace the prespecified unweighted κ and must not be selected simply because it is larger.

### Intraclass correlation

The supplementary ICC model is two-way random effects with absolute agreement. ICC(2,1) is single-rater reliability; ICC(2,k) is reliability of the mean of 11 raters.

| Score | ICC(2,1) | ICC(2,k) |
|---|---:|---:|
| LMIC Relevance | 0.553 | 0.932 |
| Translational Readiness | 0.570 | 0.936 |

ICC treats ordinal categories as equally spaced and is not a substitute for Fleiss' κ or the ordinal-weighted analysis. Neither statistic establishes construct validity or clinical effectiveness.

## LMIC–TR Spearman association

The primary study-level analysis uses the canonical LMIC extraction and evidence-coded TR score. Tied values receive average ranks. Two-sided permutation tests and paired paper-level percentile bootstrap intervals use 10,000 iterations and seed 42.

| Cohort / score source | n | Spearman ρ | Permutation p | Bootstrap 95% CI |
|---|---:|---:|---:|---:|
| All eligible studies, canonical scores | 45 | 0.374 | 0.0114 | [0.096, 0.586] |
| Strict primary-SR sensitivity | 24 | 0.578 | 0.0029 | [0.239, 0.794] |
| Pure SR or SR + denoising sensitivity | 22 | 0.654 | 0.0012 | [0.340, 0.842] |
| All eligible studies, median of 11 author ratings | 45 | −0.328 | 0.0297 | [−0.601, −0.024] |

The author-median estimate is a score-source sensitivity, not a replacement for the canonical analysis. Its direction differs from the canonical estimate, so the association is sensitive to scoring source and must not be described as robust across scoring methods or as causal evidence. Alternative TR weighting schemes test sensitivity to criterion weights, not to variability among raters.

## TR weighting sensitivity

Three alternative schemes produce mean TR scores of 1.35, 1.18, and 1.33, versus 1.20 under equal weights. Their study-score rank correlations with the equal-weight score range from 0.942 to 1.000; the 2:2:2:1:2 scheme is numerically identical to equal weights because Hardware Awareness is 0/45. LMIC–TR correlations remain positive but vary from 0.312 to 0.386. This is a criterion-weight sensitivity analysis, not evidence that the LMIC–TR association is robust to scoring source or that the rubric is validated.

## Dataset and metric characterization

General descriptive field-strength categories use explicit numeric values only: ultra-low `<0.05 T`, low-field `0.05-0.5 T`, intermediate `>0.5-<1.5 T`, standard `1.5-3 T`, and high-field `>3 T`. Generic labels such as “low-field” without a reported tesla value remain in a separate threshold-unspecified category; studies spanning numeric bins are classified as mixed. The input and target fields are characterized separately in the dataset evidence table. This descriptive taxonomy is distinct from the TR low-field criterion of `<=64 mT` and from the separate binary indicator for whether an article mentions low-field MRI.

PSNR and SSIM are summarized descriptively because acquisition pathways and reference construction differ across studies. In the final 45-study corpus, 18 studies report parseable PSNR, 17 report parseable SSIM, and 19 report at least one metric. Eight of the 19 metric-reporting studies meet the explicit paired/reference evidence rule; 11 do not. Studies with neither metric are not included in that comparison. No pooled performance effect is estimated.

Target-field status is reported as explicitly reported (20), not applicable (14), not reported (6), and not available from the accessible source text (5). These states are not collapsed into a heuristic `Unknown` category. Dataset details and evidence are in `tables/table_dataset_characterization.csv` and `data/dataset_characterization_evidence.csv`.

## Geographic metadata

Country and World Bank income-group summaries use the reconciled multi-source publication-affiliation evidence. Author employment, education, nationality, or name alone is insufficient to assign a publication country. For the final 45-study corpus, first-author affiliation country is available for all 45 studies; income-group counts are HIC 25, UMC 10, LMC 7, and not available 3. Income-group metadata describes institutional geography, not clinical deployment. Corresponding-author country is not treated as resolved unless the article explicitly identifies that author's publication affiliation.
