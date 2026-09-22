# DriftWatch Literature Citation Gaps

## Status and rule

This register separates external-literature needs from claims already supported by repository artifacts. No external bibliography has yet been verified for `PAPER_DRAFT.md`, and no author name, title, venue, year, DOI, or URL is supplied here without source retrieval and full-text checking.

- Verified external citations currently usable: **0**
- Fabricated or unverifiable citations found in the draft: **0**
- Structured external source requirements remaining: **11**
- In-text `[CITATION REQUIRED: ...]` markers: **9**
- Reference-list task markers: **11**

The counts differ because the reference list consolidates overlapping in-text needs and includes two evaluation-method topics not asserted as standalone Related Work subsections.

## External sources still required

| Gap ID | Required literature | Claims the source must support | Minimum verification before use |
|---|---|---|---|
| LIT-01 | Foundational browser-extension security and threat models | Security-sensitive roles of extensions, relevant adversaries, privilege boundaries, and established units of analysis | Retrieve full text; verify scope is browser extensions and that the cited passage supports the exact claim |
| LIT-02 | Browser-extension static, dynamic, or hybrid analysis | Established analysis techniques, observable behaviors, semantic depth, scalability, and limitations | Prefer primary peer-reviewed work; record analysis mode, corpus, and limitations |
| LIT-03 | Browser permission models and over-privilege | Permission semantics, host access, over-privilege, warnings, and limits of permission-only analysis | Verify browser/platform and time period; avoid transferring findings across incompatible permission models |
| LIT-04 | Malicious-extension detection datasets and methods | Feature representations, labeling methods, supervised targets, evaluation design, imbalance, and leakage risks | Prefer primary dataset/method papers; verify labels and evaluation unit rather than relying on abstracts |
| LIT-05 | Longitudinal extension evolution and update security | How extension capabilities or security properties change across versions and whether version pairs are analyzed | Confirm longitudinal design and version provenance; do not infer update findings from snapshot studies |
| LIT-06 | Software-update, maintainer-compromise, and supply-chain security | Updates as a security boundary; maintainer, ownership, dependency, build, or release compromise risks | Use primary research or authoritative incident evidence; distinguish motivation from validation of DriftWatch |
| LIT-07 | Differential program analysis and security regression | Syntactic/semantic differencing, change-aware analysis, and security-regression detection guarantees and limitations | Verify that the work analyzes change rather than only current state |
| LIT-08 | Behavioral drift and change detection | Baseline selection, temporal drift, and limitations of relative comparisons | Reconcile terminology across fields; do not equate statistical drift with browser-extension behavior without qualification |
| LIT-09 | Explainable cybersecurity and analyst decision support | Faithful evidence, explanation utility, analyst interpretation, and limits of post-hoc explanations | Verify whether usefulness was evaluated with humans and separate direct evidence from feature attribution |
| LIT-10 | Human-in-the-loop security review, blind review, and agreement | Independent/blind review design, uncertainty handling, agreement statistics, and adjudication limits | Support general methodology only; DriftWatch's numeric agreement results remain project-internal claims |
| LIT-11 | Evaluation under imbalance, temporal shift, and leakage | Instability of small test sets, class imbalance, temporal/group-safe evaluation, calibration, and leakage prevention | Use primary methodological or authoritative statistical sources and match each citation to the exact limitation stated |

## Project-internal claims that do not require external citations

These claims require repository evidence references, not literature citations:

| Claim family | Primary project evidence |
|---|---|
| Corpus size, extension count, label distribution | `artifacts/driftbench/phase3h/dataset_statistics.json` |
| Eligibility counts | `artifacts/driftbench/phase3h5/eligibility_report.json` |
| External-holdout size and restrictions | `artifacts/driftbench/phase3h/external_holdout_manifest.json`; `DATA_GOVERNANCE.md` |
| Frozen deterministic and exploratory-ML results | `artifacts/experiments/phase3e/`; `artifacts/experiments/phase3f/` |
| Human agreement and kappa | `artifacts/human_review/agreement/reviewer01_vs_reviewer02/agreement_summary.json` |
| Two-stage adjudication outcomes | `artifacts/human_review/adjudication/final/human_validation_summary.json`; `stage_a_to_stage_b_comparison.json` |
| Derived quality promotion | `artifacts/human_review/quality_promotion/driftwatch-human-review-quality-promotion-v1/` |
| Gold Set membership and restrictions | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/` |
| Verified environment | `ENVIRONMENT_SNAPSHOT.md`; `requirements-research-lock.txt` |

## Claims that must remain qualified even after citation

External sources may motivate version-aware security review, explain statistical limitations, or position related work. They cannot convert the current evidence into claims of malware-detection accuracy, objective ground truth, representative prevalence, external validation, production safety, or generalization to all browser extensions. Those claims require new governed empirical evidence, not stronger prose or additional citations.

## Completion procedure

For each gap, record the search date, query, screening decision, complete bibliographic metadata, stable identifier, full-text location, exact supported claim, relevant limitations, and any contradictory evidence. Add a source to the paper only after this verification. The operational search and screening process is defined in `LITERATURE_REVIEW_PLAN.md`.
