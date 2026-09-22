# Human-Review Gold Set Policy

## Policy identity and purpose

- Policy version: `driftwatch-human-gold-set-v1`
- Canonical methodology: `phase3h5-gold-set-methodology-v1`
- Applies to: construction of a versioned, derived high-quality human-validation subset

The DriftWatch Gold Set supports research reporting, qualitative case analysis, reproducibility, audit, and future evaluation under a separately approved protocol. It is not malware ground truth, a safety certification, representative prevalence evidence, training authorization, or permission to tune DriftWatch.

## Canonical qualification rules

This policy does not redefine the canonical quality tiers. The unchanged Phase 3H.5 builder accepts only `EXTERNAL_CONFIRMED`, genuine `MULTI_REVIEWER_ADJUDICATED`, or explicitly separated `CONTROLLED_GROUND_TRUTH` records. It excludes semantic labels `uncertain` and `excluded` and requires complete old/new release hashes.

For the initial human-review Gold Set, a record must additionally have:

- a completed and hash-linked Reviewer 01 and Reviewer 02 provenance chain;
- governed disagreement selection;
- completed and validated Stage A and Stage B adjudication;
- a Phase 5F final resolution with `ADJUDICATION_COMPLETE` status;
- an explicit Phase 5G `APPROVED` promotion to `MULTI_REVIEWER_ADJUDICATED`;
- a qualifying definitive semantic label;
- an immutable frozen-row linkage and complete provenance identifier;
- zero external-holdout overlap; and
- a unique record identifier within the candidate set.

Missing provenance, duplicate identifiers, unexpected membership, or conflicting fields cause construction to fail closed.

## Required exclusions

`UNCERTAIN`, `NEEDS_REVIEW`, and `EXCLUDED` semantic outcomes are not Gold Set labels. Their exclusion does not invalidate or erase completed human review.

Agreement-only cases without a qualifying canonical quality-tier promotion are excluded. This policy creates no `MULTI_REVIEWER_AGREED` tier and does not reinterpret agreement as adjudication.

External-holdout records are unconditionally excluded. The Gold Set must never contain or replace the protected external holdout.

## Immutability and relationship to frozen data

Gold Set membership exists only in a new versioned derived artifact. Frozen dataset rows, semantic labels, quality fields, eligibility decisions, splits, and provenance must remain unchanged. The Gold Set must explicitly reference the frozen row and later adjudication and promotion layers; it must never imply that a frozen row originally contained the adjudicated label or promoted tier.

Raw reviews, human rationale, adjudication submissions, private reviewer mappings, and Stage A/B packages remain immutable and private. Public-safe Gold Set artifacts use identifiers and hashes instead of human-written rationale.

## Usage restrictions

Allowed uses are limited to:

- research reporting;
- qualitative case analysis;
- reproducibility and audit; and
- future evaluation under a separately approved protocol.

Without separate governed authorization, the Gold Set must not be used for training, fine-tuning, threshold selection, scoring-weight tuning, rule development, feature selection, model selection, hyperparameter tuning, or any activity that contaminates the external holdout.

## Versioning and membership governance

The first version is `driftwatch-human-gold-set-v1`. Membership is mechanically derived from the applicable canonical policy and the validated promotion layer. Additions and removals require a separately versioned governance decision, complete revalidation, a new manifest hash, and preserved lineage to the preceding version.

Published versions are immutable. If an error is discovered, issue a superseding version that identifies the prior manifest hash and reason. Never rewrite or delete the historical manifest.

## Limitations and interpretation

The initial set is small and intentionally scoped. Its label distribution does not represent the browser-extension population. A `RISKY_TRANSITION` means the update warrants elevated manual security-review attention; it does not establish maliciousness. Gold Set membership does not establish model accuracy, sensitivity, specificity, external validation, or population-level performance.
