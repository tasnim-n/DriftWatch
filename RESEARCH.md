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
- Phase 3C baseline experiments, machine learning, large-scale DriftBench collection, and empirical ML performance evaluation have not started. No precision, recall, F1, AUC, or false-positive-rate results should be claimed until those experiments are actually run.

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
