# DriftWatch Paper-to-Artifact Evidence Map

## Purpose

This map links major empirical claims in `PAPER_DRAFT.md` to public-safe repository evidence. It excludes private reviewer rationale, private evidence references, and raw adjudication text. Paths identify the authoritative artifact; SHA-256 values identify the exact file where recorded.

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
| Two reviewers received identical 14-case blind sets with zero holdout overlap | `artifacts/human_review/agreement/reviewer01_vs_reviewer02/agreement_summary.json` | `369FFA3352E11542574618EBEECD3095271DA7DCDA4029E79C0231C3C5D10089` |
| 9 exact agreements, 5 disagreements, 64.29% agreement, unweighted nominal κ = 0.3396226415 | `artifacts/human_review/agreement/reviewer01_vs_reviewer02/agreement_summary.json` | `369FFA3352E11542574618EBEECD3095271DA7DCDA4029E79C0231C3C5D10089` |
| Five disagreements completed Stage A and Stage B | `artifacts/human_review/adjudication/final/human_validation_summary.json` | `076ED1350680853540184CC22208CA53ACCE548D0C4ED241EF1714AD8C8354B2` |
| All 5 retained the Stage A label at Stage B | `artifacts/human_review/adjudication/final/stage_a_to_stage_b_comparison.json` | `A94A77E84E5596F95CA3FCC5C5EEC1A008CDA53DB749CC28A801AC578B548D8E` |
| Final disagreement outcomes: 4 risky, 1 uncertain, 0 benign | `artifacts/human_review/adjudication/final/human_validation_summary.json` | Aggregate only; no private rationale required |
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

## Claims with no current supporting empirical artifact

No artifact currently supports claims of malware-detection accuracy, sensitivity, specificity, population false-positive or false-negative rates, representative prevalence, external validation, production safety, objective ground truth, or generalization to all browser extensions. The paper must continue to exclude or explicitly qualify those claims.
