# DriftWatch Architecture Figure Evidence Map

## Scope

This map traces every substantive component in `figures/driftwatch_architecture.svg` to public repository evidence. The figure summarizes implemented runtime behavior and completed research governance; it does not expose private human rationale or imply malware classification, automatic approval, objective ground truth, Gold Set training, or completed external validation.

## Runtime analysis pipeline

| Figure component | Implementation/documentation evidence | Supported statement and boundary |
|---|---|---|
| Previous and updated Chromium extension packages | `app/api/routes.py`; `app/services/analysis_service.py`; `app/schemas/analysis.py` | The application accepts an ordered pair of supplied extension archives. Neither package is presumed safe. |
| Secure extraction sandbox | `app/core/security.py`; `app/services/analysis_service.py`; `SECURITY.md` | Archive size, extracted size, compression ratio, entry count, path traversal, and link protections are enforced before analysis. |
| Static evidence analyzers | `analyzers/manifest_analyzer.py`; `analyzers/permission_analyzer.py`; `analyzers/host_scope_analyzer.py`; `analyzers/api_analyzer.py`; `analyzers/network_analyzer.py`; `analyzers/obfuscation_analyzer.py`; `analyzers/package_analyzer.py`; `analyzers/structure_analyzer.py` | Implemented analyzers cover manifest/permissions, host scope, APIs, static network indicators, obfuscation/dynamic-code indicators, package structure, and same-file source/sink heuristics. Extension JavaScript is not executed. |
| Version evidence | `analyzers/drift_engine.py`; `ARCHITECTURE.md` | DriftWatch constructs evidence for the previous and updated versions before expressing their change. |
| Differential feature computation | `analyzers/drift_engine.py`; `driftbench/features.py`; `PAPER_SUBMISSION.md` Sections 9–10 | Set, count, Boolean, ordinal, and structural changes represent the version transition. The subtraction notation is conceptual and feature-specific. |
| Deterministic risk prioritization | `risk_engine/scoring.py`; `risk_engine/rules.py`; `ARCHITECTURE.md`; `THREAT_MODEL.md` | Fixed contributions and rules produce security-review priority. The score is not malware probability and does not automatically approve or reject an extension. |
| Explanation and evidence cards | `risk_engine/explanations.py`; `app/templates/report.html`; `app/api/routes.py` | Reports expose evidence, V1/V2 context, cautions, score contributions, and reviewer actions. Static evidence does not prove runtime occurrence or intent. |
| Manual security review | `app/templates/report.html`; `THREAT_MODEL.md`; `RELEASE_NOTES.md` | The operational endpoint is analyst review, not a malware decision or safety certification. |

## Research validation and governance pipeline

| Figure component | Public evidence | Supported statement and boundary |
|---|---|---|
| Frozen DriftBench corpus | `artifacts/driftbench/phase3h/dataset_statistics.json`; `DATASET_CARD.md` | The frozen Phase 3H corpus contains 76 version transitions from 21 extensions. Later human-review metadata does not rewrite these rows. |
| Eligibility and provenance controls | `artifacts/driftbench/phase3h5/eligibility_report.json`; `DATA_GOVERNANCE.md` | Sixty-four records are eligible and 12 are ineligible after uncertainty, review-quality, and holdout restrictions. Eligibility is metadata, not a predictive feature. |
| Protected external holdout | `artifacts/driftbench/phase3h/external_holdout_manifest.json`; `DATA_GOVERNANCE.md`; `HUMAN_REVIEW_GOLD_SET_POLICY.md` | Ten records from two extensions are isolated from training, tuning, threshold selection, rule development, feature redesign, outcome-driven development, and Gold Set construction. No completed external-validation claim is made. |
| Independent blind review | `artifacts/human_review/public_validation/agreement_summary_public.json`; `HUMAN_REVIEW_DERIVATION_POLICY.md` | Two independent reviewers received the same 14-case non-holdout set with predictive labels and outputs hidden. Private submissions and rationale remain outside the public figure evidence. |
| Inter-rater agreement | `artifacts/human_review/public_validation/agreement_summary_public.json` | Nine cases agreed and five disagreed; exact agreement was 64.29% and nominal unweighted Cohen's kappa was 0.3396226415. These are descriptive agreement measures, not accuracy. |
| Governed two-stage adjudication | `artifacts/human_review/public_validation/adjudication_summary_public.json`; `HUMAN_REVIEW_ADJUDICATION_POLICY.md` | Five disagreements completed Stage A before prior-opinion exposure and Stage B after de-identified opinions; zero labels changed between stages. |
| Derived quality promotion | `artifacts/human_review/quality_promotion/driftwatch-human-review-quality-promotion-v1/human_validation_governance_summary.json`; `HUMAN_REVIEW_QUALITY_PROMOTION_POLICY.md` | Four definitive risky outcomes received separately versioned `MULTI_REVIEWER_ADJUDICATED` quality. Frozen dataset labels were not overwritten. |
| Governed Gold Set | `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_manifest.json`; `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/USAGE_RESTRICTIONS.json`; `HUMAN_REVIEW_GOLD_SET_POLICY.md` | The Gold Set contains four `RISKY_TRANSITION` records, all `MULTI_REVIEWER_ADJUDICATED`, with zero holdout overlap. It is small, single-class, and not authorized for training or tuning. |
| Runtime/research separation | `ARCHITECTURE.md`; `REPRODUCIBILITY.md`; `THREAT_MODEL.md` | Research labels, ML outputs, human-review outcomes, promotion metadata, holdout decisions, and Gold Set membership do not feed operational scoring. |

## Figure files

- Vector source and primary publication asset: `figures/driftwatch_architecture.svg`
- Raster fallback: `figures/driftwatch_architecture.png`

The SVG is the authoritative figure source. The PNG must be rendered from that SVG without altering labels, counts, arrows, or claim boundaries.
