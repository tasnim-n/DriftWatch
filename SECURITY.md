# DriftWatch Security Policy & Threat Model

## 1. Threat Model for DriftWatch Self-Protection

DriftWatch processes untrusted third-party archives (ZIP / CRX files) uploaded by users. The ingestion pipeline itself must be protected against malicious inputs targeting the server.

### 1.1 Evaluated Threat Vectors
1. **Zip-Slip (Path Traversal)**: Malicious archives containing filenames such as `../../etc/passwd` or `..\..\Windows\System32\cmd.exe` attempting to write outside the isolated workspace.
2. **Zip Bomb (Decompression Denial of Service)**: Highly compressed archives (e.g., 42.zip) designed to expand into gigabytes of data and exhaust disk space or memory.
3. **Symbolic Link Exploitation**: Archives containing symlinks pointing to sensitive host system files.
4. **Resource Exhaustion**: Archives containing millions of tiny files or huge single files.
5. **Code Execution on Analysis Server**: Uploaded JavaScript files executing during analysis.

---

## 2. Defensive Controls Implemented

### 2.1 Storage & Unpacking Sandbox
- `app/core/security.py` enforces strict workspace bounds using absolute path resolving (`os.path.abspath`).
- Disallows symbolic links (`is_symlink` validation).
- Enforces strict upper limits:
  - `MAX_UPLOAD_SIZE`: 25 MB
  - `MAX_EXTRACTED_SIZE`: 100 MB
  - `MAX_COMPRESSION_RATIO`: 10.0
  - `MAX_FILE_COUNT`: 1000 files
- Deletes unpacked temporary files automatically upon analysis completion or failure.

### 2.2 Static Analysis Execution Safety
- All JavaScript analysis is strictly static lexical / regex / string parsing.
- Uploaded extension code is **NEVER executed or evaluated** on the host server.
- Web UI serves sanitized data; user inputs and extracted strings are escaped before template rendering.

### 2.3 Static Decoding Limits
- DriftWatch may attempt bounded static decoding of Base64-like string literals.
- Encoded candidates are ignored if they are too short, too large, invalid Base64, not UTF-8 text, or decode to content larger than the configured static limit.
- Decoded content is scanned only as text for URLs, domains, IPs, and related endpoint indicators.
- DriftWatch never executes decoded content and never emulates extension runtime behavior.

### 2.4 Network Analysis Limitations
- Network extraction is static and best-effort. It detects direct URL strings, WebSocket strings, IPv4 addresses, domains in string/decoded contexts, and direct `fetch`, `XMLHttpRequest.open`, `WebSocket`, and `navigator.sendBeacon` destinations.
- Dynamically constructed URLs, encrypted payloads, remote configuration, or endpoints produced by arbitrary runtime logic may not be resolved.
- Local/test endpoints such as `localhost`, `127.0.0.1`, `::1`, `.local`, and controlled sample domains are recorded as behavioral destinations but are not described as malicious infrastructure.
- Oversized non-manifest JSON data files are not scanned for network indicators during static corpus analysis. This prevents large bundled rule/data files from dominating analysis while preserving JavaScript and manifest scanning.

### 2.5 Source-to-Sink Heuristic Limits
- Source-to-sink results are heuristic indicators within the same file.
- They do not prove confirmed exfiltration, data theft, intent, or exploitability.
- Findings are intended to prioritize analyst review with file, line, source, and sink evidence where practical.

### 2.6 Partial Analysis Behavior
- Core archive, manifest, and package validation failures stop analysis because the version comparison cannot be trusted.
- Optional Phase 2 analyzer failures are captured in the report as analyzer-specific errors. Remaining analyzers continue and produce partial results.

### 2.7 Trust Boundary
Uploaded archives, manifests, JavaScript, decoded strings, and derived indicators are untrusted input. They must remain inside the extraction and static-analysis boundary and must not be executed by DriftWatch.

### 2.8 DriftBench Controlled Mutations
- Controlled mutations are synthetic laboratory examples for research methodology.
- Generated mutation snippets use controlled localhost/test endpoints and sample text only.
- Mutation tooling must not create deployable credential theft, live exfiltration, exploit payloads, or real malware.
- Dataset validation and split generation operate on metadata and archive hashes only; they do not execute extension JavaScript.

### 2.9 DriftBench Feature Extraction Safety
- Feature extraction validates DriftBench records before unpacking archives.
- Archive paths are resolved under the configured DriftBench base directory; absolute paths outside that directory are rejected.
- Archives are unpacked through the same secure extraction boundary used by the application.
- Feature extraction reuses static analyzers and never executes extension JavaScript or decoded payloads.
- Labels, label rationales, split assignments, final risk scores, recommendations, and path/class-name strings are excluded from feature columns to reduce target leakage.
- Raw extracted feature values are not globally normalized. Normalization must occur later inside training pipelines using training data only.

### 2.10 Phase 3D Real-Data Intake Safety
- Phase 3D supports local import-manifest curation and dry-run validation. It does not require live internet access for reproducibility.
- Imported packages are treated as hostile archives. DriftWatch computes SHA-256 hashes, checks archive readability, validates `manifest.json`, and records provenance without installing or launching extensions.
- Unknown/unverified sources and unclear/disallowed license states are quarantined or excluded rather than silently accepted.
- Extension identity and version ordering must be defensible. Ambiguous pairs are not accepted into the research-ready dataset.
- Duplicate and split-leakage reports are generated before future training can rely on a dataset.
- DriftWatch does not compute a normalized extracted-package hash in Phase 3D because extracted package directories are transient static-analysis workspaces, not published dataset artifacts.

### 2.11 Phase 3D.5 Acquisition Safety
- Public acquisition uses ordinary HTTPS only, with safe URL validation, timeout support, filename sanitization, and a 20 MB per-package download cap in the acquisition helper.
- Downloaded packages are stored as raw hostile files and are never installed or executed.
- Normalized analysis ZIPs are layout/compression rewrites for static analysis compatibility only; raw package hashes remain preserved.
- Packages that cannot pass extraction safety checks must be excluded or normalized safely, not force-extracted.
- No Phase 3D.5 workflow contacts endpoints embedded inside extensions.

### 2.12 Phase 3D.6 Real-Pilot Expansion Safety
- Phase 3D.6 imports only public open-source release assets with recorded source URLs, timestamps, raw SHA-256 hashes, normalized SHA-256 hashes, licenses, and label provenance.
- The archive file-count cap is 1000 files. Size, extracted-size, compression-ratio, Zip-Slip, and symlink protections remain enforced.
- Label quality tiers and supervised-training eligibility are metadata only. They are preserved in feature artifacts as metadata and excluded from predictive feature columns.
- Review packets and adjudication templates support second-reviewer workflows without fabricating reviewer agreement.
- Phase 3D.6 performs no ML training and reports no model-performance metric.

### 2.13 Phase 3E Research Model Safety
- Phase 3E model artifacts are generated locally from the frozen DriftBench pilot feature snapshot and stored under `artifacts/models/phase3e/`.
- These artifacts are research outputs only. They are not loaded by the FastAPI application and do not replace the deterministic production risk scorer.
- DriftWatch must not load arbitrary or user-supplied pickle/joblib model files. Serialized model loading is permitted only for locally generated, trusted research artifacts during controlled experiments.
- Model training uses numeric feature columns only. Labels, review status, eligibility flags, split assignments, paths, final risk scores, rule severities, and recommendations remain metadata and are excluded from training matrices.
- Phase 3E does not execute extension JavaScript, decoded strings, or model-derived code.
