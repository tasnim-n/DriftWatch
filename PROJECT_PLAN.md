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
| **Week 4** | DriftBench & Empirical Research Pipeline | Phase 3A dataset specification, label ontology, provenance tracking, validator, controlled mutation framework, leakage-safe split generator; Phase 3B feature extraction, baseline feature representations, leakage checks, and reproducible artifacts. ML baselines and models are deferred. | **Phase 3B implemented; ML deferred** |
| **Week 5** | Dashboard & Visualization | Premium dark cybersecurity UI, executive summary, version progression timeline, report export (HTML/PDF). | **Completed (Phase 1 UI Foundation)** |
| **Week 6** | Research Experiments & Verification | Feature ablation study, baseline comparison, security auditing tests, final demonstration scripts. | Planned (Phase 4) |

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
- Verified test suite on 2026-08-10: `41 passed`.

## 5. Deferred / Not Started
- Phase 3C baseline experiments, machine learning, DriftBench expansion, and performance metrics are not started.
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
