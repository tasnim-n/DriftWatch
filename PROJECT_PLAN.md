# DriftWatch Project Plan

**Full Academic Title**: DriftWatch: A Longitudinal and Explainable Framework for Detecting Dangerous Behavioural Changes in Browser-Extension Updates

---

## 1. Project Overview & Scope
Browser extensions pose unique cybersecurity risks: installed with benign privileges, subsequent updates may introduce permission creep, silent host access expansion, stealth network telemetry, dynamic obfuscation, and data exfiltration.

DriftWatch addresses this challenge through version-to-version differential behavioral analysis. By calculating differential security feature vectors between consecutive versions \( D_t = F(V_t) - F(V_{t-1}) \), DriftWatch detects dangerous behavioral drift and provides human-explainable security audit reports.

---

## 2. Six-Week Implementation Roadmap

| Milestone | Target Objective | Key Deliverables | Status |
|---|---|---|---|
| **Week 1** | Foundation & Secure Ingestion | Fast-API setup, secure ZIP/CRX unpacking, path traversal/bomb protection, manifest parser, permission risk database. | **Completed (Phase 1)** |
| **Week 2** | Core Drift Engine & Laboratory | Host-scope analyzer, package comparison, delta feature builder, rule-based scoring engine, controlled sample laboratory (`v1_safe`, `v2_risky`). | **Completed (Phase 1)** |
| **Week 3** | Advanced Static Analysis | Safe JavaScript lexical preprocessing, sensitive API extraction, network endpoint extraction, bounded static Base64 endpoint decoding, obfuscation indicators, structural drift, source-to-sink heuristics, partial-analysis error reporting, and score breakdowns. | **Completed (Phase 2, verified 2026-08-10)** |
| **Week 4** | DriftBench & Empirical Research Pipeline | Phase 3A dataset specification, label ontology, provenance tracking, validator, controlled mutation framework, leakage-safe split generator; Phase 3B feature extraction, baseline feature representations, leakage checks, and reproducible artifacts; Phase 3C pilot evaluation harness, leakage audit, readiness gate, deterministic baseline comparison, and blocked-ML reporting. | **Phase 3C pilot infrastructure implemented; ML blocked by dataset readiness** |
| **Week 5** | Dashboard & Visualization | Premium dark cybersecurity UI, executive summary, version progression timeline, report export (HTML/PDF). | **Completed (Phase 1 UI Foundation)** |
| **Week 6** | Research Experiments & Verification | Phase 3D real-data intake architecture, provenance-rich curation, license governance, duplicate/split-leakage audits, dataset manifests, local import workflow, real-pilot expansion, label-quality tiers, review packets, split-stability gate, Phase 3E pilot empirical evaluation, Phase 3F replication expansion, Phase 3G dataset maturation, and Phase 3H holdout/gold-set readiness. | **Phase 3H complete; label adjudication still needed** |

---

## 3. Current Progress (Phase 1 Completion)
- Scaffolded complete FastAPI and SQLAlchemy project directory.
- Built safe archive extraction engine (`app/core/security.py`) enforcing size limits, compression ratios, Zip-Slip, and Zip-Bomb mitigation.
- Implemented manifest analyzer (`analyzers/manifest_analyzer.py`) comparing permissions, host patterns, background scripts, content scripts, and web accessible resources.
- Implemented permission risk classification knowledge base (`analyzers/permission_analyzer.py`) categorizing sensitive permissions into Informational, Low, Moderate, High, Critical.
- Implemented host-scope expansion model (`analyzers/host_scope_analyzer.py`) quantifying pattern expansion from domain-specific paths to broad wildcard patterns and `<all_urls>`.
- Built rule-based hybrid scoring engine (`risk_engine/scoring.py`, `rules.py`) generating explainable risk scores (0-100), severity levels, confidence metrics, and evidence snippets.
- Created controlled extension laboratory samples (`samples/v1_safe_note` and `samples/v2_risky_note`).
- Created automated test suite covering security, unpacking, manifest parsing, permission/host analyzer, drift calculation, and web endpoints.

## 4. Current Progress (Phase 2 Verification)
- Implemented safe JavaScript preprocessing that preserves URL strings containing `//` while removing `//` and `/* ... */` comments.
- Implemented static sensitive API drift detection without executing uploaded extension JavaScript.
- Implemented network endpoint extraction for HTTP(S), WebSocket, IPv4, ports, sink destinations, localhost/test infrastructure, and bare domains in string/decoded contexts.
- Implemented bounded static Base64 endpoint decoding. No arbitrary runtime emulation is attempted.
- Implemented obfuscation, entropy, structural drift, and source-to-sink heuristic indicators.
- Integrated Phase 2 signals into the analysis pipeline, JSON API, report UI, explanations, recommendations, and score breakdowns.
- Verified test suite on 2026-08-10: `104 passed, 2 warnings`.

## 5. Deferred / Not Started
- Generalizable ML experiments, browser-store-scale DriftBench expansion, production ML integration, and real-world performance claims are not started.
- Browser-store-scale dataset collection is not started.
- The source-to-sink feature remains a heuristic indicator and does not prove confirmed exfiltration.

## 6. Current Progress (Phase 3A)
- Added DriftBench dataset record schema, label ontology, provenance helpers, metadata validator, controlled mutation framework, and leakage-safe split generator.
- Added deterministic group-aware random splits and chronological group-aware splits by `extension_id`.
- Added controlled synthetic mutation types for permission, host, API, network, obfuscation, background-worker, remote-config, source-to-sink, and gradual expansion patterns.
- Added validator checks for required fields, labels, timestamps, SHA-256 provenance, duplicate pair IDs, and split leakage.
- No ML models, dataset-size claims, or performance metrics have been introduced.

## 7. Current Progress (Phase 3B)
- Added versioned feature schema `1.0`.
- Added deterministic feature extraction for five representations: permission-only, manifest+permission, latest-version-only static, simple differential, and full DriftWatch behavioural drift.
- Added explicit analyzer availability flags so missing analyzer output is distinguishable from genuine zero.
- Added leakage safeguards excluding labels, final risk scores, recommendations, splits, paths, and class-revealing sample names from feature columns.
- Added CSV and JSONL artifact writers plus `feature_schema.json`, `dataset_summary.json`, and `extraction_manifest.json`.
- Generated controlled-sample artifacts under `artifacts/driftbench/` from two existing synthetic controlled records. These are descriptive controlled artifacts, not real-world performance evidence.
- No ML model training or ML metrics have been introduced.

## 8. Current Progress (Phase 3C)
- Added empirical-evaluation support under `research/`: artifact loaders, binary metrics, dataset readiness reporting, leakage auditing, deterministic pilot baselines, and reproducible experiment artifact writing.
- Generated verified Phase 3C pilot artifacts under `artifacts/experiments/` from the two controlled Phase 3B records.
- Current readiness gate result: ML training is **not permitted** because there are fewer than 20 records, no train/test split assignments, and all records are controlled/synthetic.
- Current leakage audit result: passed, with 43 feature columns audited and 0 violations.
- Deterministic pilot baseline metrics are recorded for smoke-testing only. They are not generalizable research results.
- Logistic Regression, Random Forest, ROC-AUC/PR-AUC, chronological evaluation, and ablation studies remain deferred until the dataset has enough real, leakage-safe train/test or chronological split data.

## 9. Current Progress (Phase 3D)
- Added source, licensing, dataset-stage, and data-quality governance constants.
- Expanded the label ontology to include real malicious transitions, uncertain records, and excluded records while preserving existing labels.
- Added local import-manifest curation with dry-run support: `python -m driftbench.ingest --manifest <path> --dry-run`.
- Added safe static package validation for local ZIP/CRX-compatible archives, manifest presence checks, SHA-256 hashing, extension identity checks, and defensible version-order validation.
- Added consecutive version-pair construction helpers for longitudinal update sequences.
- Added duplicate detection for record IDs, version pairs, and package hashes.
- Added split-leakage audits for extension identity, package hash overlap, and controlled mutation family leakage.
- Added manual-review record support for evidence-based labels without using DriftWatch score as ground truth.
- Added Phase 3D dataset manifests under `artifacts/driftbench/phase3d/`.
- Current Phase 3D real-record count is `0`; no real corpus was present, so no real records were fabricated.
- Phase 3D did not perform ML retraining; Phase 3E later ran a separate pilot evaluation after curated real data and quality gates were available.

## 10. Current Progress (Phase 3D.5)
- Acquired an initial lawful real pilot corpus from public GitHub release ZIP assets using normal HTTPS with size limits.
- Accepted 10 real consecutive version-pair transitions across 5 open-source browser-extension repositories.
- Generated curation reports, feature artifacts, and readiness report for the initial pilot.
- Phase 3D.5 remained blocked for Phase 3E because the real corpus was too small, the test split was too small, two labels were uncertain, and single-reviewer provisional labels dominated.
- No ML retraining or classifier metrics were produced.

## 11. Current Progress (Phase 3D.6)
- Expanded the real pilot corpus to 34 accepted real version-pair transitions across 11 open-source browser-extension repositories.
- Source category distribution: `open_source_repository=34`.
- Label distribution: `benign_transition=29`, `risky_transition=3`, `uncertain=2`.
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=32`, `UNCERTAIN=2`.
- Eligible supervised-training records: 32. The two `uncertain` records are retained for review history and are not eligible for supervised training.
- License identifier distribution: `Apache-2.0=4`, `GPL-3.0=13`, `MIT=17`; license status distribution: `allowed=34`.
- Split distribution: `train=16`, `validation=12`, `test=6`; test split has 3 extension identities and eligible labels `benign_transition=5`, `risky_transition=1`.
- Duplicate audit passed, protected split-leakage audit passed with 0 violations, and provenance completeness is 34/34.
- Generated structured review packets and a review queue for `save-sora_2_0_355_to_3_0_0` and `save-sora_3_0_0_to_3_0_10`; both remain `uncertain`.
- Regenerated Phase 3B feature representations for all 34 records under `artifacts/driftbench/real_pilot_features/`.
- Readiness gate at `artifacts/driftbench/real_pilot_readiness.json` was **READY** for Phase 3E pilot ML re-evaluation, with the explicit limitation that single-reviewer provisional labels remain.

## 12. Current Progress (Phase 3E)
- Frozen Phase 3E dataset snapshot: `driftbench-real-pilot-phase3e-v1`.
- Phase 3E detected that the preserved Phase 3D.6 split had no `risky_transition` records in train, so it created a separate pre-training, label-aware, extension-group-safe experiment split: `phase3e-group-safe-label-aware-v1`.
- Frozen supervised counts: 34 total records, 32 eligible supervised records, 2 ineligible `uncertain` records, 11 unique extensions, all real records, 0 controlled records.
- Experiment split counts: train 20 eligible records (`benign_transition=19`, `risky_transition=1`), validation 6 eligible records (`benign_transition=5`, `risky_transition=1`) plus 2 retained uncertain records, test 6 eligible records (`benign_transition=5`, `risky_transition=1`).
- Leakage audit passed across all five locked Phase 3B feature representations; labels, review metadata, eligibility, split metadata, paths, final scores, severities, and recommendations were excluded from feature matrices.
- Group split audit passed with 0 extension overlaps, 0 package-hash overlaps, and 0 duplicate transition pairs across protected splits.
- Current deterministic risk scorer baseline on the held-out Phase 3E test set: precision `0.20`, recall `1.00`, F1 `0.33`, balanced accuracy `0.60`, FPR `0.80`, FNR `0.00`, confusion matrix `tn=1, fp=4, fn=0, tp=1`.
- Full DriftWatch Logistic Regression on the same held-out test set: precision `0.00`, recall `0.00`, F1 `0.00`, FPR `0.00`, FNR `1.00`, confusion matrix `tn=5, fp=0, fn=1, tp=0`.
- Full DriftWatch Random Forest on the same held-out test set: precision `0.00`, recall `0.00`, F1 `0.00`, FPR `0.00`, FNR `1.00`, confusion matrix `tn=5, fp=0, fn=1, tp=0`.
- Phase 3E artifacts are saved under `artifacts/experiments/phase3e/` and research models under `artifacts/models/phase3e/phase3e_real_pilot_v1/`.
- ML was not integrated into production scoring. The evidence does not justify production ML deployment; results remain pilot/preliminary due small sample size, one positive held-out test record, and provisional labels.

## 13. Current Progress (Phase 3F)
- Phase 3E artifacts were preserved as `PILOT_BASELINE`; Phase 3F references their hashes without overwriting Phase 3E metrics, predictions, models, or error analysis.
- New dataset version: `driftbench-real-replication-phase3f-v1`.
- Added 12 independent real replication transitions from public GitHub release ZIP assets across 3 additional extension identities: Browserpass, Dark Reader, and Stylus.
- Accepted Phase 3F corpus: 46 real records, 14 unique extensions, 0 controlled records.
- Label distribution: `benign_transition=41`, `risky_transition=3`, `uncertain=2`.
- Label quality distribution: `SINGLE_REVIEWER_PROVISIONAL=44`, `UNCERTAIN=2`. No genuine second human reviewer was available, so inter-rater agreement is not available.
- Split distribution: `train=24`, `validation=12`, `test=10`; protected group and package-hash leakage audits passed.
- Feature schema remains `1.0`; Phase 3F reused frozen Phase 3E baseline feature rows and extracted features only for the 12 new replication records.
- Current deterministic rule scorer on Phase 3F held-out test: precision `0.111111`, recall `1.0`, F1 `0.2`, FPR `0.888889`, FNR `0.0`, confusion matrix `tn=1, fp=8, fn=0, tp=1`.
- Full DriftWatch Logistic Regression and Random Forest both remained F1 `0.0` on the Phase 3F held-out test, each missing the single risky held-out transition.
- Replication conclusion: `INCONCLUSIVE`. ML integration remains unjustified; the evidence-based next phase is `CONTINUE DATASET EXPANSION`.

## 14. Current Progress (Phase 3G)
- New dataset version: `driftbench-real-maturation-phase3g-v1`.
- Phase 3F artifacts were preserved as frozen baseline history. Phase 3G writes only `phase3g` outputs.
- Added 12 lawful real version-pair records from public GitHub release ZIP assets across 3 new extension identities: Automa, LibRedirect, and Web Scrobbler.
- Accepted Phase 3G corpus: 58 real records, 17 unique extensions, 0 controlled records.
- Label distribution: `benign_transition=53`, `risky_transition=3`, `uncertain=2`.
- Label quality distribution: `SINGLE_REVIEWER_PROVISIONAL=56`, `UNCERTAIN=2`; no genuine double-review records exist, so inter-rater agreement is not available.
- Training-eligible records: 56. The two original Save Sora `uncertain` records remain unresolved and training-ineligible, with refreshed static review packets.
- Split distribution: `train=32`, `validation=16`, `test=10`; protected duplicate and leakage audits passed.
- Phase 3B feature artifacts were regenerated for all five established representations under `artifacts/driftbench/phase3g_features/`; schema remains `1.0`.
- uBlacklist candidate releases were excluded because they triggered DriftWatch extraction safety controls. Security limits were not weakened.
- Phase 3G decision: `DATASET STILL TOO WEAK - CONTINUE EXPANSION`. Production ML integration remains unjustified.

## 15. Current Progress (Phase 3H)
- New dataset version: `driftbench-real-adjudication-holdout-phase3h-v1`.
- Phase 3G artifacts were preserved as frozen baseline history. Phase 3H writes only `phase3h` outputs.
- Added 18 lawful real version-pair records from public GitHub release assets across 4 new extension identities: Bitwarden Browser, ClearURLs, HeaderEditor, and Ruffle Web Extension.
- Accepted Phase 3H corpus: 76 real records, 21 unique extensions, 0 controlled records.
- Label distribution: `benign_transition=71`, `risky_transition=3`, `uncertain=2`; no malicious-transition records are independently confirmed.
- Label quality distribution: `SINGLE_REVIEWER_PROVISIONAL=74`, `UNCERTAIN=2`; genuine double-review and adjudication counts remain 0.
- Gold Set size is 0 because no real records have external confirmation or genuine multi-reviewer adjudication.
- External replication holdout size is 10 records across 2 new extension identities. Holdout rows are excluded from non-holdout feature artifacts and locked for future Phase 3I validation.
- Phase 3B feature artifacts were regenerated for non-holdout records under `artifacts/driftbench/phase3h_features/`; schema remains `1.0`.
- Duplicate, leakage, provenance, timestamp, analyzer-health, and security-boundary audits passed.
- Phase 3H decision: `CONTINUE INDEPENDENT LABEL REVIEW / ADJUDICATION`. Production ML integration remains unjustified.
