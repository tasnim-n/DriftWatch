# DriftBench Data Governance

## Source Policy
DriftBench Phase 3D accepts only lawfully acquired local material with explicit provenance. Supported source categories are:

- `real_public`
- `research_dataset`
- `open_source_repository`
- `controlled`
- `unknown/unverified`

`unknown/unverified` sources are quarantined or excluded and must not automatically enter a research-ready dataset.

## Acquisition And Replay
Core reproducibility must not depend on a live website remaining available. Phase 3D separates acquisition from curation and feature extraction. The current implementation supports local import manifests:

```powershell
.venv\Scripts\python.exe -m driftbench.ingest --manifest datasets\manifests\import_manifest.example.json --dry-run
```

The example manifest is a template only. It is not evidence of real data.

Phase 3D.5 and Phase 3D.6 used normal public HTTPS downloads from GitHub release assets for the real pilot corpus. Downloaded raw packages are stored under `datasets/incoming/real_pilot/`; normalized static-analysis packages are stored under `datasets/validated/real_pilot_packages/`.

## Licensing And Redistribution
Each record stores license metadata, license status, research-use status, redistribution status, and attribution requirement. Records with unknown or disallowed licensing are quarantined or excluded. DriftWatch records licensing evidence; it does not provide legal guarantees.

## Provenance
Accepted records must preserve source reference, acquisition timestamp, package identifiers, old/new versions, SHA-256 hashes, label provenance, review status, and evidence references. Missing metadata is represented honestly as null/unknown and may block acceptance.

## Label Policy
Labels are evidence categories, not DriftWatch score outputs. DriftWatch's final risk score must never be used as ground truth. Supported curation labels include benign, risky, malicious transition, uncertain, controlled malicious, needs review, and excluded states.

Phase 3D.6 adds label quality tiers: `CONTROLLED_GROUND_TRUTH`, `EXTERNAL_CONFIRMED`, `MULTI_REVIEWER_ADJUDICATED`, `SINGLE_REVIEWER_PROVISIONAL`, and `UNCERTAIN`. These tiers are dataset-quality metadata only and must not be used as predictive model features. Records marked `uncertain`, `needs_review`, or `excluded` are not eligible for supervised training.

## Real Versus Controlled Data
Controlled laboratory samples remain explicitly separate from real records. The Phase 3D.6 real pilot contains 34 real records. Existing controlled Phase 3B artifacts remain controlled-only and must not be used to claim population prevalence.

## Exclusions
Records may be excluded or quarantined for unclear source rights, missing provenance, package corruption, missing manifest, ambiguous extension identity, indefensible version ordering, duplicate leakage, unresolved label uncertainty, or split leakage.

## Prohibited Uses
Do not use DriftBench to claim Chrome Web Store prevalence, malicious-extension prevalence, model accuracy, false-positive rate, or representativeness unless those claims are supported by curated data and validated experiments.

## Security Boundary
Imported packages are hostile files. DriftWatch parses archives and JavaScript statically. It must never install extensions, execute extension JavaScript, execute decoded content, launch unknown binaries, or contact embedded network endpoints.

## Current Real Pilot Governance State
- Dataset version: `0.1.0-real-pilot`
- Real records accepted: 34
- Unique real extensions: 11
- Source type: `open_source_repository=34`
- License identifiers: `Apache-2.0=4`, `GPL-3.0=13`, `MIT=17`
- Label states: `benign_transition=29`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=32`, `UNCERTAIN=2`
- Eligible supervised-training records: 32
- Split distribution: `train=16`, `validation=12`, `test=6`
- Leakage audit: passed with 0 protected split violations
- Provenance completeness: 34/34
- Review queue: two original `uncertain` Save Sora transitions remain unresolved and ineligible

The real pilot passed the Phase 3D.6 readiness gate for Phase 3E pilot ML re-evaluation. Phase 3E and Phase 3F have since produced research-only evaluation artifacts; those results remain preliminary and do not justify production ML integration.

## Current Phase 3F Replication Governance State
- Dataset version: `driftbench-real-replication-phase3f-v1`
- Real records accepted: 46
- New independent replication records: 12
- Unique extension identities: 14
- Source type: public open-source GitHub release assets
- License identifiers: `Apache-2.0=4`, `GPL-3.0=16`, `ISC=4`, `MIT=22`
- Label states: `benign_transition=41`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=44`, `UNCERTAIN=2`
- Split distribution: `train=24`, `validation=12`, `test=10`
- Duplicate audit: passed
- Protected group/package-hash leakage audit: passed
- Feature leakage audit: passed
- Provenance completeness: 46/46
- Double-reviewed records: 0
- Inter-rater agreement: not available

Phase 3F preserves Phase 3E as `PILOT_BASELINE` and writes separate replication artifacts under `artifacts/driftbench/phase3f/`, `artifacts/driftbench/phase3f_features/`, and `artifacts/experiments/phase3f/`.

Rejected or unsuitable candidate packages must remain excluded when they fail DriftWatch security limits, licensing checks, provenance checks, or accepted-source criteria. Security controls must not be weakened to force a candidate into the corpus.

Phase 3F conclusion is `INCONCLUSIVE`; the evidence-based decision gate is `CONTINUE DATASET EXPANSION`.

## Current Phase 3G Maturation Governance State
- Dataset version: `driftbench-real-maturation-phase3g-v1`
- Previous dataset version: `driftbench-real-replication-phase3f-v1`
- Real records accepted: 58
- New Phase 3G records accepted: 12
- Unique extension identities: 17
- Source type: public open-source GitHub release assets
- License identifiers: `Apache-2.0=4`, `GPL-3.0=24`, `ISC=4`, `MIT=26`
- Label states: `benign_transition=53`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=56`, `UNCERTAIN=2`
- Training-eligible records: 56
- Split distribution: `train=32`, `validation=16`, `test=10`
- Provenance completeness: 58/58
- Timestamp completeness: 58/58
- Duplicate audit: passed
- Protected group/package-hash leakage audit: passed
- Feature leakage audit: passed
- Double-reviewed records: 0
- Inter-rater agreement: not available

Phase 3G adds accepted records for Automa, LibRedirect, and Web Scrobbler. uBlacklist candidate assets were excluded after triggering DriftWatch extraction safety controls; this is an archive-safety decision and must not be represented as a maliciousness finding.

The two original Save Sora `uncertain` records remain unresolved and ineligible for supervised training. Phase 3G creates refreshed review packets and a second-review priority queue without inventing reviewers, reviewer agreement, or adjudicated labels.

Phase 3G decision: `DATASET STILL TOO WEAK - CONTINUE EXPANSION`.

## Current Phase 3H Holdout Governance State
- Dataset version: `driftbench-real-adjudication-holdout-phase3h-v1`
- Parent dataset version: `driftbench-real-maturation-phase3g-v1`
- Real records accepted: 76
- New Phase 3H records accepted: 18
- Unique extension identities: 21
- Source family: `public_github_release_assets=76`
- Label states: `benign_transition=71`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=74`, `UNCERTAIN=2`
- Gold Set size: 0
- External replication holdout size: 10
- Double-reviewed records: 0
- Adjudicated records: 0
- Inter-rater agreement: not available
- Provenance completeness: 76/76
- Timestamp completeness: 76/76
- Duplicate and leakage audits: passed

The Phase 3H holdout is locked for future validation and must not be used for threshold tuning, rule tuning, model selection, or hyperparameter selection. A genuine Gold Set could not be created because no real record currently has external confirmation or multi-reviewer adjudication.

Phase 3H decision: `CONTINUE INDEPENDENT LABEL REVIEW / ADJUDICATION`.
