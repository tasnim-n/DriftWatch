# DriftWatch

**Full Academic Title**: *DriftWatch: A Longitudinal and Explainable Framework for Detecting Dangerous Behavioural Changes in Browser-Extension Updates*

---

## Executive Summary
Browser extensions receive extensive access to sensitive web browsing data, authentication sessions, cookies, tabs, and network requests. While an extension may pass initial web store reviews as a benign utility, subsequent updates can silently introduce **permission creep**, **host-scope expansion**, **stealth data collection**, and **dynamic obfuscation**.

**DriftWatch** provides explainable differential behavioural security analysis and supports security-review prioritization. Instead of asking *"Is this single extension version malicious?"*, DriftWatch models updates as differential security feature vectors \( D_t = F(V_t) - F(V_{t-1}) \) relative to historical baselines. A historical baseline is not assumed to be safe.

Core implementation is complete. Independent human review is currently in progress; validation remains pending genuine reviewer submissions. Research-paper preparation and release preparation may proceed without changing frozen research logic. DriftWatch does not claim genuine inter-rater agreement, a real Gold Set, or completed external validation.

See `THREAT_MODEL.md` for the target-system claims boundary and `SECURITY.md` for archive-processing and analysis-host protections.

---

## Core Capabilities (Verified Phase 2)
- **Secure Archive Extraction Sandbox**: Prevents Zip-Slip path traversal, Zip Bomb decompression attacks, symbolic link exploits, and uncompressed size abuse.
- **Manifest Differential Analysis**: Detects added/removed permissions, optional permissions, background service workers, and content scripts across Manifest V2 & V3.
- **Permission Creep Classifier**: Evaluates permission sensitivity across Informational, Low, Moderate, High, and Critical levels.
- **Host Scope Expansion Model**: Quantifies webpage access expansion from single domain paths up to global `<all_urls>` wildcards.
- **Static JavaScript Preprocessing**: Removes JavaScript comments while preserving strings such as `http://127.0.0.1:8000/test`; uploaded extension JavaScript is parsed, never executed.
- **Sensitive API Drift Analysis**: Detects new static calls to browser APIs and network sinks including `chrome.cookies`, `chrome.history`, `fetch`, `XMLHttpRequest`, `WebSocket`, and `navigator.sendBeacon`.
- **Network Endpoint Analysis**: Extracts HTTP(S), WebSocket, domain, IPv4, port, sink-destination, localhost/test, and bounded decoded Base64 endpoint indicators.
- **Obfuscation & Structural Heuristics**: Reports static obfuscation indicators, high-entropy strings, structural drift, and source-to-sink heuristic indicators without claiming confirmed exfiltration.
- **Explainable Risk Scoring Engine**: Calculates normalized risk scores (0-100), risk classifications (`Low`, `Moderate`, `High`, `Critical`), confidence metrics, and human-readable evidence chains.
- **Score Breakdown**: Reports permission, host, API, network, obfuscation, structural, and combination-rule contributions.
- **DriftBench Phase 3A Tooling**: Defines dataset records, label ontology, provenance tracking, metadata validation, controlled synthetic mutations, and leakage-safe splits.
- **DriftBench Phase 3B Feature Pipeline**: Generates versioned feature artifacts for permission-only, manifest+permission, latest-version static, simple differential, and full DriftWatch representations.
- **Phase 3C Pilot Evaluation Harness**: Produces readiness, leakage-audit, deterministic baseline, confusion-matrix, prediction, and blocked-experiment artifacts without fabricating ML metrics.
- **Phase 3D Dataset Curation Intake**: Provides local import manifests, provenance capture, license governance, package hashing, duplicate/split-leakage audits, manual-review records, review queues, label-quality tiers, training eligibility, and dataset manifests for real records.
- **Phase 3E Pilot Empirical Evaluation**: Freezes a real-pilot dataset snapshot, audits leakage and group splits, evaluates the deterministic rule engine, Logistic Regression, and Random Forest across five locked feature representations, and stores research-only model artifacts without production integration.
- **Phase 3F Independent Replication Study**: Expands the real corpus with independent public release assets, preserves Phase 3E as `PILOT_BASELINE`, repeats leakage-safe evaluation, and records an inconclusive decision gate without production ML integration.
- **Phase 3G Dataset Maturation**: Expands the real corpus again, strengthens provenance/review artifacts, preserves Phase 3F as frozen history, regenerates feature artifacts, and keeps ML out of production.
- **Phase 3H Holdout & Gold-Set Readiness**: Expands the real corpus, preserves Phase 3G as frozen history, creates an external replication holdout, and documents that a genuine Gold Set is not yet available.
- **Phase 3H.5 Simulated Review Workflow**: Demonstrates the secondary-review and adjudication workflow with simulated/AI-assisted assessments, preserves external-holdout protection, and keeps genuine Reviewer B, inter-rater agreement, and Gold Set status marked unavailable.
- **Controlled Extension Laboratory**: Pre-packaged synthetic lab samples (`v1_safe_note` and `v2_risky_note`) for reproducible demonstration.
- **Executive Dark-Theme Dashboard**: Polished cybersecurity UI built with FastAPI, Jinja2, custom CSS, and responsive visualization.

---

## System Requirements & Installation

- Python `>=3.10` (project metadata)
- Currently verified research environment: Python `3.14.0` on Windows 11
- See `REPRODUCIBILITY.md`, `ENVIRONMENT_SNAPSHOT.md`, and `requirements-research-lock.txt` for the verification workflow and exact environment snapshot.

### Windows Setup (PowerShell)
```powershell
# Clone or navigate to workspace
cd e:\DriftWatch

# Run setup script (creates .venv and installs requirements)
.\setup_venv.ps1
```

### Manual Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

---

## Running the Application & Tests

### 1. Run Unit & Integration Tests
```powershell
python -m pytest -q
```

### 2. Launch FastAPI Server
```powershell
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```
Navigate to `http://localhost:8000` in your web browser.

### Verified Phase 2 Results
- Full test suite freshly verified on 2026-09-21 at commit `54a4780d58ac12b4c794145b773da5e2c15a6999`: `157 passed`, 0 failed, 0 skipped, and no warnings reported under configured pytest filters.
- Benign control pair (`samples/v1_note_benign.zip` -> `samples/v2_note_benign.zip`): `0.0/100`, `Low`.
- Risky controlled pair (`samples/v1_safe_note.zip` -> `samples/v2_risky_note.zip`): `100.0/100`, `Critical`.
- Scores are generated by the current scoring rules and may change when those rules are revised.

### DriftBench Phase 3A
Phase 3A is implemented as methodology and dataset infrastructure only:
- dataset specification and label ontology
- provenance tracking with archive SHA-256 support
- dataset validator
- controlled mutation framework
- group-aware random and chronological split generation

Phase 3A does not train ML models or claim empirical performance metrics. Later Phase 3E/F experiments are separate research-only evaluations and are not integrated into operational scoring.

### DriftBench Phase 3B
Phase 3B adds deterministic feature extraction and reproducible artifacts:
- versioned feature schema `1.0`
- permission-only baseline features
- manifest+permission baseline features
- latest-version-only static features
- simple differential features
- full DriftWatch behavioural drift features
- explicit analyzer availability flags
- leakage safeguards for target/path-derived fields
- CSV and JSONL artifact writers

Controlled-sample artifacts are generated under `artifacts/driftbench/`. They are descriptive outputs from existing synthetic samples only; no ML training or model-performance metrics are included.

### Phase 3C Pilot Evaluation
Phase 3C adds a reproducible research-evaluation harness under `research/` and writes pilot artifacts to `artifacts/experiments/`.

Current verified pilot inputs contain 2 controlled records, 2 unique extensions, and no real-world records. The leakage audit passed with 43 feature columns audited, 0 violations, and extension group split safety confirmed. The readiness gate blocks ML training because the dataset is too small, has no train/test split assignments, and is entirely controlled/synthetic.

Deterministic baseline outputs are available for pipeline smoke testing only. DriftWatch does not currently claim Logistic Regression, Random Forest, ROC-AUC, PR-AUC, or real-world detector performance.

### Phase 3D Real-Data Intake
Phase 3D adds a safe local curation workflow for lawfully acquired real extension version pairs:

```powershell
.venv\Scripts\python.exe -m driftbench.ingest --manifest datasets\manifests\import_manifest.example.json --dry-run
```

Phase 3D generated truthful empty-intake manifests under `artifacts/driftbench/phase3d/`; Phase 3D.5 and Phase 3D.6 then added the real pilot corpus described below. Existing controlled artifacts remain separate and synthetic.

Unknown sources, unclear licenses, missing provenance, ambiguous identity, malformed packages, and unresolved labels are quarantined or excluded. No extension JavaScript is executed, and ML is not retrained in Phase 3D.

### Phase 3D.6 Real Pilot Corpus
Phase 3D.6 expanded the lawful real pilot corpus from public GitHub release ZIP assets and stabilized label-quality, eligibility, review, split, and readiness metadata.

Current verified real-pilot state:
- Dataset version: `0.1.0-real-pilot`
- Real records: 34
- Unique real extensions: 11
- Labels: `benign_transition=29`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=32`, `UNCERTAIN=2`
- Eligible supervised-training records: 32
- Splits: `train=16`, `validation=12`, `test=6`
- Test eligible labels: `benign_transition=5`, `risky_transition=1`
- Licenses: `Apache-2.0=4`, `GPL-3.0=13`, `MIT=17`
- Leakage audit: passed with 0 protected split violations
- Provenance completeness: 34/34
- Feature extraction: completed for all five Phase 3B representations
- Readiness report: `artifacts/driftbench/real_pilot_readiness.json`

The Phase 3D.6 readiness gate was READY for Phase 3E pilot ML re-evaluation. The two `uncertain` records remain ineligible for supervised training and have review packets under `artifacts/driftbench/real_pilot_review_queue/`.

### Phase 3E Pilot Empirical Evaluation
Phase 3E has now run on the current real pilot corpus. Results remain pilot/preliminary and do not justify production ML integration.

Artifacts:
- `artifacts/experiments/phase3e/`
- `artifacts/models/phase3e/phase3e_real_pilot_v1/`

Frozen Phase 3E dataset:
- Dataset version: `driftbench-real-pilot-phase3e-v1`
- Total records: 34
- Eligible supervised records: 32
- Ineligible records: 2 `uncertain`
- Unique extensions: 11
- Real records: 34
- Controlled records: 0
- Target: `BENIGN` vs `REVIEW_WORTHY`

Phase 3E uses a separate pre-training split, `phase3e-group-safe-label-aware-v1`, because the preserved Phase 3D.6 split had no risky training record. Train/validation/test each contain both binary target classes while preserving extension identity isolation.

Held-out pilot results on 6 test records (`benign_transition=5`, `risky_transition=1`):
- Current deterministic rule scorer: precision `0.20`, recall `1.00`, F1 `0.33`, FPR `0.80`, FNR `0.00`, confusion matrix `tn=1, fp=4, fn=0, tp=1`.
- Full DriftWatch Logistic Regression: precision `0.00`, recall `0.00`, F1 `0.00`, FPR `0.00`, FNR `1.00`, confusion matrix `tn=5, fp=0, fn=1, tp=0`.
- Full DriftWatch Random Forest: precision `0.00`, recall `0.00`, F1 `0.00`, FPR `0.00`, FNR `1.00`, confusion matrix `tn=5, fp=0, fn=1, tp=0`.

Interpretation: the deterministic rule engine catches the single risky held-out transition but currently over-alerts on feature-rich benign updates. The ML models do not yet provide evidence of added operational value. A larger independently reviewed corpus is required before broader claims.

### Phase 3F Independent Replication Study
Phase 3F preserves Phase 3E as `PILOT_BASELINE`, adds independent public GitHub release ZIP assets, and reruns the fixed research evaluation without deploying ML.

Artifacts:
- `datasets/manifests/phase3f_import_manifest.json`
- `artifacts/driftbench/phase3f/`
- `artifacts/driftbench/phase3f_features/`
- `artifacts/experiments/phase3f/`
- `artifacts/models/phase3f/phase3f_replication_v1/`

Verified Phase 3F dataset:
- Dataset version: `driftbench-real-replication-phase3f-v1`
- Real records: 46
- New independent replication records: 12
- Unique extensions: 14
- Labels: `benign_transition=41`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=44`, `UNCERTAIN=2`
- Splits: `train=24`, `validation=12`, `test=10`
- Leakage, duplicate, and provenance audits: passed

Held-out Phase 3F result summary:
- Rule engine: precision `0.111111`, recall `1.0`, F1 `0.2`, FPR `0.888889`, confusion matrix `tn=1, fp=8, fn=0, tp=1`.
- Full DriftWatch Logistic Regression: F1 `0.0`, confusion matrix `tn=9, fp=0, fn=1, tp=0`.
- Full DriftWatch Random Forest: F1 `0.0`, confusion matrix `tn=9, fp=0, fn=1, tp=0`.

Replication conclusion: `INCONCLUSIVE`. Production ML integration remains unjustified; the next evidence-based step is continued dataset expansion and label strengthening.

### Phase 3G Dataset Maturation
Phase 3G is a dataset and ground-truth strengthening phase, not a model-deployment phase.

Artifacts:
- `datasets/manifests/phase3g_import_manifest.json`
- `artifacts/driftbench/phase3g/`
- `artifacts/driftbench/phase3g_features/`
- `artifacts/experiments/phase3g/`

Verified Phase 3G dataset:
- Dataset version: `driftbench-real-maturation-phase3g-v1`
- Real records: 58
- New Phase 3G records: 12
- Unique extensions: 17
- Labels: `benign_transition=53`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=56`, `UNCERTAIN=2`
- Training-eligible records: 56
- Splits: `train=32`, `validation=16`, `test=10`
- Provenance completeness: 58/58
- Timestamp completeness: 58/58
- Duplicate, group leakage, and feature leakage audits: passed

The new accepted records come from Automa, LibRedirect, and Web Scrobbler. uBlacklist candidate assets were excluded after triggering DriftWatch extraction safety controls; the archive protections were not weakened. The two original Save Sora `uncertain` records remain unresolved and training-ineligible, with refreshed review packets.

Phase 3G decision: `DATASET STILL TOO WEAK - CONTINUE EXPANSION`. The corpus improved, but single-reviewer provisional labels still dominate and inter-rater agreement is not available.

### Phase 3H Holdout And Ground-Truth Readiness
Phase 3H is a corpus, review, and holdout-preparation phase. It does not retrain ML, deploy ML, or change production scoring.

Artifacts:
- `datasets/manifests/phase3h_import_manifest.json`
- `artifacts/driftbench/phase3h/`
- `artifacts/driftbench/phase3h_features/`
- `artifacts/experiments/phase3h/`

Verified Phase 3H dataset:
- Dataset version: `driftbench-real-adjudication-holdout-phase3h-v1`
- Real records: 76
- New Phase 3H records: 18
- Unique extensions: 21
- Labels: `benign_transition=71`, `risky_transition=3`, `uncertain=2`
- Label quality tiers: `SINGLE_REVIEWER_PROVISIONAL=74`, `UNCERTAIN=2`
- Gold Set size: 0
- External replication holdout: 10 records across 2 extensions
- Provenance and timestamp completeness: 76/76
- Duplicate, leakage, and feature-leakage audits: passed

The accepted Phase 3H sources are public GitHub release assets for Bitwarden Browser, ClearURLs, HeaderEditor, and Ruffle Web Extension. The holdout is locked for future validation and excluded from non-holdout feature artifacts. Phase 3H decision: `CONTINUE INDEPENDENT LABEL REVIEW / ADJUDICATION`.

### Phase 3H.5 Independent Review Workflow
Phase 3H.5 implements ground-truth qualification infrastructure and a simulated review/adjudication workflow demonstration. It does not train ML, deploy ML, tune thresholds, change production scoring, or create genuine human ground truth.

Artifacts:
- `artifacts/driftbench/phase3h5/`
- `artifacts/experiments/phase3h5/`
- `datasets/reviews/phase3h5/`
- `reviewer_b_blind/`
- `REVIEWER_GUIDE.md`

Verified Phase 3H.5 state:
- Artifact version: `driftbench-independent-review-phase3h5-v1`
- Review scope: 76 Phase 3H records
- Prioritized records: 47
- Genuine Reviewer A records: 0
- Genuine Reviewer B records: 0
- Double-reviewed records: 0
- Genuine adjudicated records: 0
- Inter-rater agreement: not available
- Label quality: `SINGLE_REVIEWER_PROVISIONAL=74`, `UNCERTAIN=2`
- Real Gold Set: 0
- Controlled Gold Set: 0
- Confirmed malicious-transition records: 0

Simulated review/adjudication demonstration:
- 15 simulated/AI-assisted secondary assessments were compared with existing research labels.
- Initial simulated comparison: 2 direct agreements, 13 disagreements, simulated label-match rate `13.33%`.
- The 13 disagreements entered simulated adjudication; this is not genuine human adjudication.
- `clearurls_addon_1_20_0_to_1_21_0` is confirmed as an external holdout and marked `EXTERNAL_HOLDOUT_LOCKED`.
- Excluding that holdout, the simulated 14-record outcome is `RISKY_TRANSITION=7`, `BENIGN_TRANSITION=4`, `UNCERTAIN=3`.

The workflow prepares blind review packets and queues for genuine reviewers. It intentionally does not fabricate independent reviews or treat DriftWatch outputs, simulated assessments, or simulated adjudication outcomes as ground truth. Existing research labels were not automatically overwritten. Current status: Phase 3H.5 simulated review/adjudication workflow demonstration is complete, and external-holdout protection was successfully preserved. Current decision: `MORE INDEPENDENT REVIEW REQUIRED`; Phase 3I is not methodologically ready.

---

## Repository Structure
```
DriftWatch/
|-- app/                    # FastAPI routes, services, models, templates, and static UI
|-- analyzers/              # Manifest, permission, host, API, network, obfuscation, and structure analyzers
|-- risk_engine/            # Deterministic rules, scoring, and explanations
|-- driftbench/             # Dataset schema, intake, validation, governance, and feature extraction
|-- research/               # Offline research evaluation and versioned phase workflows
|-- datasets/               # Manifests plus local/ignored corpus workspaces
|-- artifacts/              # Versioned dataset, feature, experiment, and audit artifacts
|-- reviewer_human_b/       # Scoped independent human-review delivery workspace
|-- reviewer_b_blind/       # Separate simulated/AI-assisted workflow material
|-- samples/                # Controlled laboratory extension pairs
|-- tests/                  # Pytest suite
|-- ARCHITECTURE.md
|-- SECURITY.md             # Analysis-host and archive-processing security boundary
|-- THREAT_MODEL.md         # Target-system research threat model
|-- RESEARCH.md
|-- DATASET_CARD.md
|-- DATA_GOVERNANCE.md
|-- REPRODUCIBILITY.md
|-- ENVIRONMENT_SNAPSHOT.md
`-- DEMO_GUIDE.md
```

---

## Ethical Statement & Limitations
DriftWatch is strictly designed for cybersecurity research, extension security auditing, and academic analysis. Laboratory test samples use synthetic controlled endpoints (`http://analytics.untrusted-domain.com`) and contain no malicious exploits, weaponized payloads, or real user data exfiltration logic. High DriftWatch risk means review-worthy behavioural drift, not malware probability. Source-to-sink results are heuristic indicators for analyst review, not claims of confirmed exfiltration, and obfuscation is contextual evidence rather than proof of maliciousness.
