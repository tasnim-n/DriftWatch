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

The real pilot passes the Phase 3D.6 readiness gate for Phase 3E pilot ML re-evaluation. Phase 3E has not started, and no ML performance metrics are claimed.
