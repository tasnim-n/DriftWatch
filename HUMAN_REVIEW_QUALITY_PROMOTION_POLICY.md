# Human-Review Quality-Tier Promotion Policy

## Policy identity and scope

- Policy version: `driftwatch-human-review-quality-promotion-v1`
- Applies to: explicit derived quality-tier decisions following a completed, validated human-adjudication workflow
- Initial governed scope: the five Phase 5F final adjudication records

This policy records a quality assessment and promotion in a versioned derived layer. It does not rewrite frozen dataset history, determine malware probability, authorize tuning, or create a Gold Set.

## Separate governance action

Adjudication completion establishes a final human review outcome but does not automatically change label-quality metadata. Promotion requires a separate, explicit, versioned decision so that the original frozen row, the adjudicated semantic label, and the promoted quality tier remain distinguishable and auditable.

## Required provenance and integrity

A promotion must fail closed unless all of the following are present and valid:

- immutable Reviewer 01 and Reviewer 02 source hashes and review identifiers;
- the governed disagreement-selection record;
- a complete and validated Stage A record;
- a complete and validated Stage B record linked to Stage A;
- a final resolution with `ADJUDICATION_COMPLETE` status;
- the Phase 5F eligibility assessment;
- complete old/new release hashes and frozen-row provenance;
- a valid canonical target tier; and
- zero external-holdout overlap.

Source artifacts and human wording must not be altered. A derived manifest may reference private sources by identifier and hash but must not copy rationale text into a public-safe output.

## Qualifying labels and tier

This policy does not redefine the canonical tiers in `driftbench/label_quality.py`. A definitive semantic label that completed the governed multi-reviewer adjudication workflow may be promoted to the existing `MULTI_REVIEWER_ADJUDICATED` tier when all integrity conditions pass.

`UNCERTAIN`, `NEEDS_REVIEW`, and `EXCLUDED` are non-definitive outcomes and must not be promoted to `MULTI_REVIEWER_ADJUDICATED`. An adjudicated `UNCERTAIN` outcome remains a valid completed review with strong provenance and retains the canonical `UNCERTAIN` quality assessment.

Agreement between two reviewers without governed adjudication is not sufficient. This policy creates no `MULTI_REVIEWER_AGREED` tier and does not promote agreement-only records.

## Frozen-data immutability

Promotion must be expressed only through a versioned derived manifest or view. The original dataset label, quality tier, review status, eligibility decision, and provenance remain frozen. The derived view must identify both the frozen values and the later governed values and must never imply that the frozen row originally contained the promoted tier.

## External holdout exclusion

An external-holdout record cannot be promoted under this policy. External holdout remains prohibited from training, tuning, threshold selection, rule development, and Gold Set construction.

## No tuning or scoring consequence

A promotion does not authorize changes to analyzers, features, scoring logic, weights, thresholds, rules, review selection, ML experiments, or evaluation artifacts. Quality-tier metadata must not become a predictive feature.

## Gold Set separation

Promotion may make a record ready for a later Gold Set decision, but it does not create or modify a Gold Set. Gold Set construction requires separate authorization, revalidation of canonical policy, complete provenance, qualifying semantics, and renewed external-holdout exclusion checks.

## Audit, supersession, and rollback

Each promotion decision must include a deterministic decision identifier, decision timestamp, policy version, source hashes, per-record reasons, and an explicit statement that frozen data and Gold Set artifacts were not modified. Outputs are immutable once recorded.

If a decision is later found invalid, do not edit or delete the historical record. Issue a new versioned superseding decision that references the prior manifest hash, states the reason, and marks the earlier decision superseded. Consumers must use the latest valid non-superseded decision while preserving the full audit trail.
