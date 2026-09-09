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

## Phase 3F Independent Replication Study - 2026-08-11

Phase 3F preserves Phase 3E as `PILOT_BASELINE` and creates a separate replication dataset and experiment series.

Artifacts:
- `datasets/manifests/phase3f_import_manifest.json`
- `artifacts/driftbench/phase3f/`
- `artifacts/driftbench/phase3f_features/`
- `artifacts/experiments/phase3f/`
- `artifacts/models/phase3f/phase3f_replication_v1/`

Dataset:
- Dataset version: `driftbench-real-replication-phase3f-v1`
- Real records: 46
- New independent replication records: 12
- Unique extensions: 14
- Controlled records: 0
- Labels: `benign_transition=41`, `risky_transition=3`, `uncertain=2`
- Label quality: `SINGLE_REVIEWER_PROVISIONAL=44`, `UNCERTAIN=2`
- Double-reviewed records: 0
- Inter-rater agreement: not available
- Licenses: `Apache-2.0=4`, `GPL-3.0=16`, `ISC=4`, `MIT=22`
- Splits: `train=24`, `validation=12`, `test=10`

Quality gates:
- Provenance completeness: 46/46
- Duplicate audit: passed
- Group/package-hash leakage audit: passed
- Feature leakage audit: passed
- Feature schema: unchanged at `1.0`
- UNCERTAIN records remained training-ineligible
- ML was not deployed to production

Held-out replication metrics:

| Method | Feature Set | Precision | Recall | F1 | Balanced Accuracy | FPR | FNR | False Alerts / 100 Benign | Confusion Matrix |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Rule engine | Full DriftWatch | 0.111111 | 1.0 | 0.2 | 0.555556 | 0.888889 | 0.0 | 88.888889 | `tn=1, fp=8, fn=0, tp=1` |
| Logistic Regression | Full DriftWatch | 0.0 | 0.0 | 0.0 | 0.5 | 0.0 | 1.0 | 0.0 | `tn=9, fp=0, fn=1, tp=0` |
| Random Forest | Full DriftWatch | 0.0 | 0.0 | 0.0 | 0.5 | 0.0 | 1.0 | 0.0 | `tn=9, fp=0, fn=1, tp=0` |
| Random Forest | Permission-only | 0.1 | 1.0 | 0.181818 | 0.5 | 1.0 | 0.0 | 100.0 | `tn=0, fp=9, fn=0, tp=1` |

Phase 3E vs Phase 3F:
- Rule-engine F1: `0.333333` -> `0.2`
- Rule-engine recall: `1.0` -> `1.0`
- Rule-engine FPR: `0.8` -> `0.888889`
- Full DriftWatch Logistic Regression F1: `0.0` -> `0.0`
- Full DriftWatch Random Forest F1: `0.0` -> `0.0`

Interpretation:
- The Phase 3E finding did not become deployment-positive after replication.
- Rules still catch the single held-out risky transition but continue to over-alert on feature-rich benign updates.
- ML remains not justified for production integration.
- Replication conclusion: `INCONCLUSIVE`.
- Evidence-based next phase: `CONTINUE DATASET EXPANSION`.

## Phase 3G Real-Corpus Maturation - 2026-08-11

Phase 3G is a data-quality and ground-truth maturation phase. It does not retrain/deploy ML or change production scoring.

Artifacts:
- `datasets/manifests/phase3g_import_manifest.json`
- `artifacts/driftbench/phase3g/`
- `artifacts/driftbench/phase3g_features/`
- `artifacts/experiments/phase3g/`

Dataset:
- Dataset version: `driftbench-real-maturation-phase3g-v1`
- Previous dataset version: `driftbench-real-replication-phase3f-v1`
- Real records: 58
- New Phase 3G records: 12
- Unique extensions: 17
- Controlled records: 0
- Labels: `benign_transition=53`, `risky_transition=3`, `uncertain=2`
- Label quality: `SINGLE_REVIEWER_PROVISIONAL=56`, `UNCERTAIN=2`
- Training-eligible records: 56
- Licenses: `Apache-2.0=4`, `GPL-3.0=24`, `ISC=4`, `MIT=26`
- Splits: `train=32`, `validation=16`, `test=10`

Quality gates:
- Provenance completeness: 58/58
- Timestamp completeness: 58/58
- Duplicate audit: passed
- Protected leakage audit: passed
- Feature leakage audit: passed
- Feature schema: unchanged at `1.0`
- Feature regeneration: completed for all five established Phase 3B representations
- Inter-rater agreement: not available

Phase 3F vs Phase 3G dataset comparison:
- Total real records: `46` -> `58`
- Unique extensions: `14` -> `17`
- Risky or malicious records: `3` -> `3`
- Uncertain records: `2` -> `2`
- Double-reviewed records: `0` -> `0`
- Provenance completeness: `46/46` -> `58/58`
- Timestamp completeness: `46/46` -> `58/58`

Interpretation:
- Phase 3G improved corpus size, extension diversity, provenance, timestamp coverage, review packets, and feature artifacts.
- uBlacklist was excluded after triggering extraction safety controls; security gates were not weakened.
- Single-reviewer provisional labels still dominate, the risky/review-worthy class remains small, and no genuine second-review agreement exists.
- Evidence-based decision: `DATASET STILL TOO WEAK - CONTINUE EXPANSION`.

## Phase 3H Holdout And Gold-Set Readiness - 2026-08-11

Phase 3H expands the corpus and prepares future external validation. It does not run model replication, retrain ML, deploy ML, or change production scoring.

Artifacts:
- `datasets/manifests/phase3h_import_manifest.json`
- `artifacts/driftbench/phase3h/`
- `artifacts/driftbench/phase3h_features/`
- `artifacts/experiments/phase3h/`

Dataset:
- Dataset version: `driftbench-real-adjudication-holdout-phase3h-v1`
- Parent dataset version: `driftbench-real-maturation-phase3g-v1`
- Real records: 76
- New Phase 3H records: 18
- Unique extensions: 21
- Controlled records: 0
- Labels: `benign_transition=71`, `risky_transition=3`, `uncertain=2`
- Label quality: `SINGLE_REVIEWER_PROVISIONAL=74`, `UNCERTAIN=2`
- Gold Set size: 0
- External holdout size: 10 records across 2 extensions

Quality gates:
- Provenance completeness: 76/76
- Timestamp completeness: 76/76
- Duplicate audit: passed
- Leakage audit: passed
- Feature leakage audit: passed
- Analyzer missingness: 0
- Inter-rater agreement: not available

Phase 3G vs Phase 3H:
- Real records: `58` -> `76`
- Unique extensions: `17` -> `21`
- Risky or malicious records: `3` -> `3`
- Uncertain records: `2` -> `2`
- Double-reviewed records: `0` -> `0`
- Gold Set size: `0` -> `0`
- External holdout size: `0` -> `10`

Interpretation:
- Phase 3H materially increased corpus size and extension diversity and created an untouched external holdout.
- It did not improve review-worthy class representation or label quality.
- A genuine Gold Set is not yet available.
- Evidence-based decision: `CONTINUE INDEPENDENT LABEL REVIEW / ADJUDICATION`.

## Phase 3H.5 Independent Review And Ground-Truth Qualification - 2026-08-11

Phase 3H.5 implements the next evidence-based step from Phase 3H: independent label-review workflow and Gold Set qualification. It does not train or deploy ML and does not change production scoring.

Artifacts:
- `artifacts/driftbench/phase3h5/`
- `artifacts/experiments/phase3h5/`
- `datasets/reviews/phase3h5/`
- `REVIEWER_GUIDE.md`
- `reviewer_b_blind/`

Verified outputs:
- Artifact version: `driftbench-independent-review-phase3h5-v1`
- Parent dataset version: `driftbench-real-adjudication-holdout-phase3h-v1`
- Review scope: 76 records
- Priority records: 47
- Blind review packets: 76
- Genuine Reviewer A count: 0
- Genuine Reviewer B count: 0
- Double-reviewed count: 0
- Genuine agreement count: 0
- Genuine disagreement count: 0
- Genuine adjudicated count: 0
- Inter-rater agreement: not available
- Label quality: `SINGLE_REVIEWER_PROVISIONAL=74`, `UNCERTAIN=2`
- Real Gold Set size: 0
- Controlled Gold Set size: 0
- Supervised-training eligible records after recheck and external-holdout exclusion: 64
- Confirmed malicious-transition records: 0

Simulated secondary-review/adjudication exercise:
- A 15-record simulated/AI-assisted secondary-review exercise was run. It is not a genuine human Reviewer B review.
- Initial comparison produced 15 comparable selected records, 2 direct agreements, 13 disagreements, and a simulated label-match rate of `13.33%`.
- The 13 disagreements entered a simulated adjudication workflow; no genuine human adjudication was created.
- `clearurls_addon_1_20_0_to_1_21_0` was confirmed through `artifacts/driftbench/phase3h/external_holdout_manifest.json` as an external holdout and marked `EXTERNAL_HOLDOUT_LOCKED` in the simulated adjudication queue.
- The locked holdout record must not be used for model tuning, rule tuning, Gold Set construction, adjudication-driven label changes, training, or development decisions.
- Excluding that external holdout, the simulated 14-record outcome was `RISKY_TRANSITION=7`, `BENIGN_TRANSITION=4`, `UNCERTAIN=3`.
- Existing research labels were not automatically overwritten.

Quality gates:
- Phase 3H reference frozen.
- Review packets hide DriftWatch numeric output, severity, recommendations, ML outputs, previous predictions, and current provisional labels.
- Reviewer metadata leakage audit passed for predictive feature columns.
- External holdout remains isolated from model training, rule tuning, Gold Set construction, adjudication-driven label changes, and development decisions.
- Research-integrity audit passed: no completed independent review, Gold Set, inter-rater agreement, or confirmed malicious records are claimed.

Decision:
- Current status: Phase 3H.5 simulated review/adjudication workflow demonstration is complete, and external-holdout protection was successfully preserved.
- Final Phase 3H.5 decision: `MORE INDEPENDENT REVIEW REQUIRED`.
- Phase 3I is not methodologically ready.
