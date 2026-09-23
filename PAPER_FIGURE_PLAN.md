# DriftWatch Publication Figure Plan

## Purpose

Create one publication architecture figure with two visually separated panels: the runtime analysis pipeline and the research-validation/governance pipeline. The figure must make clear that research labels, human-review outcomes, promotion metadata, the external holdout, and the Gold Set do not feed the runtime score.

No final graphic is generated in Phase 8A because the repository has no governed figure-generation workflow or selected venue template.

## Panel A: Runtime analysis pipeline

Use the following exact node labels and flow:

```text
Previous Chromium extension archive (V_{t-1}) --\
                                                   > Secure extraction sandbox
Updated Chromium extension archive (V_t) --------/
    -> Static analyzers
       [Manifest and permissions | Host scope | Sensitive APIs |
        Network indicators | Obfuscation | Package/structure]
    -> Version evidence: F(V_{t-1}) and F(V_t)
    -> Differential features: D_t = F(V_t) - F(V_{t-1})
    -> Deterministic risk prioritization
       [Review-priority score; not malware probability]
    -> Explanation and evidence cards
    -> Human security review
```

Show a shield or bounded-container motif around `Secure extraction sandbox` and `Static analyzers`. Do not depict JavaScript execution, endpoint contact, automatic blocking, malware classification, or production approval.

Runtime implementation sources:

- `app/`
- `analyzers/`
- `risk_engine/`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `THREAT_MODEL.md`

## Panel B: Research validation and governance

Use the following exact node labels and flow:

```text
Frozen DriftBench corpus
[76 transitions; 21 extensions]
    -> Eligibility and provenance controls
    -> Protected external holdout
       [10 records; 2 extensions; no training/tuning/rule development]

Non-holdout scoped review set
[14 blind cases; identical case sets]
    -> Independent Reviewer 1 + Independent Reviewer 2
    -> Agreement analysis
       [9 agreement; 5 disagreement; 64.29%; nominal unweighted kappa 0.3396]
    -> Two-stage adjudication of 5 disagreements
       [Stage A -> de-identified prior opinions -> Stage B; 0 label changes]
    -> Derived quality promotion
       [4 definitive risky cases promoted]
    -> Governed Gold Set
       [4 RISKY_TRANSITION; MULTI_REVIEWER_ADJUDICATED;
        zero holdout overlap; prohibited from training/tuning]
```

The holdout branch must remain visibly isolated from review selection, promotion, and Gold Set construction. Use a dashed boundary labeled `Research-only governance; no runtime scoring input` between Panel B and Panel A.

Research evidence sources:

- `artifacts/driftbench/phase3h/dataset_statistics.json`
- `artifacts/driftbench/phase3h/external_holdout_manifest.json`
- `artifacts/driftbench/phase3h5/eligibility_report.json`
- `artifacts/human_review/public_validation/agreement_summary_public.json`
- `artifacts/human_review/public_validation/adjudication_summary_public.json`
- `artifacts/human_review/public_validation/human_validation_public_manifest.json`
- `artifacts/human_review/quality_promotion/driftwatch-human-review-quality-promotion-v1/human_validation_governance_summary.json`
- `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_manifest.json`
- `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/USAGE_RESTRICTIONS.json`
- `DATA_GOVERNANCE.md`
- `HUMAN_REVIEW_GOLD_SET_POLICY.md`

## Visual encoding and caption constraints

- Use solid arrows only for actual data/control flow and dashed arrows for traceability references.
- Use one color family for runtime processing and a second for research governance.
- Mark the external holdout with a lock and the Gold Set with a separate governed-container boundary.
- Label human decisions as review outcomes, never ground-truth maliciousness determinations.
- Keep counts in annotations, not oversized headline graphics.
- Define every abbreviation in the caption.

Suggested caption: `DriftWatch separates secure, static, differential runtime analysis from offline research governance. Runtime evidence supports manual review prioritization; protected holdout, independent review, adjudication, derived promotion, and the governed Gold Set remain outside operational scoring.`
