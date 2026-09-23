# DriftWatch Academic Demonstration Guide

## Demonstration objective

This 5–7 minute demonstration shows how DriftWatch compares two Chromium-extension versions, identifies security-sensitive behavioural drift, and presents explainable evidence for manual review.

Use these claims consistently:

- DriftWatch detects **behavioural drift** between versions.
- It does **not** prove malicious intent.
- Risk score means **manual security-review priority**, not malware probability.
- ML experiments are **research-only** and do not feed the operational score.
- The scoped independent human review and adjudication are **complete**; the resulting agreement and Gold Set are limited validation evidence, and external validation remains incomplete.

## Pre-demonstration preparation

From the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Confirm these four controlled sample archives exist:

- `samples/v1_note_benign.zip`
- `samples/v2_note_benign.zip`
- `samples/v1_safe_note.zip`
- `samples/v2_risky_note.zip`

The implementation baseline was freshly verified at `157 passed` before this documentation-only phase. The current Phase 2 UI commit is `e50e170b62b2f3ab16c65891c226a34e52d7b372`.

## Timed 5–7 minute script

### 0:00–0:45 — Problem and motivation

**Show:** Landing page and the V1 + V2 → behavioural-change flow.

**Say:**

> Browser extensions update continuously. A single-version scan can miss the security significance of what changed. DriftWatch compares a previous version, V1, with an updated version, V2, and highlights security-sensitive behavioural drift for a human reviewer. It is an explainable prioritization framework, not a malware detector.

Point out that a historical baseline is not assumed to be safe; it is simply the comparison state.

### 0:45–1:30 — What DriftWatch analyzes

**Show:** The two upload controls.

**Say:**

> Both ZIP archives are validated and securely extracted. Extension JavaScript is never executed. Static analyzers inspect manifest permissions, host scope, package structure, browser APIs, endpoint indicators, obfuscation signals, and source/sink co-occurrence. DriftWatch constructs V1 and V2 feature states, derives their delta, applies deterministic rules and weights, and generates evidence for review.

State explicitly that exploratory ML is not in this live pipeline.

### 1:30–3:30 — Live V1/V2 analysis

**Action:**

1. Upload `samples/v1_safe_note.zip` as **Previous Version (V1)**.
2. Upload `samples/v2_risky_note.zip` as **Updated Version (V2)**.
3. Click **Compare V1 and V2**.

**While the report loads, say:**

> This is a controlled synthetic example. It is designed to exercise the analysis path safely and contains no weaponized payload or real user-data exfiltration.

**On the report, point out:**

- the exact versions compared;
- the overall review-priority classification;
- the visible statement that the score is not malware probability;
- added `cookies` and `history` permissions;
- host expansion from `https://notes.local/*` to `<all_urls>`;
- new API evidence such as `chrome.cookies`, `chrome.history`, and `fetch`;
- the statically decoded controlled endpoint `http://analytics.untrusted-domain.com/collect`;
- the new background worker; and
- the source/sink heuristic in `background.js`.

Use the actual score shown on screen. The current controlled pair is expected to produce a Critical review-priority result, but do not present that as proof of maliciousness.

### 3:30–4:45 — Evidence Cards and behavioural drift

**Show:** V1 → V2 summary and two or three Evidence Cards.

**Say:**

> The primary unit of explanation is the behavioural change. Each card shows the previous state, updated state, observed static evidence, why the change matters, and a recommended reviewer action. Category-specific cautions prevent over-interpretation.

For the network card:

> Static endpoint evidence does not prove malicious communication.

For the source/sink card:

> Heuristic source/sink co-occurrence does not prove exfiltration.

For obfuscation, if shown:

> Obfuscation or minification indicators do not establish malicious intent.

Briefly show **Analyzer Completeness**. Explain that execution coverage reports which optional analyzers completed; missing evidence must not be interpreted as safety.

### 4:45–5:30 — Review-priority interpretation

**Show:** Deterministic score breakdown.

**Say:**

> The score combines fixed security-signal contributions and deterministic rules. It answers “How urgently should a reviewer inspect this update?” It does not estimate the probability that the extension is malware. A high score supports triage; a low score does not certify safety.

Open the advanced technical details only briefly to show that the raw differential vector and archive hashes remain available for reproducibility.

### 5:30–6:15 — Separate operational analysis from research evaluation

**Show:** The operational/research architecture diagram in `ARCHITECTURE.md`, or a prepared screenshot of it.

**Say:**

> The live application is deterministic. Separately, DriftBench supports dataset curation, exploratory ML experiments, human review, and a protected external holdout. Research ML predictions do not feed the live score. Existing ML results are preliminary and research-only. The scoped independent human review and adjudication workflow is complete, with 9/14 exact agreement and a separate four-record, single-class Gold Set. These results do not establish accuracy, objective ground truth, or completed external validation.

If time permits, mention the KaTeX case from `CASE_STUDIES.md`: the deterministic system prioritized a multi-signal transition that both exploratory pilot models missed. Describe this as one provisional held-out observation, not proof that ML is generally inferior.

### 6:15–7:00 — Limitations and conclusion

**Say:**

> DriftWatch is static and pairwise. Bundled code can inflate endpoint, obfuscation, and structural counts. Source/sink findings are heuristic. Legitimate feature updates can add sensitive capabilities, and an unsafe baseline can make a delta look small. Most frozen corpus labels remain single-reviewer provisional despite the completed scoped human-validation workflow.

Close with:

> DriftWatch's contribution is transparent, version-aware security-review prioritization: it makes important changes visible and auditable while leaving intent and final disposition to evidence-based human review.

## Demo case selection

| Role | Transition | Why suitable | Expected report characteristics | What to emphasize | Demo risk or failure mode |
|---|---|---|---|---|---|
| Simple / low drift | `samples/v1_note_benign.zip` → `samples/v2_note_benign.zip` | Fast controlled comparison with no major security expansion | Low review priority; no permission or host expansion; few or no Evidence Cards | Low priority is not approval or a safety certificate | An empty findings section can appear visually less dramatic; explain that absence of observed drift is not proof of safety |
| Meaningful / high drift | `samples/v1_safe_note.zip` → `samples/v2_risky_note.zip` | Controlled example exercises permissions, host scope, APIs, network, background, decoding, and source/sink evidence | Critical review priority expected; several Evidence Cards and deterministic contributions | Claims disclaimer, V1/V2 changes, evidence location, category cautions | Presenting the synthetic endpoint as real malicious infrastructure would be misleading; identify it as controlled test data |
| Backup / real transition | `datasets/validated/real_pilot_packages/katex-github-chrome-extension_v0.1.0.zip` → `datasets/validated/real_pilot_packages/katex-github-chrome-extension_v0.2.0.zip` | Existing public-release pair with broad host, permission, background, network, and obfuscation drift | Rich multi-signal report; frozen held-out artifact records deterministic 70.5/100 Critical prioritization | Difference between deterministic evidence and exploratory ML output; provisional nature of research labels | Larger archives may take longer; endpoint counts may be visually dominant and require the static-count caveat; use the actual live score rather than promising an exact result |

Do not modify these examples for the presentation. Verify the local archive paths during rehearsal.

## Demo fallback plan

### Prepare before the session

Capture screenshots from actual generated reports at the current commit:

1. Landing page with V1/V2 controls.
2. Report header, versions, priority, and claims disclaimer.
3. V1 → V2 behavioural-change summary.
4. Representative permission/host, network, and source/sink Evidence Cards.
5. Analyzer Completeness and deterministic score breakdown.
6. Operational/offline architecture diagram.

Record the transition, commit, and capture date beside the screenshots. Do not edit displayed scores.

The application has no native report-export or PDF feature. A saved HTML fallback is feasible only by using the browser's **Save Page Complete** function and testing the saved page with its stylesheet/assets before the session. Alternatively, retain the application database and report URL, keep the local server available, and reopen the existing report.

### If live upload or analysis fails

1. State that the live path normally performs secure extraction, version-level static analysis, differential construction, deterministic scoring, explanation generation, and persistence.
2. Switch to the prepared high-drift report screenshots or tested saved HTML.
3. Walk through the same versions, disclaimer, behavioural summary, Evidence Cards, completeness section, and technical details.
4. If time and the application permit, try the smaller benign control pair.
5. If the controlled pair remains unavailable, use the prepared KaTeX case-study materials rather than improvising a result.

### Key fallback talking points

- The evidence shown was generated from the named V1/V2 pair; it is not fabricated for the presentation.
- The score is deterministic review priority, not malware probability.
- Static endpoints do not prove communication.
- Source/sink co-occurrence does not prove exfiltration.
- ML is research-only and disconnected from live scoring.
- Human-review agreement and adjudication are descriptive evidence, not classifier accuracy or objective ground truth.

## Presenter claims checklist

Before the demonstration, confirm that the script and slides do not claim:

- that any case is a malicious extension;
- that a risk score is malware probability;
- proven exfiltration or command-and-control;
- reviewer agreement or Gold Set membership as proof of accuracy, maliciousness, prevalence, or generalization;
- completed external validation; or
- native PDF export.

The defensible current statement is: DriftWatch detects and explains security-sensitive behavioural drift to prioritize manual review. Scoped independent human validation is complete, while external validation and population-level performance evidence remain incomplete.
