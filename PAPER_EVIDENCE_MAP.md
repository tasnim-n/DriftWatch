# DriftWatch Paper-to-Artifact Evidence Map

## Purpose

This map links major empirical claims in `PAPER_SUBMISSION.md` to public-safe repository evidence. It excludes private reviewer rationale, private evidence references, and raw adjudication text. Paths identify the authoritative artifact; SHA-256 values identify the exact file where recorded.

## Corpus and governance

| Paper claim | Evidence path | SHA-256 / evidence note |
|---|---|---|
| 76 version-pair transitions, 21 extensions, labels 71 benign / 3 risky / 2 uncertain | `artifacts/driftbench/phase3h/dataset_statistics.json` | `ED5B9C0DD0C775B079A56642148A57F1036DB637062331709CC8CFBDF0281CC2` |
| 64 supervised-training eligible and 12 ineligible | `artifacts/driftbench/phase3h5/eligibility_report.json` | `3839A18380A51273C5ACA019EACD3E9393421EC6634CAEECF15D00E05EB8FB1D` |
| External holdout contains 10 records from 2 extensions and prohibits training/tuning use | `artifacts/driftbench/phase3h/external_holdout_manifest.json` | `6443371438369689DC957CFE4AACB2C3E15A002F988BD8FD4E75573414CDE73A` |
| External holdout excluded from rule/threshold development and Gold Set construction | `DATA_GOVERNANCE.md`; `HUMAN_REVIEW_GOLD_SET_POLICY.md` | Policy documentation; also enforced by Gold Set validation artifact |
| Frozen dataset labels remain separate from later derived human quality metadata | `artifacts/human_review/quality_promotion/driftwatch-human-review-quality-promotion-v1/human_validation_governance_summary.json` | `5796164A87770577515AEAE17527B2165813E01363880C4F6391C90DB999979C` |

## Human review and adjudication

| Paper claim | Evidence path | SHA-256 / evidence note |
|---|---|---|
| Two reviewers received identical 14-case blind sets with zero holdout overlap | `artifacts/human_review/public_validation/agreement_summary_public.json` | `4D6F6193E893B0A0DCEDF681CC74DA201A73FD95FDA5E61DF1A31F9062125D9F` |
| 9 exact agreements, 5 disagreements, 64.29% agreement, unweighted nominal κ = 0.3396226415 | `artifacts/human_review/public_validation/agreement_summary_public.json` | `4D6F6193E893B0A0DCEDF681CC74DA201A73FD95FDA5E61DF1A31F9062125D9F` |
| Five disagreements completed Stage A and Stage B | `artifacts/human_review/public_validation/adjudication_summary_public.json` | `1621346F09FF71055AFE709B5F7545AA5B4F82644AAC2BDE89A31DD497CEDA48` |
| All 5 retained the Stage A label at Stage B | `artifacts/human_review/public_validation/adjudication_summary_public.json` | `1621346F09FF71055AFE709B5F7545AA5B4F82644AAC2BDE89A31DD497CEDA48` |
| Final disagreement outcomes: 4 risky, 1 uncertain, 0 benign | `artifacts/human_review/public_validation/adjudication_summary_public.json` | `1621346F09FF71055AFE709B5F7545AA5B4F82644AAC2BDE89A31DD497CEDA48`; aggregate and final-label fields only |
| Public human-validation lineage, source-hash references, privacy boundary, and Gold Set linkage | `artifacts/human_review/public_validation/human_validation_public_manifest.json` | `583960955FEA321CCDDD9D19C9EDD9758569FB8FCCF9E6193AAAA34B316E5D46` |
| Four definitive risky cases received explicit derived promotion; uncertain and agreement-only cases were not promoted | `artifacts/human_review/quality_promotion/driftwatch-human-review-quality-promotion-v1/human_validation_governance_summary.json` | `5796164A87770577515AEAE17527B2165813E01363880C4F6391C90DB999979C` |

## Governed Gold Set

| Paper claim | Evidence path | SHA-256 / evidence note |
|---|---|---|
| Gold Set version, ID, four-record membership, labels, tiers, and zero holdout overlap | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_manifest.json` | `F83FF5276E26724200123FE0E64160C4397F71F289EC40E680D74086F46A9F60` |
| Gold Set summary and limitations | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_summary.json` | `B186C96B778F008DD8139DDA4AA24C35D613062AF4374213B2497B4AE23225CE` |
| Training, tuning, rule, threshold, weight, feature, model, and hyperparameter use prohibited | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/USAGE_RESTRICTIONS.json` | `909DDD2094248C40710E5FA3739BB06129F9693F0E86F7E98D17F48CDE97AD6D` |
| Gold Set validation passed; no private human text included; frozen rows unchanged | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/validation_report.json` | `3F8770EE243CEC20EE1ABA6798BCDE297C442AA88839F3001F0DA357EC919FFE` |
| Internal deterministic manifest hash | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_manifest.json` | `d1984552f8298c9133f0988fe8e38fe499772ae8f2e20ccea2715730d1c0a7e1` |

Gold Set ID: `GOLD1::367B78340517770D9DB1E5DABE1DCA63399829A5FA5B64756C820F7696EEA0B8`.

## Experimental and qualitative results

| Paper claim | Evidence path | Evidence note |
|---|---|---|
| Phase 3E deterministic/ML held-out results | `artifacts/experiments/phase3e/` | Frozen metrics and error-analysis artifacts; do not rerun or tune |
| Phase 3F replication results and `INCONCLUSIVE` decision | `artifacts/experiments/phase3f/` | Frozen metrics, error analysis, and replication conclusion |
| Four flagship case studies and their interpretation boundaries | `CASE_STUDIES.md` | Derived from frozen review packets, feature table, queues, and experiment artifacts |
| Browserpass 3.11.0 → 3.12.0 content-script field discrepancy | `CASE_STUDIES.md`; Phase 3H full feature row; Phase 3H.5 review packet | Preserved and not resolved by Phase 6 |
| Failure mechanisms and provisional-error boundaries | `FAILURE_ANALYSIS.md` | Synthesizes frozen Phase 3E/3F/3H/3H.5 artifacts plus public-safe human aggregates |

## System, threat model, and reproducibility

| Paper claim | Evidence path | Evidence note |
|---|---|---|
| Operational architecture and research/runtime separation | `ARCHITECTURE.md`; application source and tests | Repository implementation evidence |
| Threat scope, static observability, evasion, and claims boundary | `THREAT_MODEL.md` | DriftWatch prioritizes review; it does not determine intent or certify safety |
| Python 3.14.0 verified environment | `ENVIRONMENT_SNAPSHOT.md` | Snapshot dated 2026-09-21; do not generalize to unverified environments |
| Reproduction and non-regeneration policy | `REPRODUCIBILITY.md` | Frozen artifact generators must not be rerun merely for verification |

## External literature evidence

External sources support background, prior-work positioning, and methodological cautions only. They do not replace the artifact mappings above.

| Paper claim family | Verified citation keys | Evidence boundary |
|---|---|---|
| Extension privilege boundaries and threat models | BARTH2010 [1]; CARLINI2012 [2]; KAPRAVELOS2014 [4] | Establishes architectures, vulnerabilities, and malicious behavior; not DriftWatch performance |
| Static, dynamic, and hybrid extension analysis | BANDHAKAVI2010 [3]; KAPRAVELOS2014 [4]; FASS2021 [5]; WANG2018 [6] | Establishes analysis modes and limitations; not equivalence to DriftWatch features |
| Permissions and review triage | FELT2011 [7]; BARTH2010 [1]; CARLINI2012 [2] | Supports permissions as useful but incomplete evidence; platform/time boundaries retained |
| Malicious-extension detection | KAPRAVELOS2014 [4]; WANG2018 [6]; JAGPAL2015 [8] | Contextualizes detection targets; no metric transfer to DriftWatch |
| Longitudinal extension update deltas | PANTELAIOS2020 [9] | Nearest work; prevents a “first update-delta system” claim |
| Supply-chain provenance and version ordering | TORRESARIAS2019 [10]; KUPPUSAMY2017 [11] | General update-security motivation; no attribution of compromise to a DriftBench case |
| Differential program analysis | JACKSON1994 [12]; PERSON2008 [13] | Supports change-aware analysis concepts; no security-regression guarantee for DriftWatch |
| Concept-drift terminology | GAMA2014 [14] | Used to distinguish statistical concept drift from static extension-version differences |
| Explainability and analyst decision support | PHILLIPS2021 [15]; ALAHMADI2022 [16]; CRANOR2008 [17] | Supports explanation/human-task principles; no measured DriftWatch utility claim |
| Nominal agreement and kappa limits | COHEN1960 [18]; FEINSTEIN1990 [19] | Supports coefficient definition and marginal-imbalance caveat; agreement remains non-accuracy |
| Imbalance, model-selection bias, and leakage | HE2009 [20]; VARMA2006 [21]; KAPOOR2023 [22] | Supports evaluation cautions; DriftWatch results remain project-artifact claims |

Complete metadata, verification notes, and limitations are in `LITERATURE_VERIFIED_SOURCES.md`. Screening exclusions are in `LITERATURE_REJECTED_SOURCES.md`.

## Claims with no current supporting empirical artifact

No artifact currently supports claims of malware-detection accuracy, sensitivity, specificity, population false-positive or false-negative rates, representative prevalence, external validation, production safety, objective ground truth, or generalization to all browser extensions. The paper must continue to exclude or explicitly qualify those claims.
