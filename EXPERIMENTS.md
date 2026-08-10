# DriftWatch Experiment Log

## Phase 3C Pilot - 2026-08-10

This pilot verifies the empirical-evaluation pipeline against the current Phase 3B controlled artifacts. It is not a real-world performance study.

Input artifacts:
- `artifacts/driftbench/`
- 2 records
- 2 unique extensions
- Labels: `benign_transition=1`, `risky_transition=1`
- Splits: `controlled_holdout=2`
- Controlled records: 2
- Real records: 0

Output artifacts:
- `artifacts/experiments/dataset_readiness.json`
- `artifacts/experiments/leakage_audit.json`
- `artifacts/experiments/baseline_comparison.csv`
- `artifacts/experiments/confusion_matrices/*.json`
- `artifacts/experiments/predictions/*.jsonl`
- `artifacts/experiments/error_analysis.json`
- `artifacts/experiments/ablation_results.csv`
- `artifacts/experiments/chronological_results.csv`
- `artifacts/experiments/model_comparison.csv`
- `artifacts/experiments/experiment_manifest.json`

Readiness gate:
- Status: blocked for ML training.
- Reasons: fewer than 20 records; no train/test split assignments; all records are controlled/synthetic.

Leakage audit:
- Status: passed.
- Feature columns audited: 43.
- Violations: 0.
- Extension group split safety: passed.

Deterministic pilot baseline results:

| Baseline | Records | Precision | Recall | F1 | Balanced Accuracy | FPR | FNR | False Alerts / 100 Benign |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| permission_only | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| manifest_permission | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| latest_version_static | 2 | 0.5 | 1.0 | 0.666667 | 0.5 | 1.0 | 0.0 | 100.0 |
| simple_differential | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| full_driftwatch | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |

Interpretation:
- These numbers only confirm that the evaluation code can load artifacts, apply deterministic pilot rules, and write reproducible outputs.
- They are not ML metrics.
- They are not generalizable detection-performance claims.
- Logistic Regression, Random Forest, ROC-AUC, PR-AUC, chronological evaluation, and ablation are blocked until DriftBench contains enough real, leakage-safe records.

## Phase 3D Intake Manifests - 2026-08-10

Phase 3D generated research-curation manifests for the current repository state.

Artifact location:
- `artifacts/driftbench/phase3d/`

Current intake results:
- DriftBench version: `0.1.0`
- Imported records: 0
- Accepted records: 0
- Quarantined records: 0
- Excluded records: 0
- Real records accepted: 0
- Controlled records imported through Phase 3D intake: 0

Interpretation:
- At Phase 3D time, no lawfully usable real extension corpus was present in the repository.
- No real records were fabricated in Phase 3D.
- Phase 3D.5 later added the small real pilot corpus described below.
- ML retraining remains deferred.

## Phase 3D.5 Real Pilot Corpus - 2026-08-10

Phase 3D.5 acquired and curated a small real open-source browser-extension pilot corpus.

Artifacts:
- `datasets/manifests/real_pilot_import_manifest.json`
- `artifacts/driftbench/real_pilot/`
- `artifacts/driftbench/real_pilot_features/`
- `artifacts/driftbench/real_pilot_readiness.json`

Actual results:
- Real records: 10
- Unique real extensions: 5
- Controlled records in Phase 3D.5: 0
- Label distribution: `benign_transition=6`, `risky_transition=2`, `uncertain=2`
- License identifiers: `MIT=9`, `GPL-3.0=1`
- Duplicate report: passed; 5 adjacent-version reuses tracked as expected longitudinal chain reuse.
- Leakage report: passed with 0 violations.
- Feature extraction: completed for all 10 records across all five Phase 3B representations.

Interpretation:
- This is a pilot curation corpus only.
- No ML retraining occurred.
- No accuracy, FPR, FNR, ROC-AUC, PR-AUC, or production detection metric is claimed.
- Phase 3E ML re-evaluation remains blocked by sample size, small test split, uncertain labels, and provisional label review.

## Phase 3D.6 Real Corpus Expansion - 2026-08-10

Phase 3D.6 expanded the real pilot corpus, added label-quality tiers, generated review packets for unresolved labels, stabilized group-safe splits, and regenerated Phase 3B feature artifacts. It did not train ML models.

Artifacts:
- `datasets/manifests/real_pilot_import_manifest.json`
- `artifacts/driftbench/real_pilot/`
- `artifacts/driftbench/real_pilot_features/`
- `artifacts/driftbench/real_pilot_readiness.json`
- `artifacts/driftbench/real_pilot_review_queue/`

Verified results:
- Real records: 34
- Unique real extensions: 11
- Controlled records in this intake: 0
- Label distribution: `benign_transition=29`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=32`, `UNCERTAIN=2`
- Eligible supervised-training records: 32
- Split distribution: `train=16`, `validation=12`, `test=6`
- Unique extensions per split: `train=4`, `validation=4`, `test=3`
- Test eligible labels: `benign_transition=5`, `risky_transition=1`
- License identifiers: `Apache-2.0=4`, `GPL-3.0=13`, `MIT=17`
- Duplicate report: passed; adjacent-version reuse is tracked as expected longitudinal chain reuse.
- Leakage report: passed with 0 protected split violations.
- Provenance completeness: 34/34.
- Feature extraction: completed for all 34 records across all five Phase 3B representations.

Readiness:
- Phase 3E readiness decision: READY for pilot ML re-evaluation.
- Limitation: single-reviewer provisional labels remain and must be treated as a methodology limitation.
- The two original `uncertain` Save Sora records remain `uncertain`, have structured review packets, and are excluded from supervised eligibility.
- No model was trained and no accuracy, FPR, FNR, ROC-AUC, PR-AUC, or production detection metric is claimed.

## Phase 3E Pilot Empirical Evaluation - 2026-08-11

Phase 3E ran the first research-grade pilot ML evaluation on the real pilot feature artifacts. These results are pilot/preliminary only.

Artifacts:
- `artifacts/experiments/phase3e/dataset_snapshot.json`
- `artifacts/experiments/phase3e/target_definition.json`
- `artifacts/experiments/phase3e/leakage_audit.json`
- `artifacts/experiments/phase3e/group_split_audit.json`
- `artifacts/experiments/phase3e/rule_baseline.json`
- `artifacts/experiments/phase3e/feature_set_comparison.csv`
- `artifacts/experiments/phase3e/logistic_results.csv`
- `artifacts/experiments/phase3e/random_forest_results.csv`
- `artifacts/experiments/phase3e/model_comparison.csv`
- `artifacts/experiments/phase3e/ablation_results.csv`
- `artifacts/experiments/phase3e/error_analysis.json`
- `artifacts/models/phase3e/phase3e_real_pilot_v1/`

Frozen dataset:
- Dataset version: `driftbench-real-pilot-phase3e-v1`
- Feature schema version: `1.0`
- Records: 34 total, 32 eligible supervised, 2 ineligible `uncertain`
- Unique extensions: 11
- Real records: 34
- Controlled records: 0
- Labels: `benign_transition=29`, `risky_transition=3`, `uncertain=2`

Split methodology:
- The preserved Phase 3D.6 split had no risky record in train, so it was not valid for supervised Phase 3E model fitting.
- Phase 3E froze `phase3e-group-safe-label-aware-v1` before training.
- Train: 20 eligible records, 5 extensions, `benign_transition=19`, `risky_transition=1`
- Validation: 6 eligible records plus 2 retained uncertain records, 3 extensions, `benign_transition=5`, `risky_transition=1`
- Test: 6 eligible records, 3 extensions, `benign_transition=5`, `risky_transition=1`

Quality gates:
- Leakage audit: passed across all five locked feature representations.
- Group split audit: passed with 0 extension overlaps, 0 package-hash overlaps, and 0 duplicate transition pairs.
- UNCERTAIN records were retained in dataset artifacts but excluded from supervised fitting and evaluation.
- ML artifacts were saved as research outputs only and were not integrated into production scoring.

Held-out test metrics:

| Method | Feature Set | Precision | Recall | F1 | Balanced Accuracy | FPR | FNR | False Alerts / 100 Benign | Confusion Matrix |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Rule engine | Full DriftWatch | 0.20 | 1.00 | 0.33 | 0.60 | 0.80 | 0.00 | 80.0 | `tn=1, fp=4, fn=0, tp=1` |
| Logistic Regression | Permission-only | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Logistic Regression | Manifest + permission | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Logistic Regression | Latest-version-only | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Logistic Regression | Simple differential | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Logistic Regression | Full DriftWatch | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Random Forest | Permission-only | 0.17 | 1.00 | 0.29 | 0.50 | 1.00 | 0.00 | 100.0 | `tn=0, fp=5, fn=0, tp=1` |
| Random Forest | Manifest + permission | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 100.0 | `tn=0, fp=5, fn=1, tp=0` |
| Random Forest | Latest-version-only | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Random Forest | Simple differential | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |
| Random Forest | Full DriftWatch | 0.00 | 0.00 | 0.00 | 0.50 | 0.00 | 1.00 | 0.0 | `tn=5, fp=0, fn=1, tp=0` |

Interpretation:
- The deterministic rule engine caught the single held-out risky transition but produced 4 false positives from 5 benign held-out updates.
- The primary ML models did not show enough value for production integration. Full DriftWatch Logistic Regression and Random Forest both missed the single held-out risky transition.
- The best F1 in this pilot was the rule engine at `0.33`; Random Forest permission-only reached `0.29` by alerting on every held-out record.
- Chronological evaluation was marked `not_reliable_pilot_too_small`.
- Label-quality sensitivity could not be rerun because the corpus has no sufficiently large higher-confidence subset with both target classes.
- Real-only evaluation is the primary Phase 3E result. Controlled-only and combined evaluations were not run.
