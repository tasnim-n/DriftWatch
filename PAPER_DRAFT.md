# DriftWatch: Explainable Differential Behavioural Analysis for Security-Review Prioritization of Browser-Extension Updates

> **Provisional research-paper scaffold.** This draft is grounded in the current DriftWatch repository and frozen research artifacts. Independent human validation and the literature review are incomplete. Claims and section status must be re-audited before submission.

## 1. Title

**DriftWatch: Explainable Differential Behavioural Analysis for Security-Review Prioritization of Browser-Extension Updates**

This title emphasizes the implemented unit of analysis—an extension-version pair—and the system's purpose: explainable prioritization of manual security review. It deliberately avoids positioning DriftWatch as an antivirus product or a malicious-extension classifier.

## 2. Abstract

Browser extensions evolve through frequent updates that can alter permissions, host access, browser-API use, network indicators, background execution, code structure, and obfuscation characteristics. Security analysis of a single extension snapshot does not directly express which capabilities or behaviours changed between releases. We present DriftWatch, a static differential analysis framework that compares a previous Chromium-extension archive, (V_{t-1}), with an updated archive, (V_t). DriftWatch securely extracts both archives, constructs version-level feature states, derives heterogeneous differential features, applies a deterministic multi-signal risk engine, and produces analyst-facing evidence and recommendations. Its score represents manual security-review priority, not malware probability.

The current governed DriftBench corpus contains 76 real version-pair transitions from 21 open-source extensions: 71 provisionally benign, 3 provisionally risky, and 2 uncertain. After uncertainty and protected-holdout restrictions, 64 records are eligible for supervised research use; 10 records remain isolated in an external holdout. Preliminary evaluation includes a fixed deterministic rule baseline and exploratory Logistic Regression and Random Forest experiments. Across the small held-out sets, the deterministic system identified the single provisionally review-worthy transition but generated many alerts on provisionally benign, feature-rich updates, while the exploratory models often missed that transition. These observations are not sufficient for population-level performance or production-ML claims. Independent human validation is ongoing, labels remain predominantly single-reviewer provisional, no genuine Gold Set is available, and the protected external holdout has not undergone formal external validation. DriftWatch therefore demonstrates a functional and explainable approach to version-aware security-review prioritization while leaving malicious intent and final disposition to evidence-based human assessment.

## 3. Introduction

Browser extensions occupy a privileged position between users, webpages, and browser APIs. Their functionality and security exposure can change over time as maintainers add features, update dependencies, modify build pipelines, transfer ownership, or respond to platform changes. A reviewer examining only the latest package sees its current capabilities but may not see the security significance of the update itself: a new permission, broader host pattern, newly introduced background worker, sensitive API, encoded endpoint, or structural data-flow indicator.

DriftWatch treats the transition between versions as the primary object of analysis. Given a historical version (V_{t-1}) and update (V_t), it derives security-relevant observations for each version and expresses the change as a differential representation. This representation combines set changes, count deltas, Boolean events, scope expansions, and structural indicators. A deterministic risk engine converts those signals into a review-priority score and an explanation report. The score does not estimate maliciousness; it helps an analyst decide where review effort is most warranted.

The framework also separates operational analysis from offline research. The live FastAPI application uses deterministic analyzers and scoring only. DriftBench, exploratory machine-learning experiments, independent review, and the protected external holdout reside in a separate research lane and do not feed runtime scores. This separation supports reproducibility and reduces the risk that provisional labels or holdout observations influence operational rules.

This work makes the following repository-supported contributions:

1. A secure, static framework for comparing two supplied Chromium-extension archives.
2. A structured multi-signal representation of permission, host, API, network, obfuscation, package, manifest, and structural drift.
3. A deterministic explanation and review-priority engine with evidence, V1/V2 context, category-level contributions, and analyst recommendations.
4. DriftBench, a governed version-pair corpus with provenance, version ordering, label-quality, eligibility, split, leakage, and analyzer-availability metadata.
5. A protected external-holdout policy and blind independent-review protocol designed to prevent training, tuning, and ground-truth leakage.
6. Preliminary deterministic and exploratory-ML evaluations accompanied by failure analysis and explicit threats to validity.

These are implementation and methodology contributions. Novelty relative to prior literature remains subject to a completed literature review.

## 4. Motivation

Traditional snapshot-oriented analysis asks what an extension can do at one point in time. Update review instead asks what changed, whether the change expands security exposure, and whether the available evidence justifies deeper inspection. The distinction matters because broad capability may be longstanding, while a small textual update can introduce a high-impact privilege or new communication path. Conversely, large generated-file changes can produce many static indicators without corresponding harmful behaviour.

Differential analysis provides a natural organizing principle for this review problem. It focuses attention on added and removed capabilities, relates evidence to a specific release transition, and can support explanations such as “host access expanded from a domain-specific pattern to a wildcard” rather than “the extension has host access.” This framing may improve reviewer efficiency and accountability, but its relationship to established browser-extension analysis, security regression analysis, and software-evolution research requires literature validation. [CITATION REQUIRED: empirical or conceptual work on security-sensitive software evolution and update review]

The practical motivation is prioritization under uncertainty. Static analysis cannot establish intent, and security teams cannot manually inspect every update at equal depth. A transparent prioritizer can expose why an update was raised, preserve raw evidence for reproducibility, and allow analysts to distinguish legitimate feature growth from changes requiring escalation.

## 5. Research Questions

The paper adopts the research questions defined in `RESEARCH.md`:

- **RQ1:** Can version-to-version behavioural-difference features detect risky browser-extension updates more effectively and explainably than permission-only analysis or analysis of only the latest version?
- **RQ2:** Which behavioural-drift categories—permission, host scope, sensitive API, network, obfuscation, and structure—contribute most significantly to risk detection?
- **RQ3:** Can extension-specific baselines, using (V_{t-1}) as the reference for (V_t), reduce false-positive rates compared with absolute global thresholds?
- **RQ4:** Does chronological evaluation provide a more realistic performance estimate for browser-update monitoring than random dataset splitting?
- **RQ5:** Can explainable risk reports provide security analysts with actionable visual evidence for efficiently auditing complex updates?

The present evidence does not resolve all five questions. RQ1–RQ4 remain limited by corpus size, imbalance, provisional labels, and small held-out sets. RQ5 requires genuine human-review evidence that is still pending.

## 6. Related Work

This section is a structure for a formal literature review; it does not assert novelty. DriftWatch is positioned as a version-pair, security-sensitive change-analysis and review-prioritization framework rather than solely a classifier of a single extension snapshot.

### 6.1 Browser-extension security analysis

Summarize studies of extension privilege, content-script isolation, browser-API misuse, data access, remote communication, and ecosystem-scale security measurement. Establish common threat models and units of analysis. [CITATION REQUIRED: peer-reviewed browser-extension security surveys and empirical ecosystem studies]

### 6.2 Static analysis of browser extensions

Review manifest analysis, JavaScript static analysis, taint/data-flow techniques, API-use extraction, and extension-specific program models. Compare semantic depth, scalability, and handling of bundled code. [CITATION REQUIRED: primary papers on static or hybrid analysis of browser extensions]

### 6.3 Permission-based security analysis

Review permission models, over-privilege, host permissions, permission warnings, and longitudinal permission change. Position permission drift as one signal family rather than a complete security verdict. [CITATION REQUIRED: browser permission-system and over-privilege studies]

### 6.4 Behavioural, change, and differential analysis

Survey work that compares program versions, models behavioural deltas, or detects security-relevant change. Determine whether prior extension work explicitly uses consecutive version pairs and heterogeneous feature deltas. [CITATION REQUIRED: differential program analysis and behavioural change-detection research]

### 6.5 Software evolution and security regression

Review research on vulnerability introduction, regression detection, dependency changes, supply-chain compromise, and update risk. Connect extension updates to broader software-evolution methodology without assuming equivalence. [CITATION REQUIRED: security regression and software-update security literature]

### 6.6 Explainable security analysis

Review evidence-centered security tooling, interpretable alerts, explanation quality, analyst decision support, and limitations of post-hoc explanation. Relate these ideas to DriftWatch's direct mapping from deterministic signals to evidence cards. [CITATION REQUIRED: explainable cybersecurity and analyst-facing alert explanation studies]

### 6.7 Security prioritization and deterministic risk scoring

Review rule-based prioritization, transparent risk scoring, alert triage, calibration, and the danger of interpreting ordinal/heuristic scores as probabilities. [CITATION REQUIRED: security alert prioritization and transparent risk-scoring methods]

### 6.8 ML-based malicious-extension detection

Review feature representations, supervised targets, dataset construction, temporal evaluation, imbalance handling, calibration, and leakage risks in malicious-extension classifiers. Contrast those goals with DriftWatch's operational review-priority objective and research-only ML lane. [CITATION REQUIRED: peer-reviewed malicious-extension detection and dataset papers]

### 6.9 Positioning statement

DriftWatch is positioned as an explainable differential framework centered on security-sensitive change between supplied extension versions. It combines version-aware evidence, deterministic triage, dataset governance, and a blind-review protocol. The claim that this combination is novel must remain provisional until the literature plan in `LITERATURE_REVIEW_PLAN.md` is completed.

## 7. System Overview

The operational pipeline is:

\[
V_{t-1}, V_t
\rightarrow \text{secure validation and extraction}
\rightarrow \text{version-level static analysis}
\rightarrow F(V_{t-1}), F(V_t)
\rightarrow D_t
\rightarrow \text{deterministic scoring}
\rightarrow \text{explanation}
\rightarrow \text{persistence and report}
\]

The web application accepts two ZIP archives through FastAPI. `SecureExtractor` enforces archive-size, extracted-size, compression-ratio, entry-count, path-traversal, and link protections. Extraction occurs in separate temporary workspaces, which are cleaned after analysis. DriftEngine coordinates package, manifest, permission, host-scope, API, network, obfuscation, and structural analyzers without executing extension JavaScript.

The engine constructs version-level feature states and a differential representation. The deterministic scorer combines fixed signal contributions and combination rules into a 0–100 review-priority score and `Low`, `Moderate`, `High`, or `Critical` classification. The explanation layer produces findings, evidence, V1/V2 context, interpretation cautions, and reviewer actions. Results are persisted as an `AnalysisRecord` and exposed through an HTML report and JSON API.

Offline research is architecturally separate. DriftBench datasets and feature artifacts support deterministic evaluation and exploratory ML experiments. Blind human review and the protected holdout are research-governance mechanisms. The runtime application does not load ML models, provisional labels, reviewer submissions, or holdout decisions.

**Planned paper figure:** redraw the two-lane diagram from `ARCHITECTURE.md`, with no arrow from research ML to operational scoring.

## 8. Threat Model

### Target system and scenarios

DriftWatch targets supplied pairs of Chromium-style extension archives and supports implemented Manifest V2 and V3 fields. Relevant change scenarios include benign feature growth, accidental capability expansion, dependency or build compromise, maintainer-account compromise, ownership transfer, and intentionally harmful updates. Static drift does not determine which scenario occurred.

### Baseline assumption

(V_{t-1}) is historical, not trusted safe. Harmful behaviour present and materially unchanged in both versions may produce little or no drift. Skipped intermediate releases, reversed pairs, repackaging, or incorrect version identity can also distort interpretation.

### Observability

Observable signals include selected manifest changes, permission and host-scope drift, statically visible browser APIs and endpoints, bounded decoded endpoint indicators, obfuscation and dynamic-code indicators, package and source structure, and same-file source/sink heuristics.

### Evasion and false-negative mechanisms

The system may miss time-, user-, site-, locale-, or environment-dependent behaviour; remote activation; runtime string or endpoint construction; downloaded code; encrypted payloads; indirect or cross-file flows; WebAssembly semantics; and server-side behaviour. Static parsing and analyzer failures can also reduce evidence.

### False-positive mechanisms

Legitimate bundling, minification, telemetry, dependency updates, embedded lists, test endpoints, generated resources, and broad but justified features can raise review-priority signals. Same-file source/sink co-occurrence may lack a feasible data flow.

### Claims boundary

DriftWatch can state that security-sensitive behavioural drift was observed and should be reviewed. It cannot state that an extension is malicious, that an endpoint was contacted, or that data was exfiltrated. Low priority does not certify safety, and high priority is not malware probability.

## 9. Methodology

DriftWatch compares two validated archive workspaces using deterministic static analyzers. The analysis records observations and then separates those observations from their security interpretation.

| Signal family | Observed signal | Permitted interpretation |
|---|---|---|
| Manifest | Added/removed fields, background or content-script changes, externally-connectable or resource changes | Configuration changed; review purpose and exposure |
| Permissions | Added/removed required or optional permissions and sensitivity metadata | Capability expanded or contracted; determine proportionality |
| Host scope | Added host patterns, wildcard or global access, scope-score delta | Webpage reach expanded; inspect whether scope is necessary |
| Sensitive APIs | Newly observed browser/API call patterns with file and line evidence | New code-level capability appears; inspect call sites |
| Network | New static URLs, domains, IPs, sink destinations, or decoded indicators | Potential communication surface changed; runtime communication is unproven |
| Obfuscation | Added dynamic-code, encoding, entropy, or binary indicators | Reviewability changed; intent is unproven |
| Structure | Added functions/listeners, modified files, and package-size changes | Code organization or scale changed; semantics require review |
| Source/sink | Sensitive-source and outbound-sink co-occurrence within one file | Heuristic review lead; not a proven flow or exfiltration path |

Required package/manifest processing must succeed for a meaningful comparison. Optional code analyzers are isolated so one failure can yield a partial report with explicit completeness metadata rather than silently converting unavailable evidence into a negative finding.

The method does not execute uploaded JavaScript, install the extension, emulate a browser, or observe live traffic. Explanations retain archive hashes, evidence text, category, severity, finding confidence, previous/new values when available, and recommended reviewer actions.

## 10. Differential Feature Representation

Let (F(V)) denote the heterogeneous security feature state extracted from version (V). DriftWatch models the transition as:

\[
D_t = F(V_t) - F(V_{t-1}).
\]

The subtraction symbol is conceptual and feature-specific. It does not imply that every feature is a scalar suitable for ordinary arithmetic. Implemented differential forms include:

- **Set differences:** added or removed permissions, host patterns, APIs, files, or indicators.
- **Count differences:** permission, host, file, size, API, network, obfuscation, and function-count deltas.
- **Boolean transition events:** global host expansion, background-worker introduction, content-script change, or critical-API addition.
- **Ordinal or weighted changes:** permission-risk and host-scope-score deltas.
- **Structural evidence:** added functions/listeners and same-file source/sink findings.
- **Availability metadata:** whether optional analyzers completed and whether evidence is partial.

The research pipeline exposes five locked representations: permission-only, manifest plus permission, latest-version-only static, simple differential, and full DriftWatch behavioural drift. Metadata, labels, paths, split identity, final risk score, severity, and recommendation are separated from model features to reduce leakage.

## 11. Deterministic Risk Engine

The operational risk engine is deterministic. It combines fixed contributions from permission, host, API, network, obfuscation, and structural signal families with fixed combination rules. The resulting value is capped on a 0–100 scale and mapped to `Low`, `Moderate`, `High`, or `Critical` review-priority categories. Explanations connect contributing signals to evidence and reviewer actions.

“Multi-signal” or “hybrid” in this context refers to deterministic signal combination, not a production ML ensemble. The score is not calibrated as malware probability. The separate completeness score reflects optional-analyzer execution coverage, not confidence that an extension is safe or harmful.

Weights and thresholds are implementation constants established independently of the protected external holdout. This paper does not retrospectively justify or tune them using current results. Their role is to provide transparent and reproducible triage; calibration against stronger labels remains future work.

## 12. Dataset Construction

DriftBench models extension updates as ordered version pairs with provenance and curation metadata. Current Phase 3H facts are:

| Property | Verified value |
|---|---:|
| Version-pair transitions | 76 |
| Unique extensions | 21 |
| Benign transitions | 71 |
| Risky transitions | 3 |
| Uncertain transitions | 2 |
| Eligible after Phase 3H.5 and holdout exclusion | 64 |
| Ineligible | 12 |
| External-holdout records | 10 |

All 76 records are real open-source version pairs; the current Phase 3H corpus contains no controlled records. Accepted records originate from public GitHub release assets and preserve source URLs, version identifiers, release timestamps, licenses, raw or normalized archive hashes, split assignment, and label provenance. Archive normalization changes layout or compression for static-analysis compatibility while preserving separate provenance hashes; extension JavaScript is not executed.

Labels describe transition state rather than extension identity. The current labels are predominantly `SINGLE_REVIEWER_PROVISIONAL`; the two uncertain records remain ineligible. There are no confirmed malicious-transition records. The corpus is severely imbalanced and biased toward open-source GitHub projects, so it cannot estimate browser-store prevalence or support broad population claims.

Eligibility is distinct from label inclusion. Phase 3H.5 rechecks uncertainty, review quality, and external-holdout restrictions. This yields 64 supervised-eligible records and 12 ineligible records, including the 10 protected holdout cases.

## 13. Data Governance and External Holdout

Dataset versions, provenance schemas, feature schemas, and split policies are explicitly versioned. Duplicate, package-hash, extension-group, feature-leakage, timestamp, provenance, and analyzer-missingness audits accompany the research artifacts. Labels, eligibility, review status, and predictive outputs are not feature columns.

The Phase 3H `EXTERNAL_REPLICATION_HOLDOUT` contains 10 records from 2 extensions. Holdout rows remain in curation metadata but are excluded from non-holdout Phase 3H feature artifacts. They must not be used for:

- model training;
- model or hyperparameter tuning;
- threshold selection;
- deterministic rule development or tuning;
- feature-family redesign;
- Gold Set construction; or
- development decisions based on holdout outcomes.

This separation matters because repeated inspection or optimization against holdout outcomes would turn external validation into another development loop. The holdout therefore remains protected while label quality and review methodology are strengthened. Formal external validation is incomplete.

## 14. Experimental ML Evaluation

ML is evaluated only as an offline research question. Logistic Regression and Random Forest were trained across five locked feature representations using extension-group-safe splits. Preprocessing for Logistic Regression was fit on training data only; model selection used train/validation data, followed by one held-out test evaluation. Leakage audits passed, and models were not integrated into the application.

### Phase 3E pilot

Phase 3E contains 34 real pairs from 11 extensions, with 32 eligible records. The held-out test set has 6 records—5 provisionally benign and 1 provisionally review-worthy. The small positive-class support makes estimates unstable.

| Method / representation | Precision | Recall | F1 | FPR | Confusion matrix |
|---|---:|---:|---:|---:|---|
| Deterministic rule engine / full drift | 0.20 | 1.00 | 0.33 | 0.80 | tn=1, fp=4, fn=0, tp=1 |
| Logistic Regression / full drift | 0.00 | 0.00 | 0.00 | 0.00 | tn=5, fp=0, fn=1, tp=0 |
| Random Forest / full drift | 0.00 | 0.00 | 0.00 | 0.00 | tn=5, fp=0, fn=1, tp=0 |
| Random Forest / permission-only | 0.17 | 1.00 | 0.29 | 1.00 | tn=0, fp=5, fn=0, tp=1 |

### Phase 3F replication

Phase 3F expands the corpus to 46 real pairs from 14 extensions. Its held-out test set has 10 records—9 provisionally benign and 1 provisionally review-worthy.

| Method / representation | Precision | Recall | F1 | FPR | Confusion matrix |
|---|---:|---:|---:|---:|---|
| Deterministic rule engine / full drift | 0.11 | 1.00 | 0.20 | 0.89 | tn=1, fp=8, fn=0, tp=1 |
| Logistic Regression / full drift | 0.00 | 0.00 | 0.00 | 0.00 | tn=9, fp=0, fn=1, tp=0 |
| Random Forest / full drift | 0.00 | 0.00 | 0.00 | 0.00 | tn=9, fp=0, fn=1, tp=0 |
| Random Forest / permission-only | 0.10 | 1.00 | 0.18 | 1.00 | tn=0, fp=9, fn=0, tp=1 |

All five representations were evaluated; the complete matrices remain in the frozen experiment artifacts. No configuration supports a production-ML claim. The rule engine retained recall for the single held-out positive but at high false-alert cost. Full-drift exploratory models predicted every held-out case as benign at the selected thresholds and missed the single positive. These are preliminary observations on tiny, imbalanced, provisionally labeled sets—not stable comparative estimates.

Chronological evaluation and high-confidence label-sensitivity analysis were not sufficiently supported. The Phase 3F conclusion is `INCONCLUSIVE`, with production ML integration unjustified.

## 15. Independent Human Review Methodology

Phase 3H.5 defines an independent blind-review protocol. Initial packets expose version identity, provenance, release evidence, manifest differences, and neutral static feature summaries. They hide:

- current provisional dataset labels;
- DriftWatch numeric score and severity;
- rule recommendations;
- ML predictions or probabilities;
- earlier predictive outputs; and
- earlier reviewer labels.

A genuine reviewer supplies an independent transition label, ordinal confidence (`HIGH`, `MEDIUM`, or `LOW`), rationale, evidence references, reviewer identity, review round, and timestamp. Permitted labels distinguish benign, risky, malicious, uncertain, and excluded transitions. `MALICIOUS_TRANSITION` requires independent evidence of intentional harmful behaviour; static DriftWatch signals alone are insufficient.

The currently delivered package contains 14 scoped blind cases and matching blank submission forms, with no external-holdout overlap. **Human review is currently in progress.** No genuine returned submission has been incorporated. Simulated/AI-assisted workflow material is stored separately and is not human evidence, ground truth, agreement, or adjudication.

Current status: zero genuine double-reviewed records, zero genuine adjudicated records, no inter-rater agreement estimate, and no Gold Set.

## 16. Case Studies

The full evidence synthesis appears in `CASE_STUDIES.md`. Four cases illustrate complementary strengths and limitations.

### 16.1 GitHub Math Display 0.1.0 → 0.2.0

This transition adds `webNavigation`, a wildcard GitHub host pattern, a background worker, an API, external-network indicators, and a dynamic-execution indicator. The frozen held-out deterministic artifact reports 70.5/100, `Critical`, and `REVIEW_WORTHY`. Exploratory Phase 3F Logistic Regression and Random Forest probabilities were 0.332308 and 0.155, respectively, and both selected the benign class. The contrast illustrates transparent multi-signal prioritization and an exploratory model miss, but the reference label remains provisional. **Human review result: pending.**

### 16.2 Save Sora 2.0.196 → 2.0.355

No permission increase was observed, but V2 adds `https://api.dyysy.com/*`, two APIs, large network-indicator and structural churn, and one source/sink heuristic. The case demonstrates why permission-only review is insufficient and why large static counts require build and release context. No held-out operational-score artifact exists for this validation-split row, so none is inferred. **Human review result: pending.**

### 16.3 Refined GitHub 26.6.7 → 26.7

Permissions and hosts remain unchanged, while two APIs—including a critical-API flag—12 new external indicators, 46 added functions, and 164 modified files are reported. This illustrates code-level drift without manifest expansion and the ambiguity of broad maintenance churn. **Human review result: pending.**

### 16.4 Browserpass 3.11.0 → 3.12.0

No permission, host, or API additions are reported, yet static analysis identifies 256 new external indicators, 40 dynamic-execution additions, a large obfuscation score, and two source/sink heuristics. Build tooling or packaged-code structure may explain these signals. The frozen Phase 3H feature row and Phase 3H.5 packet disagree about the content-script-change flag, so this case does not rely on that field. **Human review result: pending.**

None of these cases establishes maliciousness, runtime communication, or exfiltration.

## 17. Failure Analysis

The detailed analysis appears in `FAILURE_ANALYSIS.md`.

### Provisional apparent false positives

The Phase 3E held-out deterministic evaluation contains four alerts on provisionally benign records; Phase 3F contains eight, including repeated Phase 3E cases. These feature-rich updates contain network, obfuscation/minification, and source/sink signals. Because labels are single-reviewer provisional, “false positive” is an apparent error against current curation, not final ground truth.

### Exploratory model miss

Both exploratory models missed the provisionally review-worthy KaTeX transition in Phase 3E and Phase 3F, despite strong static drift. Limited positive-class support and distribution mismatch are plausible explanations. This single repeated observation does not establish general model inferiority.

### Ambiguous cases

Two Save Sora transitions remain `UNCERTAIN` and training-ineligible. Their static signals support review, but no independent assessment, maintainer clarification, or corroborating public evidence resolves their intent or impact.

### Signal limitations

Network counts may be inflated by bundles, source maps, fixtures, or repeated literals. Obfuscation signals may reflect normal production builds. Same-file source/sink findings do not prove flow. Structural churn may reflect formatting or dependency changes. Permission and API additions require proportionality and release-context review.

### Label-quality limitation

All held-out errors use provisional labels, and no sufficiently large higher-confidence subset with both classes exists. Error interpretation therefore remains conditional on future independent review.

## 18. Results

### A. Deterministic system observations

In Phase 3E and Phase 3F, the fixed deterministic rule baseline detected the single held-out provisionally review-worthy transition (`recall=1.00`) but alerted on 4 of 5 and 8 of 9 provisionally benign transitions, respectively. The observed strength is sensitivity to heterogeneous static drift; the observed weakness is high false-alert cost on feature-rich updates. These test sets are too small for stable rate estimates.

### B. Exploratory ML evaluation

Full-drift Logistic Regression and Random Forest both had held-out recall and F1 of 0.00 in Phase 3E and Phase 3F at their selected thresholds, missing the single provisionally review-worthy transition. Permission-only Random Forest achieved recall 1.00 but classified every provisionally benign test case as review-worthy. No evaluated model supports production integration, and the replication conclusion is inconclusive.

### C. Case-study observations

The four flagship cases show that security-sensitive drift can appear as manifest expansion, code-level capability change without permission change, large network/structural churn, or strong obfuscation/source-sink signals. They also demonstrate that analyzer counts and heuristic evidence require release, build, and code context.

### D. Human validation

**PENDING GENUINE HUMAN REVIEW**

No genuine reviewer result, inter-rater agreement, adjudicated Gold Set, or final external-validation result is available. This section must be replaced only after independently returned submissions pass the documented validation and governance workflow.

## 19. Discussion

### Differential value

Version-pair analysis makes change explicit. It can distinguish longstanding capability from newly added scope and can organize evidence around a concrete release transition. The current pilot does not prove superiority over snapshot baselines, but the case studies show qualitative review value in surfacing changes that permission-only analysis would omit.

### Explainability

Deterministic contributions and evidence cards give reviewers a traceable path from observed signal to recommendation. This transparency is useful when alerts are ambiguous: an analyst can see whether priority came from host expansion, endpoints, obfuscation, structural churn, or a combination. RQ5 nevertheless remains empirically unresolved until genuine reviewers evaluate usefulness and decision quality.

### Deterministic and ML roles

The deterministic engine is an operational prioritizer; exploratory ML is a research comparator. Current results expose a trade-off: deterministic sensitivity with high alert cost versus model conservatism that missed the only positive. The appropriate response is stronger evidence and calibration, not post-hoc threshold tuning against the same held-out cases.

### Review prioritization

DriftWatch should be interpreted as allocating scarce review attention. High priority means that a change deserves inspection, not that it is malicious. Low priority means that the implemented static signals did not identify substantial drift, not that the extension is safe.

### Implications for extension review

A practical update-review process can combine provenance, differential static evidence, release notes, code inspection, and independent public evidence. DriftWatch supplies the differential evidence layer. Final disposition remains a human governance decision.

## 20. Limitations

1. **Small corpus:** 76 transitions and 21 extensions are insufficient for broad empirical claims.
2. **Severe imbalance:** only 3 transitions are provisionally risky, while 71 are provisionally benign and 2 uncertain.
3. **Provisional labels:** 74 records are single-reviewer provisional and 2 uncertain; genuine double review is absent.
4. **Source bias:** all accepted Phase 3H records derive from public GitHub release assets and do not represent browser-store prevalence.
5. **No confirmed malicious ground truth:** the current real corpus contains no independently confirmed malicious transition.
6. **Static analysis:** runtime activation, remote configuration, dynamic loading, indirect flows, WebAssembly semantics, and server behaviour may be missed.
7. **Historical-baseline limitation:** unchanged harmful behaviour in V1 and V2 may not appear as drift; V1 is not assumed safe.
8. **Pairwise limitation:** skipped versions, bad ordering, repackaging, or identity errors can distort the delta.
9. **Network-count inflation:** bundles, repeated literals, source maps, fixtures, and dead code can increase static counts.
10. **Obfuscation ambiguity:** minification and generated production bundles can resemble concealment.
11. **Source/sink limitation:** same-file co-occurrence does not establish data flow, reachability, or exfiltration.
12. **Structural ambiguity:** formatting, refactoring, dependency churn, and build regeneration can dominate file/function changes.
13. **Analyzer limitations:** unsupported syntax, parser approximations, or partial analyzer failure can reduce evidence.
14. **Tiny held-out sets:** Phase 3E and 3F tests contain only one positive each, and it is the same preserved transition.
15. **Incomplete human validation:** reviewer outcomes and report-usability evidence are pending.
16. **Incomplete external validation:** the protected holdout has not been formally evaluated and must remain untouched by development.
17. **Cross-artifact consistency:** at least one content-script-change field differs between frozen feature and review-packet representations and requires future audit.

## 21. Future Work

- Expand the corpus across more extensions, ecosystems, source families, and time periods.
- Acquire more independently verified risky transitions and, where lawful and safe, confirmed malicious update pairs.
- Complete genuine blinded review with additional independent reviewers and governed adjudication.
- Preserve the current holdout until a methodologically ready external-validation phase.
- Evaluate reviewer efficiency, explanation usefulness, and decision consistency.
- Study calibrated ML only after label quality, class support, and sample size improve.
- Strengthen cross-file, interprocedural, asynchronous, and semantic data-flow analysis.
- Improve endpoint canonicalization and distinguish occurrence counts from unique destinations.
- Audit cross-artifact feature representations and schema consistency.
- Explore optional sandboxed dynamic analysis under a separate threat model and containment design.
- Evaluate temporal and chronological protocols once sufficient review-worthy extension groups exist.

These are research directions, not completed features.

## 22. Conclusion

DriftWatch demonstrates a functional approach to explainable differential security analysis of browser-extension updates. It securely compares two supplied versions, represents heterogeneous security-sensitive drift, applies transparent deterministic prioritization, and presents evidence for manual review. DriftBench adds provenance, leakage controls, label-quality tracking, eligibility policy, exploratory evaluation, a protected holdout, and a blind human-review protocol.

Current evidence is preliminary. The deterministic system surfaced the only held-out provisionally review-worthy transition but at high false-alert cost, while exploratory models did not show deployable value. The corpus remains small, imbalanced, open-source biased, and provisionally labeled. Independent human validation is ongoing, and external validation is incomplete. DriftWatch therefore provides an implemented foundation for version-aware security-review prioritization rather than a validated malicious-extension detector.

## 23. References

No unverified external citation has been inserted. Replace the following placeholders with verified bibliographic entries after executing `LITERATURE_REVIEW_PLAN.md`:

1. [CITATION REQUIRED: foundational browser-extension security and threat-model studies]
2. [CITATION REQUIRED: browser-extension static, dynamic, or hybrid analysis]
3. [CITATION REQUIRED: browser permission models and over-privilege]
4. [CITATION REQUIRED: malicious-extension detection datasets and ML methods]
5. [CITATION REQUIRED: longitudinal extension evolution or update-security studies]
6. [CITATION REQUIRED: software-update security, maintainer compromise, and supply-chain risk]
7. [CITATION REQUIRED: differential program analysis and security-regression detection]
8. [CITATION REQUIRED: behavioural drift or change detection]
9. [CITATION REQUIRED: explainable cybersecurity and analyst decision support]
10. [CITATION REQUIRED: human-in-the-loop security review and alert triage]
11. [CITATION REQUIRED: evaluation under class imbalance, temporal shift, and dataset leakage]

### Repository evidence sources (not publication references)

- `ARCHITECTURE.md`
- `THREAT_MODEL.md`
- `RESEARCH.md`
- `DATASET_CARD.md`
- `DATA_GOVERNANCE.md`
- `CASE_STUDIES.md`
- `FAILURE_ANALYSIS.md`
- `artifacts/driftbench/phase3h/`
- `artifacts/driftbench/phase3h5/`
- `artifacts/experiments/phase3e/`
- `artifacts/experiments/phase3f/`

---

# INTERNAL DRAFT STATUS — REMOVE BEFORE SUBMISSION

This matrix is internal project metadata and must not appear in a submitted manuscript.

| Paper section | Status | Blocking work |
|---|---|---|
| 1. Title | READY | Reconfirm after venue and literature positioning are selected |
| 2. Abstract | PARTIAL | Update after genuine human review and final paper results freeze |
| 3. Introduction | PARTIAL | Add verified literature citations and refine venue framing |
| 4. Motivation | WAITING FOR LITERATURE | Support claims about update review and snapshot limitations |
| 5. Research Questions | READY | Preserve consistency with `RESEARCH.md` |
| 6. Related Work | WAITING FOR LITERATURE | Execute literature plan; verify novelty and positioning |
| 7. System Overview | READY | Produce publication-quality two-lane figure |
| 8. Threat Model | READY | Final copy edit only |
| 9. Methodology | READY | Add implementation citations/appendix references if required by venue |
| 10. Differential Feature Representation | READY | Confirm notation during final typesetting |
| 11. Deterministic Risk Engine | READY | Do not retune or post-hoc justify weights |
| 12. Dataset Construction | PARTIAL | Update only if a separately governed dataset release is approved |
| 13. Data Governance and External Holdout | READY | Preserve holdout restrictions |
| 14. Experimental ML Evaluation | READY | Frozen preliminary results; no selective rewriting |
| 15. Independent Human Review Methodology | WAITING FOR HUMAN REVIEW | Incorporate only validated genuine submissions |
| 16. Case Studies | WAITING FOR HUMAN REVIEW | Add reviewer outcomes without exposing blind-review material prematurely |
| 17. Failure Analysis | PARTIAL | Reassess apparent errors after genuine label review |
| 18. Results | WAITING FOR HUMAN REVIEW | Human-validation subsection is pending |
| 19. Discussion | PARTIAL | Revisit after literature and genuine review |
| 20. Limitations | READY | Maintain claims discipline during shortening |
| 21. Future Work | PARTIAL | Align with final discussion and venue scope |
| 22. Conclusion | WAITING FOR HUMAN REVIEW | Finalize only after results are complete |
| 23. References | WAITING FOR LITERATURE | Replace every citation placeholder with verified sources |
| Repository/release metadata | WAITING FOR FINAL RELEASE | Freeze commit, artifact identifiers, availability statement, and archival link |
