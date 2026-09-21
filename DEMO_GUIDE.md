# DriftWatch Live Demonstration Guide

Follow this step-by-step guide to demonstrate the completed deterministic DriftWatch analysis pipeline. Research ML artifacts and the ongoing independent human review are separate from this operational workflow.

---

## 1. Setup & Environment Verification
1. Open PowerShell and navigate to `e:\DriftWatch`.
2. Run the environment setup script or activate the virtual environment:
   ```powershell
   .\setup_venv.ps1
   ```
3. Run the automated Pytest suite to confirm all security and drift analysis unit tests pass:
   ```powershell
   .venv\Scripts\python.exe -m pytest -q
   ```

   Freshly verified on 2026-09-21 at commit `54a4780d58ac12b4c794145b773da5e2c15a6999`: `157 passed`, 0 failed, 0 skipped, and no warnings reported under configured pytest filters.

---

## 2. Launching the Web Application
1. Start the FastAPI development server:
   ```powershell
   .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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
   - Review **Recommended Actions**: Hold risky updates for manual security review before browser deployment.
   - State the claims boundary: the score prioritizes review; it is not malware probability, and the static evidence does not prove malicious intent or exfiltration.

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

## 6. Current Research Status

Core implementation is complete. Independent human review is in progress separately, and no genuine reviewer result, inter-rater agreement, Gold Set, or completed external-validation claim should be presented during the demonstration. Existing ML outputs are exploratory research artifacts and are not part of operational scoring.
