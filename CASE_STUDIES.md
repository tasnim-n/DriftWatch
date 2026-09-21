# DriftWatch Flagship Case Studies

## Scope and claims boundary

These case studies summarize existing frozen DriftBench artifacts. They do not rerun analyzers, rescore transitions, change labels, or use simulated-review output. Static indicators show where manual security review may be valuable; they do not establish malicious intent, actual data transfer, command-and-control activity, or user harm.

The Phase 3H.5 `priority_score` is a deterministic **review-workflow triage value** that combines static signals with curation/workflow state. It is not the application's 0–100 risk score and is not malware probability. An operational rule-engine score is reported only when a frozen prediction artifact already contains one.

For every case below: **Human review: PENDING**.

## Evidence sources and display conventions

| Source | Role |
|---|---|
| `artifacts/driftbench/phase3h5/review_packets/<record_id>.json` | Blinded static evidence, version metadata, and interpretation boundaries |
| `artifacts/driftbench/phase3h_features/full_driftwatch.csv` | Frozen differential feature values and analyzer-availability flags |
| `artifacts/driftbench/phase3h5/second_review_queue.json` | Deterministic review-workflow priority and signal reasons |
| `artifacts/driftbench/phase3h/dataset_manifest.json` | Frozen provenance, archive hashes, split, and version metadata |
| `artifacts/experiments/phase3e/` and `phase3f/` | Existing held-out deterministic or exploratory-ML outputs, where available |

In proposed figures, a **count** means an analyzer-derived static count, a **deterministic score** names the exact rule or workflow that produced it, an **exploratory ML output** is labeled as a model probability, and any dataset label is explicitly identified as provisional. None of these values is a malware probability.

---

## Case 1 — GitHub Math Display 0.1.0 → 0.2.0

**Record:** `katex-github-chrome-extension_0_1_0_to_0_2_0`  
**Repository:** `github:aaroncql/katex-github-chrome-extension`  
**Why selected:** This is the clearest multi-signal case: manifest capability expansion, a new background worker, host-scope expansion, new API evidence, large network-indicator churn, and a dynamic-execution indicator all occur in one transition. It is also the held-out case for which frozen deterministic and exploratory-ML outputs coexist.

### Observed static evidence

| Capability | V1 state | V2 state | Observed delta |
|---|---|---|---|
| Browser permission | `webNavigation` absent | `webNavigation` present | 1 permission added; permission-risk delta 10 |
| Host access | No `*://*.github.com/*` pattern | `*://*.github.com/*` present | 1 host added; wildcard-host flag 1; host-scope-score delta 90 |
| Background execution | No added background worker | Background worker added | `background_added=true` / service-worker-introduced flag 1 |
| Sensitive APIs | Prior static API state | 1 added API | API-count delta −25; no critical-API-added flag |
| Network indicators | Prior static indicator set | 822 indicators classified as new external additions | Net network-destination-count delta +643 |
| Obfuscation/dynamic execution | Prior indicator set | 1 new dynamic-execution indicator | Obfuscation-count delta +17; added-obfuscation score 530 |
| Structure | Prior structure | 62 added functions and 2 added event listeners | Net function-count delta −90; 2 modified files; no source/sink heuristic |

The addition count and net delta are different measurements: additions and removals can coexist. Network counts describe static indicator output, not verified connections or necessarily unique remote services.

### Deterministic review-priority result

- Phase 3H.5 review-workflow priority: **220**, rank **2 of 47** prioritized records.
- Signal-derived queue reasons include wildcard host expansion, added API use, new external network indicators, a dynamic-execution indicator, and substantial obfuscation change.
- Frozen Phase 3E and Phase 3F held-out rule-engine output: **70.5/100, Critical, REVIEW_WORTHY**. This is deterministic review prioritization, not a maliciousness judgment.
- **Human review: PENDING**.

### Interpretation

The combination of a broader GitHub host pattern, new navigation capability, background execution, and additional static network/dynamic-code evidence makes this transition suitable for focused manual review. A reviewer should connect the manifest changes to release intent and inspect the background code and newly observed destinations.

### Limitations and what DriftWatch cannot conclude

- The static network count does not prove that any endpoint is contacted at runtime.
- The dynamic-execution/obfuscation signal can arise from bundling, minification, or legitimate runtime mechanisms.
- No source-to-sink heuristic was reported for this pair.
- The packet contains no independent public security evidence.
- DriftWatch cannot conclude that the update is malicious, that data was exfiltrated, or that the added GitHub scope is unjustified.

### Suggested visualization

Use a **V1 → V2 → delta capability matrix** for permission, host, background, API, network, obfuscation, and structure. Beside it, use a compact deterministic contribution bar based only on the frozen Phase 3E score breakdown, labeled “deterministic score points.” If exploratory ML is shown, place the Phase 3F Logistic Regression probability `0.332308` and Random Forest probability `0.155` in a separate panel labeled “exploratory held-out model probability,” never on the deterministic-score axis.

### Evidence references

- `artifacts/driftbench/phase3h5/review_packets/katex-github-chrome-extension_0_1_0_to_0_2_0.json`
- `artifacts/driftbench/phase3h_features/full_driftwatch.csv`
- `artifacts/driftbench/phase3h5/second_review_queue.json`
- `artifacts/experiments/phase3f/predictions/rule_engine_full_driftwatch.jsonl`
- `artifacts/experiments/phase3f/error_analysis.json`

---

## Case 2 — Save Sora 2.0.196 → 2.0.355

**Record:** `save-sora_2_0_196_to_2_0_355`  
**Repository:** `github:alpha1337/save-sora`  
**Why selected:** This transition combines a specific new host, API additions, very large network/structural churn, and one source-to-sink heuristic without a permission increase. It demonstrates why manifest-only review is insufficient and why large static counts require context.

### Observed static evidence

| Capability | V1 state | V2 state | Observed delta |
|---|---|---|---|
| Permissions | Existing permission set | Same permission count | No permissions added or removed; permission-risk delta 0 |
| Host access | `https://api.dyysy.com/*` absent | `https://api.dyysy.com/*` present | 1 host added; wildcard-host flag 1; host-scope-score delta 0 |
| Sensitive APIs | Prior API set | 2 added APIs | API-count delta +2; no critical-API-added flag |
| Network indicators | Prior static indicator set | 1,343 indicators classified as new external additions | Net network-destination-count delta +1,052 |
| Obfuscation | Prior indicator set | New indicators produced an added-obfuscation score of 295 | Net obfuscation-count delta −8; no new dynamic-execution indicator |
| Source/sink heuristic | Not represented as a V1 absolute value in the packet | 1 heuristic indicator reported for the comparison | Same-file heuristic only; not confirmed exfiltration |
| Structure/package | Smaller prior package/state | 1,288 added functions and 36 added event listeners | Net function delta +331; 4 modified files; package-size delta +4,655,469 bytes |

### Deterministic review-priority result

- Phase 3H.5 review-workflow priority: **230**, rank **1 of 47** prioritized records.
- Signal-derived queue reasons include wildcard host expansion, API additions, external network additions, one source/sink heuristic, and substantial obfuscation change.
- No held-out operational rule-engine prediction artifact exists for this validation-split row; no application score is inferred or recomputed here.
- **Human review: PENDING**.

### Interpretation

The new host and APIs deserve direct review, while the scale of package, network, and structural churn suggests a large build or feature change. The useful security question is whether the new access and code paths are justified by the update's intended functionality—not whether the raw counts are large in isolation.

### Limitations and what DriftWatch cannot conclude

- Static endpoints can be duplicated across bundles, source maps, generated assets, or dead code; counts do not equal runtime requests.
- The single source/sink indicator is co-occurrence evidence and does not demonstrate a complete data flow.
- A negative net obfuscation-count delta can coexist with newly added indicators; the metrics measure different aspects of churn.
- The packet contains no independent public security evidence.
- DriftWatch cannot conclude that `api.dyysy.com` is harmful, that sensitive data reached it, or that the transition is malicious.

### Suggested visualization

Use a **three-part V1/V2/delta display**: (1) host and permission matrix, (2) API/network counts explicitly labeled “static analyzer counts,” and (3) structural-churn bars for bytes, functions, listeners, and modified files. Add a boxed source/sink evidence card labeled “1 heuristic indicator; not confirmed exfiltration.” Do not use a proportional endpoint graphic that could imply 1,343 runtime connections.

### Evidence references

- `artifacts/driftbench/phase3h5/review_packets/save-sora_2_0_196_to_2_0_355.json`
- `artifacts/driftbench/phase3h_features/full_driftwatch.csv`
- `artifacts/driftbench/phase3h5/second_review_queue.json`
- `artifacts/driftbench/phase3h/dataset_manifest.json`

---

## Case 3 — Refined GitHub 26.6.7 → 26.7

**Record:** `refined_github_26_6_7_to_26_7`  
**Repository:** `github:refined-github/refined-github`  
**Why selected:** This case has no manifest permission or host expansion but still contains API, network, and extensive file-level churn. It is a useful counterexample to the idea that unchanged permissions imply an uninteresting update.

### Observed static evidence

| Capability | V1 state | V2 state | Observed delta |
|---|---|---|---|
| Permissions and hosts | Existing sets | No added or removed permissions/hosts | Permission-risk and host-scope deltas 0 |
| Background/manifest capabilities | Existing manifest state | No new background worker or externally-connectable expansion | No reported expansion in those fields |
| Sensitive APIs | Prior API set | 2 APIs classified as added | API-count delta +3; critical-API-added flag 1 |
| Network indicators | Prior static indicator set | 12 indicators classified as new external additions | Net network-destination-count delta +5 |
| Obfuscation | Prior indicator set | Small set of added indicators | Added-obfuscation score 15; net count delta 0; no dynamic-execution addition |
| Structure/package | Prior structure | 46 added functions and 1 added event listener | Net function delta +8; 164 modified files; package-size delta +7,352 bytes |
| Source/sink heuristic | Prior state | No heuristic indicator reported | Count 0 |

### Deterministic review-priority result

- Phase 3H.5 review-workflow priority: **115**, rank **8 of 47** prioritized records.
- Signal-derived queue reasons include a critical API flag, API additions, new external network indicators, and an obfuscation-change signal.
- No held-out operational rule-engine prediction artifact exists for this training-split row; no application score is inferred or recomputed here.
- **Human review: PENDING**.

### Interpretation

The strongest review question is whether the newly observed critical API use is expected in the release context. The 164 modified files show broad structural churn, but the small package-size and net function changes illustrate why “files modified” is not itself a security verdict.

### Limitations and what DriftWatch cannot conclude

- The artifact identifies a critical-API flag but does not expose an API name in the review packet; this document does not guess it.
- Modified-file count can be driven by formatting, generated output, dependency refreshes, or broad maintenance edits.
- Twelve new external indicators do not prove twelve contacted services.
- The packet contains no independent public security evidence.
- DriftWatch cannot conclude that the API use is abusive or that the broad source change is malicious.

### Suggested visualization

Use a **structural-churn summary** with exact axes and units: modified files (count), package-size delta (bytes), added functions (count), and net function delta (count). Pair it with a small permission/host/API matrix showing “unchanged / unchanged / 2 APIs added.” Avoid a single composite bar because these measures have different units and scales.

### Evidence references

- `artifacts/driftbench/phase3h5/review_packets/refined_github_26_6_7_to_26_7.json`
- `artifacts/driftbench/phase3h_features/full_driftwatch.csv`
- `artifacts/driftbench/phase3h5/second_review_queue.json`
- `artifacts/driftbench/phase3h/dataset_manifest.json`

---

## Case 4 — Browserpass 3.11.0 → 3.12.0

**Record:** `browserpass_browserpass_extension_3_11_0_to_3_12_0`  
**Repository:** `github:browserpass/browserpass-extension`  
**Why selected:** This transition has no permission, host, or API additions but produces strong network, obfuscation/dynamic-execution, and source/sink signals. It is valuable for explaining both the reach and the false-alert risk of static analysis on packaged code.

### Observed static evidence

| Capability | V1 state | V2 state | Observed delta |
|---|---|---|---|
| Permissions and hosts | Existing sets | No added or removed permissions/hosts | Permission-risk and host-scope deltas 0 |
| Sensitive APIs | Prior API set | No API additions | API-count delta 0 |
| Network indicators | Prior static indicator set | 256 indicators classified as new external additions | Net network-destination-count delta +665 |
| Obfuscation/dynamic execution | Prior indicator set | 40 new dynamic-execution indicators | Obfuscation-count delta +79; added-obfuscation score 9,485 |
| Source/sink heuristic | Not represented as a V1 absolute value in the packet | 2 heuristic indicators reported for the comparison | Co-occurrence evidence only; not confirmed exfiltration |
| Structure/package | Prior structure | 83 added functions and 1 added event listener | Net function delta −18; 5 modified files; package-size delta −100,835 bytes |

The frozen artifacts disagree on one non-central field: the Phase 3H feature row records `content_script_changed=1`, while the Phase 3H.5 review packet records `content_scripts_changed=false`. This case study does not resolve or rely on that field; a future artifact-level audit should reconcile the representations without rewriting frozen history.

### Deterministic review-priority result

- Phase 3H.5 review-workflow priority: **105**, rank **14 of 47** prioritized records.
- Signal-derived queue reasons include external network additions, source/sink heuristics, dynamic-execution additions, and substantial obfuscation change.
- No held-out operational rule-engine prediction artifact exists for this training-split row; no application score is inferred or recomputed here.
- **Human review: PENDING**.

### Interpretation

The absence of manifest and API expansion narrows the review focus to packaged-code changes. A reviewer should determine whether build tooling, minification, generated assets, or legitimate application logic explain the dynamic-code and endpoint indicators before escalating the finding.

### Limitations and what DriftWatch cannot conclude

- Dynamic-execution and obfuscation indicators do not establish malicious intent.
- Static endpoint counts may be inflated by bundled or generated code and do not prove communication.
- Same-file source/sink co-occurrence does not establish data flow or exfiltration.
- The content-script-change discrepancy limits conclusions about that field.
- The packet contains no independent public security evidence.
- DriftWatch cannot conclude that Browserpass transmitted credentials, contacted command-and-control infrastructure, or introduced malicious behavior.

### Suggested visualization

Use an **evidence-card group** rather than one aggregate chart: separate cards for network indicators (counts), dynamic execution (counts), obfuscation score (deterministic static feature value), and source/sink heuristics (counts). Add a neutral “manifest/API expansion: none observed” row and an artifact-discrepancy note. Never combine the obfuscation score and counts on one unlabeled axis.

### Evidence references

- `artifacts/driftbench/phase3h5/review_packets/browserpass_browserpass_extension_3_11_0_to_3_12_0.json`
- `artifacts/driftbench/phase3h_features/full_driftwatch.csv`
- `artifacts/driftbench/phase3h5/second_review_queue.json`
- `artifacts/driftbench/phase3h/dataset_manifest.json`

## Cross-case conclusion

The four cases show complementary reasons for review: manifest capability expansion, a new host with large packaged-code churn, API change without permission change, and strong code-level signals without manifest expansion. They also expose why each signal needs context. Across all four cases, **Human review: PENDING**, and no case supports a claim of maliciousness or confirmed exfiltration.
