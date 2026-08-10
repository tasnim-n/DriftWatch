# DriftWatch Live Demonstration Guide

Follow this step-by-step guide to run the live demonstration for DriftWatch Phase 2.

---

## 1. Setup & Environment Verification
1. Open PowerShell and navigate to `e:\DriftWatch`.
2. Run the environment setup script or activate the virtual environment:
   ```powershell
   .\setup_venv.ps1
   ```
3. Run the automated Pytest suite to confirm all security and drift analysis unit tests pass:
   ```powershell
   .venv\Scripts\pytest.exe tests\ -v -W default
   ```

---

## 2. Launching the Web Application
1. Start the FastAPI development server:
   ```powershell
   .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
   ```
2. Open your web browser and navigate to:
   `http://localhost:8000`

---

## 3. Executive Demo Walkthrough
1. **Landing Page**: View the executive overview of DriftWatch, explaining why version-to-version behavioral comparison outperforms static permission checks.
2. **New Analysis Form**:
   - Upload **Previous Version (V1)**: Browse and select `samples/v1_safe_note.zip` (or zip `samples/v1_safe_note/`).
   - Upload **Updated Version (V2)**: Browse and select `samples/v2_risky_note.zip` (or zip `samples/v2_risky_note/`).
   - Click **Run Differential Security Analysis**.
3. **Audit Findings & Report**:
   - Observe the actual risk score generated during the live demonstration.
   - The controlled risky sample is expected to produce a High or Critical classification based on the current verified scoring rules.
   - Verified on current project test run (2026-08-10): `100.0/100`, `Critical`. Scores may change if scoring rules change.
   - Observe **Host Scope Expansion**: Expansion detected from `https://notes.local/*` to `<all_urls>`.
   - Observe **Permission Creep**: Added sensitive permissions `cookies` and `history`.
   - Observe **Sensitive API Drift**: New static API calls such as `chrome.cookies`, `chrome.history`, and `fetch`.
   - Observe **Decoded Static Endpoint Indicator**: A bounded static Base64 decode identifies the controlled endpoint `http://analytics.untrusted-domain.com/collect`.
   - Observe **Source-to-Sink Heuristic**: A heuristic indicator links sensitive sources and outbound sinks within `background.js`; this is not proof of confirmed exfiltration.
   - Observe **Service Worker Addition**: Background worker added for telemetry.
   - Review **Recommended Actions**: Immediate block or security audit required before browser deployment.

## 4. Benign Control Run
Use `samples/v1_note_benign.zip` as V1 and `samples/v2_note_benign.zip` as V2.

- Verified on current project test run (2026-08-10): `0.0/100`, `Low`.
- This control pair should not produce a Critical result.

## 5. DriftBench Phase 3A Verification
Phase 3A adds dataset methodology and tooling only. Run:

```powershell
.venv\Scripts\pytest.exe tests\test_driftbench_phase3a.py -v -W default
```

This verifies label ontology, provenance validation, leakage-safe splits, and controlled synthetic mutations. It does not train ML models.
