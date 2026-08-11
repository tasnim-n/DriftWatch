# DriftWatch Phase 3H.5 Reviewer Guide

## Purpose
Phase 3H.5 review strengthens DriftBench ground truth. Reviewers assess browser-extension version pairs from evidence packets, not from DriftWatch scores or model predictions.

## Label Definitions
- `BENIGN_TRANSITION`: security-sensitive changes have a documented legitimate purpose and no independent evidence supports harmful intent or unacceptable security behavior.
- `RISKY_TRANSITION`: the update introduces meaningful security-sensitive capability or behavior that warrants security review, even without proof of malicious intent.
- `MALICIOUS_TRANSITION`: strong independent evidence shows the update introduced or enabled intentionally harmful behavior.
- `UNCERTAIN`: available evidence is insufficient or contradictory.
- `EXCLUDED`: the record is methodologically unsuitable because of provenance, identity, corruption, licensing, duplication, or similar quality problems.

## Evidence Hierarchy
- Tier 1: peer-reviewed dataset or verified public security disclosure.
- Tier 2: multiple reputable independent security reports.
- Tier 3: maintainer or vendor disclosure with corroborating evidence.
- Tier 4: repository history, release notes, package metadata, or commit evidence.
- Tier 5: single-reviewer technical assessment.
- Tier 6: weak, incomplete, or contradictory evidence.

DriftWatch output is never external evidence.

## How To Review A Version Pair
1. Open the assigned packet under `artifacts/driftbench/phase3h5/review_packets/`.
2. Inspect provenance, version timestamps, release evidence, manifest diff, permissions, host scope, APIs, network indicators, obfuscation, structure, and source-to-sink evidence.
3. Record a label, confidence, rationale, evidence references, reviewer id, round, and timestamp using the schema in `datasets/reviews/phase3h5/review_submission_schema.json`.
4. Choose `UNCERTAIN` when the evidence does not justify a stronger label.

## Risky Versus Malicious
Risky means security review is warranted. Malicious means independent evidence supports intentional harm. Do not label a transition malicious just because permissions increased, `<all_urls>` appeared, code is minified, sensitive APIs were added, or a heuristic source-to-sink indicator fired.

## Confidence
- `HIGH`: strong independent evidence and a clear version transition.
- `MEDIUM`: reasonable evidence but some ambiguity remains.
- `LOW`: insufficient, indirect, or incomplete evidence.

Confidence is not malware probability.

## Blind Review
Initial review packets hide DriftWatch numeric output, severity, rule recommendations, ML outputs, previous model outputs, and current provisional dataset labels. Do not search for those values before completing the independent label.

## Prohibited Ground-Truth Sources
Do not use DriftWatch score, DriftWatch severity, rule recommendations, model predictions, reviewer identity, or gold-set flags as ground truth.

## Adjudication
If two genuine reviewers disagree, preserve both original reviews. An adjudicator may assign `BENIGN_TRANSITION`, `RISKY_TRANSITION`, `MALICIOUS_TRANSITION`, `UNCERTAIN`, or `EXCLUDED`, with rationale and evidence references. If evidence remains insufficient, `UNCERTAIN` is valid.
