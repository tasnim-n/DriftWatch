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
  - `MAX_FILE_COUNT`: 500 files
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
