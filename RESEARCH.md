# DriftWatch Research Specifications

## 1. Primary Research Question
**RQ1**: Can version-to-version behavioral-difference features detect risky browser-extension updates more effectively and explainably than permission-only analysis or analyzing only the latest version?

## 2. Secondary Research Questions
- **RQ2**: Which behavioral-drift categories (permission, host-scope, sensitive API, network, obfuscation, structural) contribute most significantly to risk detection?
- **RQ3**: Can extension-specific baselines (using version \( V_{t-1} \) as the baseline for version \( V_t \)) reduce false positive rates compared to absolute global thresholds?
- **RQ4**: Does chronological evaluation provide a more realistic performance estimate for browser update monitoring than random dataset splitting?
- **RQ5**: Can explainable risk reports provide security analysts with actionable visual evidence to audit complex updates efficiently?

## 3. Mathematical Formulation

Let \( V_{t-1} \) be the baseline trusted extension version, and \( V_t \) be the update under analysis.

Each extension version is represented by an absolute security feature vector:
\[
F(V_t) \in \mathbb{R}^k
\]

The behavioral drift vector \( D_t \) is defined as:
\[
D_t = F(V_t) - F(V_{t-1})
\]

Where \( D_t \) captures:
1. **Permission Drift** (\( \Delta P \)): Net added permissions weighted by severity.
2. **Host-Scope Expansion** (\( \Delta H \)): Numerical expansion ratio of webpage access scope.
3. **Sensitive API Drift** (\( \Delta A \)): Newly introduced calls to `chrome.cookies`, `chrome.webRequest`, `chrome.tabs`, `chrome.storage`, etc.
4. **Network Destination Drift** (\( \Delta N \)): New remote hosts, IP addresses, or WebSocket endpoints.
5. **Obfuscation & Entropy Drift** (\( \Delta O \)): Increase in Shannon entropy, `eval()`, string encoding, and minification ratio.
6. **Structural Code Drift** (\( \Delta S \)): AST node differences, function additions, line count changes, and source-to-sink flow heuristic changes.

## 4. Evaluation Methodology
- **Baselines**:
  1. Permission-only detection (evaluating only manifest permissions).
  2. Single-version classification (evaluating version \( V_t \) without baseline context).
  3. Naive text diff (line count change).
  4. Full DriftWatch Differential Model.
- **Metrics**: Precision, Recall, F1-Score, Balanced Accuracy, ROC-AUC, PR-AUC, False Positive Rate (FPR), False Alerts per 100 updates, Analysis Latency (ms).

## 5. Current Implementation Status
- Phase 2 static analysis is implemented and verified on the controlled local samples as of 2026-08-10.
- The implementation uses static lexical and regex-based JavaScript analysis, not runtime execution and not full JavaScript AST semantics.
- Static decoding is limited to bounded Base64-like string literals and scans decoded text only for endpoint indicators.
- Source-to-sink results are heuristic indicators within the same file. They do not prove confirmed exfiltration.
- Phase 3A DriftBench methodology is implemented: dataset specification, labels, provenance, validator, controlled mutations, and leakage-safe splits.
- Phase 3B feature extraction is implemented: versioned feature schema, baseline feature representations, leakage checks, explicit analyzer availability, and reproducible CSV/JSONL artifacts.
- Phase 3C pilot evaluation infrastructure is implemented. It produces readiness, leakage-audit, baseline-comparison, confusion-matrix, prediction, and blocked-experiment artifacts.
- Phase 3E pilot empirical evaluation has been run on the current DriftBench real pilot corpus. The results are preliminary pilot findings, not broad browser-extension performance claims.
- Generalizable ML experiments, large-scale DriftBench collection, production ML integration, and real-world population-level performance evaluation have not started.

## 6. Verified Controlled Runs
- Benign control pair (`v1_note_benign` -> `v2_note_benign`): verified on 2026-08-10 as `0.0/100`, `Low`.
- Risky controlled pair (`v1_safe_note` -> `v2_risky_note`): verified on 2026-08-10 as `100.0/100`, `Critical`.
- These are current rule-engine outputs for synthetic samples, not general detection-performance metrics. Scores may change when scoring rules change.

## 7. DriftBench Phase 3A Methodology
DriftBench records are version pairs with explicit provenance, labels, label rationale, archive hashes, and split assignments. The split generator is leakage-aware: related versions of the same `extension_id` must stay in one experiment split.

Controlled mutations are allowed only as synthetic laboratory records. They are useful for testing expected detector behavior but must be separated from real-world evaluation claims.

## 8. DriftBench Phase 3B Feature Representations
Phase 3B prepares feature rows for future experiments without training models.

1. Permission-only drift: permission count, sensitive permission count, permission risk delta, and high/critical permission flags.
2. Manifest + permission drift: permission features plus host expansion, service-worker introduction, content-script, CSP, externally-connectable, and web-accessible-resource changes.
3. Latest-version-only static: V2-only static properties such as total permissions, V2 hosts, V2 API count, V2 endpoint count, V2 obfuscation count, V2 service-worker presence, and V2 source-to-sink heuristic count. This representation intentionally ignores V1/delta fields.
4. Simple differential: compact count/size deltas such as permission, host, file, package size, JS file, API, network, obfuscation, and function deltas.
5. Full DriftWatch behavioural drift: evidence-rich drift features spanning permission, host, API, network, obfuscation, structural, package, and analyzer-health families.

Feature artifacts preserve labels and splits as metadata only. They do not include final DriftWatch risk score, final risk classification, recommendations, label rationale text, or path-derived class names as features. Raw values are not normalized during extraction; scaling belongs inside future training pipelines using training data only.

## 9. Phase 3C Pilot Evaluation
Phase 3C currently verifies the empirical-evaluation machinery on the controlled Phase 3B artifacts. The current artifact set has:

- `record_count`: 2
- `unique_extension_count`: 2
- `label_distribution`: `benign_transition=1`, `risky_transition=1`
- `split_counts`: `controlled_holdout=2`
- `controlled_record_count`: 2
- `real_record_count`: 0

The readiness gate blocks ML training because there are fewer than 20 records, no train/test split assignments, and all records are controlled/synthetic. This is intentional research hygiene, not a failure to train.

The leakage audit passed on the current feature artifacts: 43 feature columns audited, 0 violations, and extension group split safety confirmed. Labels, splits, paths, risk scores, final classifications, recommendations, and class-revealing text remain excluded from feature columns.

Deterministic pilot baseline metrics generated on 2026-08-10 are smoke-test results only:

| Baseline | Records | Precision | Recall | F1 | Balanced Accuracy | FPR | FNR | False Alerts / 100 Benign |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| permission_only | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| manifest_permission | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| latest_version_static | 2 | 0.5 | 1.0 | 0.666667 | 0.5 | 1.0 | 0.0 | 100.0 |
| simple_differential | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| full_driftwatch | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |

These values validate artifact plumbing and rule execution over two controlled records. They must not be reported as model performance, real-world detector performance, or evidence of prevalence.

Logistic Regression, Random Forest, ROC-AUC/PR-AUC, chronological evaluation, and ablation studies are not run on the current artifacts. They are explicitly marked as blocked or unavailable in `artifacts/experiments/`.

## 10. Phase 3D Real-Data Intake And Curation
Phase 3D adds research-grade intake infrastructure for future real DriftBench records. It does not add fabricated real records.

Current verified Phase 3D intake artifact state:

- `driftbench_version`: `0.1.0`
- Accepted real records: 0
- Controlled records imported through Phase 3D intake: 0
- Accepted version pairs through Phase 3D intake: 0
- Existing controlled Phase 3B artifact records: 2

The Phase 3D workflow supports local/offline replay after lawful acquisition:

1. Capture provenance and licensing metadata in an import manifest.
2. Validate local package paths, ZIP readability, `manifest.json`, SHA-256 hashes, extension identity, and version ordering.
3. Quarantine or exclude records with unknown source rights, missing provenance, ambiguous identity, broken packages, or unresolved labels.
4. Emit dataset, provenance, quality, duplicate, leakage, license, and validation reports.
5. Pass accepted records to the existing Phase 3B feature extractor without changing the feature schema.

Labels are evidence-based curation labels. DriftWatch's own risk score must not be used as ground truth because that would create circular evaluation.

No Phase 3D artifact supports claims about web-store prevalence, malicious-extension prevalence, model accuracy, false-positive rate, or representativeness.

## 11. Phase 3D.5 Real Pilot Corpus
Phase 3D.5 created a small real pilot corpus from public open-source browser-extension release ZIP assets. The corpus is intended to validate acquisition, curation, provenance, and feature extraction. It is not a representative web-store dataset.

Actual real pilot corpus facts:

- Dataset version: `0.1.0-real-pilot`
- Real version-pair records: 10
- Unique real extensions: 5
- Controlled records imported in Phase 3D.5: 0
- Existing controlled Phase 3B records remain separate: 2
- Source type distribution: `open_source_repository=10`
- Label distribution: `benign_transition=6`, `risky_transition=2`, `uncertain=2`
- Label-source distribution: `repository_documented_change=1`, `single_reviewer_provisional=9`
- License identifiers: `MIT=9`, `GPL-3.0=1`
- Timestamp source: GitHub release `published_at` metadata with medium confidence

The five source repositories are:

- `AaronCQL/katex-github-chrome-extension`
- `yniijia/SubtideX`
- `kevinsqi/save_tabbed_images`
- `alpha1337/save-sora`
- `alyssaxuu/screenity`

Labels are independent curation labels. DriftWatch risk scores, severities, recommendations, and ML outputs were not used as ground truth. Two `uncertain` records are retained for curation but must be excluded from supervised training until reviewed.

Feature extraction completed for all 10 accepted real-pilot records using the existing Phase 3B feature schema. No model training, no classifier evaluation, and no performance metrics were run.

## 12. Phase 3D.6 Real Pilot Expansion
Phase 3D.6 expanded the real pilot corpus and strengthened curation metadata. It did not train models and did not produce classifier-performance metrics.

Verified real pilot facts as of 2026-08-10:

- Dataset version: `0.1.0-real-pilot`
- Real version-pair records: 34
- Unique real extensions: 11
- Existing controlled Phase 3B records remain separate: 2
- Source type distribution: `open_source_repository=34`
- Label distribution: `benign_transition=29`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=32`, `UNCERTAIN=2`
- Eligible supervised-training records: 32
- Split distribution: `train=16`, `validation=12`, `test=6`
- Unique extensions per split: `train=4`, `validation=4`, `test=3`
- Test eligible labels: `benign_transition=5`, `risky_transition=1`
- License identifiers: `Apache-2.0=4`, `GPL-3.0=13`, `MIT=17`
- Provenance completeness: 34/34
- Duplicate audit: passed
- Protected split-leakage audit: passed with 0 violations
- Feature extraction: completed for all 34 records across all five Phase 3B feature representations

The two original `uncertain` Save Sora records remain unresolved because the local evidence bundle does not independently justify a benign, risky, or malicious label. They are retained for review history, have structured review packets, and are excluded from supervised eligibility.

The Phase 3D.6 readiness gate marks Phase 3E as READY for pilot ML re-evaluation. This means the methodology gate is satisfied for the next phase; it is not a model-performance result. Single-reviewer provisional labels remain a known limitation and must be acknowledged in Phase 3E.

## 13. Phase 3E Pilot Empirical Evaluation

### Research Question
On the current DriftBench pilot corpus, Phase 3E asks whether version-aware behavioural-drift features add measurable review value over simpler baselines, and whether ML models provide enough benefit to justify a future integration gate.

### Hypotheses
- Full behavioural drift may improve review-worthy transition detection relative to permission-only analysis.
- Longitudinal/differential features may improve over latest-version-only static features.
- The deterministic rule engine may remain operationally valuable because it is explainable, even when ML metrics are mixed.

### Dataset
- Frozen dataset version: `driftbench-real-pilot-phase3e-v1`
- Source dataset: `0.1.0-real-pilot`
- Total records: 34
- Eligible supervised records: 32
- Ineligible records: 2 `uncertain`
- Unique extensions: 11
- Real records: 34
- Controlled records: 0
- Label distribution: `benign_transition=29`, `risky_transition=3`, `uncertain=2`

The preserved Phase 3D.6 split had no `risky_transition` records in train, which made supervised binary training invalid. Phase 3E therefore froze a separate pre-training experiment split, `phase3e-group-safe-label-aware-v1`, without changing records or labels.

Phase 3E split:
- Train: 20 eligible records, 5 extensions, `benign_transition=19`, `risky_transition=1`
- Validation: 6 eligible records plus 2 retained uncertain records, 3 extensions, `benign_transition=5`, `risky_transition=1`
- Test: 6 eligible records, 3 extensions, `benign_transition=5`, `risky_transition=1`

### Target Definition
The current corpus does not support defensible multiclass evaluation. Phase 3E uses:

| Source Label | Binary Target |
|---|---|
| `benign_transition` | `BENIGN` |
| `risky_transition` | `REVIEW_WORTHY` |
| `controlled_malicious_transition` | `REVIEW_WORTHY` if present in future eligible artifacts |
| `uncertain` | excluded from supervised fitting/evaluation |

`REVIEW_WORTHY` is a research target and does not mean confirmed malicious intent.

### Feature Representations
The five Phase 3B feature representations were locked before model evaluation:
1. Permission-only drift
2. Manifest + permission drift
3. Latest-version-only static features
4. Simple differential features
5. Full DriftWatch behavioural-drift features

The leakage audit passed across all five feature sets. Metadata such as labels, review status, split assignment, paths, final DriftWatch scores, severities, and recommendations remained excluded from model inputs.

### Evaluation Protocol
Models were selected using train/validation only and evaluated once on the held-out extension-group-safe test split. Logistic Regression used an sklearn `Pipeline` with `StandardScaler` fit on train only. Random Forest used fixed `random_state` and conservative validation-only hyperparameter selection. ML artifacts were saved for research only and were not integrated into the production risk engine.

### Baselines And Models
- Current deterministic DriftWatch risk scorer, evaluated with the fixed High-or-Critical review threshold: `risk_score >= 40.0`
- Logistic Regression across all five feature sets
- Random Forest across all five feature sets

### Results
Held-out test set size is 6 records with only 1 review-worthy record. Accuracy is not a headline metric.

| Method | Feature Set | Precision | Recall | F1 | Balanced Acc. | FPR | FNR | False Alerts / 100 Benign | Confusion Matrix |
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

### Ablation
Full DriftWatch Logistic Regression already had F1 `0.00`, recall `0.00`, and FPR `0.00` on the held-out test set. Removing permission, host, API, network, obfuscation, structural, or source-to-sink feature families did not change those held-out metrics. This does not prove the families are unimportant; the test set is too small and contains only one review-worthy example.

### Error Analysis
The deterministic risk scorer produced four false positives, all from benign real updates with strong static behavioural signals. The dominant category was feature-rich benign update / network false positive, especially updates with new external network destinations, obfuscation-like/minification indicators, and source-to-sink heuristics.

Full DriftWatch Logistic Regression and Random Forest each produced one false negative: the held-out `katex-github-chrome-extension_0_1_0_to_0_2_0` risky transition. The record contains strong static drift signals, but the tiny and imbalanced train set did not support reliable generalization.

### Threats To Validity
Internal validity: labels are mostly single-reviewer provisional, static analyzer errors may affect features, and scoring assumptions influence the deterministic rule baseline.

External validity: the corpus is pilot-scale, open-source-repository biased, and not representative of browser-store-scale extension updates.

Construct validity: `risky_transition` and `REVIEW_WORTHY` are security-review labels, not proof of malicious intent. Static indicators do not prove runtime behaviour.

Statistical conclusion validity: the held-out test set has 6 records and 1 positive. Confidence intervals are computed as artifacts but are not reliable for inference.

### Interpretation
Q1 and Q2 cannot be answered affirmatively from this pilot: full behavioural drift did not outperform permission-only analysis in the ML held-out results. The deterministic scorer detected the risky held-out transition but generated many false positives.

Q3 remains inconclusive: feature importances and coefficients are unstable. In this pilot, network, obfuscation, function-count, and optional-permission features appear in model summaries, but no causal or general importance claim is justified.

Q4: the main false-positive cause is feature-rich benign updates that look suspicious to static drift rules, especially network/obfuscation/source-to-sink combinations.

Q5: the main false-negative cause for ML is insufficient positive training support and distribution mismatch, not absence of detectable static drift.

Q6: results are sensitive to provisional labels; no higher-confidence subset exists with enough support to rerun the experiment.

Q7: Phase 3E evaluates real-only records. Controlled-only and combined evaluations were not run because no controlled records are in the real-pilot feature snapshot and mixing the two would weaken real-world interpretation.

Q8: chronological evaluation is not reliable on the current pilot because only three review-worthy records across three extension groups are available.

Q9: ML does not currently provide enough evidence to justify production integration. A future hybrid approach may be worth studying only after a larger, independently reviewed corpus exists.

Q10: broader claims require more independently labeled real records, more review-worthy transitions, adjudicated labels, and a larger held-out set.

Artifacts:
- `artifacts/experiments/phase3e/`
- `artifacts/models/phase3e/phase3e_real_pilot_v1/`
