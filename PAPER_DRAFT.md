# DriftWatch: Explainable Differential Behavioural Analysis for Security-Review Prioritization of Browser-Extension Updates

> **Research-paper draft.** This draft is grounded in the current DriftWatch repository, frozen research artifacts, completed independent human-validation workflow, and governed Gold Set. The external literature review remains incomplete; citation placeholders and internal draft metadata must be resolved before submission.

## 1. Title

**DriftWatch: Explainable Differential Behavioural Analysis for Security-Review Prioritization of Browser-Extension Updates**

This title emphasizes the implemented unit of analysis—an extension-version pair—and the system's purpose: explainable prioritization of manual security review. It deliberately avoids positioning DriftWatch as an antivirus product or a malicious-extension classifier.

## 2. Abstract

Browser extensions evolve through frequent updates that can alter permissions, host access, browser-API use, network indicators, background execution, code structure, and obfuscation characteristics. Security analysis of a single extension snapshot does not directly express which capabilities or behaviours changed between releases. We present DriftWatch, a static differential analysis framework that compares a previous Chromium-extension archive, (V_{t-1}), with an updated archive, (V_t). DriftWatch securely extracts both archives, constructs version-level feature states, derives heterogeneous differential features, applies a deterministic multi-signal risk engine, and produces analyst-facing evidence and recommendations. Its score represents manual security-review priority, not malware probability.

The governed DriftBench corpus contains 76 real version-pair transitions from 21 open-source extensions: 71 frozen as benign, 3 as risky, and 2 as uncertain. After uncertainty and protected-holdout restrictions, 64 records are eligible for supervised research use; 10 records remain isolated in an external holdout. A scoped blind validation involved two independent human reviewers examining the same 14 cases. They agreed exactly on 9 cases (64.29%); unweighted nominal Cohen's kappa was approximately 0.34 and is interpreted cautiously because the sample is small and label marginals are concentrated. Five disagreements entered governed two-stage adjudication. All five retained their Stage A label after de-identified prior opinions were revealed at Stage B, yielding four outcomes labeled `RISKY_TRANSITION` and one labeled `UNCERTAIN`. Four definitive cases qualified for a separate, provenance-rich `MULTI_REVIEWER_ADJUDICATED` Gold Set with zero external-holdout overlap. The Gold Set is small, single-class, and prohibited from training or tuning; it supports qualitative validation and audit, not classifier-performance, prevalence, maliciousness, or production-safety claims. DriftWatch therefore demonstrates a functional, explainable, and reproducibly governed approach to version-aware security-review prioritization while leaving intent and final disposition to evidence-based human assessment.

## 3. Introduction

Browser extensions occupy a privileged position between users, webpages, and browser APIs. Their functionality and security exposure can change over time as maintainers add features, update dependencies, modify build pipelines, transfer ownership, or respond to platform changes. A reviewer examining only the latest package sees its current capabilities but may not see the security significance of the update itself: a new permission, broader host pattern, newly introduced background worker, sensitive API, encoded endpoint, or structural data-flow indicator.

DriftWatch treats the transition between versions as the primary object of analysis. Given a historical version (V_{t-1}) and update (V_t), it derives security-relevant observations for each version and expresses the change as a differential representation. This representation combines set changes, count deltas, Boolean events, scope expansions, and structural indicators. A deterministic risk engine converts those signals into a review-priority score and an explanation report. The score does not estimate maliciousness; it helps an analyst decide where review effort is most warranted.

The framework also separates operational analysis from offline research. The live FastAPI application uses deterministic analyzers and scoring only. DriftBench, exploratory machine-learning experiments, independent review, and the protected external holdout reside in a separate research lane and do not feed runtime scores. This separation supports reproducibility and reduces the risk that provisional labels or holdout observations influence operational rules.

This work makes the following repository-supported contributions:

1. A secure, static framework for comparing two supplied Chromium-extension archives.
2. A structured multi-signal representation of permission, host, API, network, obfuscation, package, manifest, and structural drift.
3. A deterministic explanation and review-priority engine with evidence, V1/V2 context, category-level contributions, and analyst recommendations.
4. DriftBench, a governed version-pair corpus with provenance, version ordering, label-quality, eligibility, split, leakage, and analyzer-availability metadata.
5. A protected external-holdout policy and completed blind independent-review and two-stage adjudication workflow designed to prevent training, tuning, and label leakage.
6. A separately governed four-record Gold Set that preserves provenance, excludes the external holdout, and prohibits training and tuning use.
7. Preliminary deterministic and exploratory-ML evaluations accompanied by failure analysis and explicit threats to validity.

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

The present evidence does not resolve all five questions. RQ1–RQ4 remain limited by corpus size, imbalance, predominantly provisional frozen labels, and small held-out sets. The completed human review supplies evidence about judgment consistency and uncertainty handling, but it did not measure reviewer efficiency, explanation usefulness, or decision quality; RQ5 therefore remains unresolved.

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

Labels describe transition state rather than extension identity. In the frozen Phase 3H dataset, 74 records have `SINGLE_REVIEWER_PROVISIONAL` label quality and 2 have `UNCERTAIN` quality. There are no confirmed malicious-transition records. The corpus is severely imbalanced and biased toward open-source GitHub projects, so it cannot estimate browser-store prevalence or support broad population claims.

Eligibility is distinct from label inclusion. Phase 3H.5 rechecks uncertainty, review quality, and external-holdout restrictions. This yields 64 supervised-eligible records and 12 ineligible records, including the 10 protected holdout cases.

Later human adjudication did not rewrite these frozen rows. It produced separate derived quality metadata for four reviewed cases. Consequently, the dataset distribution above and the governed Gold Set distribution below answer different questions and must not be merged: the former records frozen corpus history, while the latter records a qualified human-validation subset.

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

## 15. Independent Human Review and Adjudication

Phase 3H.5 defined an independent blind-review protocol. Two human reviewers received the same scoped set of 14 cases and made independent judgments. Initial packets exposed version identity, provenance, release evidence, manifest differences, and neutral static feature summaries. They hid:

- current provisional dataset labels;
- DriftWatch numeric score and severity;
- rule recommendations;
- ML predictions or probabilities;
- earlier predictive outputs; and
- earlier reviewer labels.

A reviewer supplied an independent transition label, ordinal confidence (`HIGH`, `MEDIUM`, or `LOW`), rationale, evidence references, reviewer identity, review round, and timestamp. Permitted labels distinguished benign, risky, malicious, uncertain, and excluded transitions. `MALICIOUS_TRANSITION` required independent evidence of intentional harmful behaviour; static DriftWatch signals alone were insufficient. Raw submissions were preserved immutably, and human outcomes were not used to alter features, rules, weights, thresholds, frozen labels, experiments, or holdout policy.

The reviewers agreed exactly on 9 of 14 cases and disagreed on 5. Agreement was 64.29%, with unweighted nominal Cohen's kappa of 0.3396226415 (approximately 0.34). Kappa is reported descriptively rather than assigned an uncited qualitative category. Its interpretation is limited by the small sample and concentrated marginals: Reviewer 01 assigned 8 risky and 6 uncertain labels, whereas Reviewer 02 assigned 3 risky and 11 uncertain labels. Agreement is not accuracy, and no independent objective ground truth exists.

| Human-review measure | Verified result | Interpretation boundary |
|---|---:|---|
| Blind cases reviewed by each human | 14 | Same case set; zero holdout overlap |
| Exact agreements | 9 | Observed agreement only |
| Disagreements | 5 | Entered governed adjudication |
| Exact agreement | 64.29% | Not accuracy |
| Unweighted nominal Cohen's kappa | 0.3396226415 | Small, marginally concentrated sample |

Each disagreement then entered two-stage adjudication by the same adjudicator. Stage A recorded an assessment before exposure to either prior review. At Stage B, the adjudicator reconsidered the case after receiving de-identified Reviewer A and Reviewer B opinions. The protocol did not require majority vote and permitted `UNCERTAIN`. All five cases retained their Stage A label at Stage B; the final disagreement outcomes were four `RISKY_TRANSITION`, one `UNCERTAIN`, and zero `BENIGN_TRANSITION`.

| Adjudication measure | Verified result |
|---|---:|
| Disagreements entering Stage A | 5 |
| Stage A and Stage B completed | 5 |
| Stage A labels retained at Stage B | 5 |
| Stage A labels changed at Stage B | 0 |
| Final `RISKY_TRANSITION` outcomes | 4 |
| Final `UNCERTAIN` outcomes | 1 |
| Final `BENIGN_TRANSITION` outcomes | 0 |

Adjudication strengthened label provenance and made disagreement resolution auditable; it did not prove that either original reviewer was objectively correct. `RISKY_TRANSITION` means that the update warrants elevated manual security-review attention. It does not mean malware.

## 16. Governed Gold Set

Four definitive adjudicated records received explicit, derived promotion to `MULTI_REVIEWER_ADJUDICATED` and qualified for `driftwatch-human-gold-set-v1`. The uncertain adjudicated record was not promoted, and the nine agreement-only records were not silently promoted. Frozen source rows remained unchanged; the Gold Set exists as a separate derived artifact.

| Gold Set record | Final human label | Quality tier | Holdout overlap |
|---|---|---|---:|
| `automaapp_automa_1_29_11_to_1_29_12` | `RISKY_TRANSITION` | `MULTI_REVIEWER_ADJUDICATED` | 0 |
| `bitwarden_clients_browser_v2026_6_1_to_browser_v2026_7_0` | `RISKY_TRANSITION` | `MULTI_REVIEWER_ADJUDICATED` | 0 |
| `browserpass_browserpass_extension_3_10_2_to_3_11_0` | `RISKY_TRANSITION` | `MULTI_REVIEWER_ADJUDICATED` | 0 |
| `duckduckgo_privacy_2026_1_12_to_2026_4_28` | `RISKY_TRANSITION` | `MULTI_REVIEWER_ADJUDICATED` | 0 |

The Gold Set has four records, all in one class, and zero external-holdout overlap. Its policy permits research reporting, qualitative case analysis, reproducibility, audit, and future evaluation only under a separately approved protocol. It does not authorize training, fine-tuning, threshold selection, rule development, scoring-weight tuning, feature or model selection, or hyperparameter tuning.

The Gold Set is therefore suitable for provenance-rich qualitative validation and research audit. Its very small, single-class membership cannot estimate classifier performance, class-balanced performance, population prevalence, maliciousness, or safety.

## 17. Case Studies

The full evidence synthesis appears in `CASE_STUDIES.md`. Four cases illustrate complementary strengths and limitations.

### 17.1 GitHub Math Display 0.1.0 → 0.2.0

This transition adds `webNavigation`, a wildcard GitHub host pattern, a background worker, an API, external-network indicators, and a dynamic-execution indicator. The frozen held-out deterministic artifact reports 70.5/100, `Critical`, and `REVIEW_WORTHY`. Exploratory Phase 3F Logistic Regression and Random Forest probabilities were 0.332308 and 0.155, respectively, and both selected the benign class. The contrast illustrates transparent multi-signal prioritization and an exploratory model miss, but the reference label remains provisional. This transition was not part of the scoped 14-case human-review set, so no human-validation outcome is inferred.

### 17.2 Save Sora 2.0.196 → 2.0.355

No permission increase was observed, but V2 adds `https://api.dyysy.com/*`, two APIs, large network-indicator and structural churn, and one source/sink heuristic. The case demonstrates why permission-only review is insufficient and why large static counts require build and release context. No held-out operational-score artifact exists for this validation-split row, so none is inferred. Both human reviewers independently assigned `RISKY_TRANSITION` with high confidence. This agreement-only case was not adjudicated or promoted to `MULTI_REVIEWER_ADJUDICATED`.

### 17.3 Refined GitHub 26.6.7 → 26.7

Permissions and hosts remain unchanged, while two APIs—including a critical-API flag—12 new external indicators, 46 added functions, and 164 modified files are reported. This illustrates code-level drift without manifest expansion and the ambiguity of broad maintenance churn. Both human reviewers independently assigned `RISKY_TRANSITION` (high and medium confidence). This agreement-only case was not adjudicated or promoted.

### 17.4 Browserpass 3.11.0 → 3.12.0

No permission, host, or API additions are reported, yet static analysis identifies 256 new external indicators, 40 dynamic-execution additions, a large obfuscation score, and two source/sink heuristics. Build tooling or packaged-code structure may explain these signals. The frozen Phase 3H feature row and Phase 3H.5 packet disagree about the content-script-change flag, so this case does not rely on or silently resolve that field. This transition was not part of the scoped 14-case human-review set; the related Browserpass 3.10.2 → 3.11.0 transition is a distinct Gold Set record.

None of these cases establishes maliciousness, runtime communication, or exfiltration.

## 18. Failure Analysis

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

All held-out errors use provisional labels, and no sufficiently large higher-confidence subset with both classes exists. The new Gold Set cannot repair this limitation because its four records are all risky and its policy prohibits training or tuning use. Error interpretation therefore remains conditional and must not be converted into population false-positive or false-negative rates.

Human disagreement adds a separate limitation: 5 of 14 scoped judgments differed even though the reviewers saw identical blind evidence. The adjudication workflow records how those cases were resolved, but the disagreements demonstrate the ambiguity of behavioral deltas when semantic, release, and runtime context is incomplete. Benign-but-security-relevant changes may correctly warrant review without being malicious, while static source/sink, permission, endpoint, and code-structure evidence cannot alone establish intent or actual execution.

## 19. Results

### A. Deterministic system observations

In Phase 3E and Phase 3F, the fixed deterministic rule baseline detected the single held-out provisionally review-worthy transition (`recall=1.00`) but alerted on 4 of 5 and 8 of 9 provisionally benign transitions, respectively. The observed strength is sensitivity to heterogeneous static drift; the observed weakness is high false-alert cost on feature-rich updates. These test sets are too small for stable rate estimates.

### B. Exploratory ML evaluation

Full-drift Logistic Regression and Random Forest both had held-out recall and F1 of 0.00 in Phase 3E and Phase 3F at their selected thresholds, missing the single provisionally review-worthy transition. Permission-only Random Forest achieved recall 1.00 but classified every provisionally benign test case as review-worthy. No evaluated model supports production integration, and the replication conclusion is inconclusive.

### C. Case-study observations

The four flagship cases show that security-sensitive drift can appear as manifest expansion, code-level capability change without permission change, large network/structural churn, or strong obfuscation/source-sink signals. They also demonstrate that analyzer counts and heuristic evidence require release, build, and code context.

### D. Human validation

Two independent human reviewers completed the same 14-case blind set. They agreed exactly on 9 cases and disagreed on 5, for observed agreement of 64.29%. Unweighted nominal Cohen's kappa was 0.3396226415. This statistic is descriptive for the scoped package, not an accuracy estimate; the small sample and concentrated risky/uncertain marginals make it unstable and sensitive to category prevalence.

All five disagreements completed Stage A and Stage B adjudication. No Stage A label changed after the adjudicator saw de-identified prior opinions at Stage B. Final disagreement outcomes were four `RISKY_TRANSITION` and one `UNCERTAIN`. These outcomes document governed human judgments; they do not establish objective truth or show that either initial reviewer was correct.

The four definitive adjudicated risky records were explicitly promoted to `MULTI_REVIEWER_ADJUDICATED` and placed in a separate governed Gold Set. The set has zero external-holdout overlap and is not authorized for training or tuning. Because it contains only four risky records, it supports qualitative audit but no classifier-performance, prevalence, or external-validation claim.

## 20. Discussion

### Differential value

Version-pair analysis makes change explicit. It can distinguish longstanding capability from newly added scope and can organize evidence around a concrete release transition. The current pilot does not prove superiority over snapshot baselines, but the case studies show qualitative review value in surfacing changes that permission-only analysis would omit.

### Explainability

Deterministic contributions and evidence cards give reviewers a traceable path from observed signal to recommendation. This transparency is useful when alerts are ambiguous: an analyst can see whether priority came from host expansion, endpoints, obfuscation, structural churn, or a combination. The completed review validates that humans can apply the packet protocol and records where their judgments diverge; it did not measure task time, explanation usefulness, or decision quality. RQ5 therefore remains empirically unresolved.

### Deterministic and ML roles

The deterministic engine is an operational prioritizer; exploratory ML is a research comparator. Current results expose a trade-off: deterministic sensitivity with high alert cost versus model conservatism that missed the only positive. The appropriate response is stronger evidence and calibration, not post-hoc threshold tuning against the same held-out cases.

### Review prioritization

DriftWatch should be interpreted as allocating scarce review attention. High priority means that a change deserves inspection, not that it is malicious. Low priority means that the implemented static signals did not identify substantial drift, not that the extension is safe.

### Implications for extension review

A practical update-review process can combine provenance, differential static evidence, release notes, code inspection, and independent public evidence. DriftWatch supplies the differential evidence layer. Final disposition remains a human governance decision.

## 21. Reproducibility

The verified research environment recorded in `ENVIRONMENT_SNAPSHOT.md` uses Python 3.14.0 on Windows 11. Exact installed packages are preserved in `requirements-research-lock.txt`, while `requirements.txt` and `pyproject.toml` retain broader supported-version policy. The repository provides a PowerShell setup and verification runbook in `REPRODUCIBILITY.md`.

Research claims identify versioned artifacts rather than requiring frozen phases to be regenerated. Phase 3E–3H.5 generators can overwrite or refresh outputs and therefore must not be rerun merely for verification. Existing JSON, CSV, and Markdown artifacts can instead be parsed and hashed read-only. Raw incoming archives are excluded from Git, so a clean clone supports code and artifact inspection but not necessarily exact archive reacquisition. `PAPER_EVIDENCE_MAP.md` maps major empirical claims to paths and hashes.

The operational application, analyzers, deterministic scoring, datasets, ML experiments, human evidence, promotion decisions, and Gold Set membership were not modified during paper integration. The full repository test command is `python -m pytest -q`; Phase 6 verification results are recorded in the development history rather than substituted for earlier environment snapshots.

## 22. Ethical and Governance Considerations

DriftWatch analyzes supplied packages statically and does not execute extension JavaScript. Reports describe observable security-sensitive drift and review priority, not developer intent or criminality. Neither a high score, a `RISKY_TRANSITION` human label, nor Gold Set membership establishes malware. Public reporting should avoid attributing harmful behavior without independent evidence and should preserve distinctions among static indicators, reviewer judgments, and verified runtime conduct.

Blind review concealed provisional labels and predictive outputs. Raw human submissions were preserved immutably, while public-safe aggregate artifacts omit private rationale text. Disagreements were not erased: `UNCERTAIN` remained an available outcome, and adjudication preserved the original review trail. The external holdout remains isolated from training, tuning, rule development, threshold selection, and Gold Set construction. These controls improve auditability but do not eliminate reviewer bias, source-selection bias, or uncertainty.

## 23. Limitations

| Limitation | Consequence for interpretation |
|---|---|
| Small, imbalanced corpus | The 76 transitions from 21 extensions, with 3 frozen risky labels, cannot support broad or population-level estimates. |
| Predominantly provisional frozen labels | Seventy-four source rows remain `SINGLE_REVIEWER_PROVISIONAL`; later derived human quality metadata does not rewrite them. |
| Small human-review sample | Agreement and kappa describe only 14 scoped cases; disagreement demonstrates residual judgment uncertainty. |
| Very small, single-class Gold Set | Four risky records support qualitative audit, not classifier metrics, prevalence, or generalization. |
| Open-source source bias | Public GitHub release assets do not represent browser-store prevalence or all extension ecosystems. |
| No confirmed malicious ground truth | Neither human adjudication nor Gold Set membership proves maliciousness or objective truth. |
| Static observability | Runtime activation, remote configuration, dynamic loading, indirect flows, WebAssembly semantics, and server behavior may be missed. |
| Historical and pairwise baselines | V1 is not assumed safe; skipped releases, bad ordering, repackaging, or identity errors can distort a delta. |
| Ambiguous static signals | Bundles, minification, generated assets, dependencies, repeated literals, and ordinary feature growth can appear security-relevant. |
| Source/sink approximation | Same-file co-occurrence does not establish data flow, reachability, sanitization, runtime transfer, or exfiltration. |
| Analyzer and artifact limitations | Unsupported syntax or partial failures can reduce evidence; one Browserpass content-script field remains inconsistent across frozen artifacts. |
| Tiny experimental test sets | Phase 3E and 3F each contain only one held-out positive, the same preserved transition; displayed rates are not stable estimates. |
| Incomplete external validation | The protected holdout has not been formally evaluated and remains excluded from development and Gold Set construction. |

These boundaries prevent claims of malware-detection accuracy, sensitivity, specificity, population false-positive or false-negative rates, representative prevalence, external validation, production safety, objective ground truth, or generalization to all browser extensions.

## 24. Future Work

- Expand the corpus across more extensions, ecosystems, source families, and time periods.
- Acquire more independently verified risky transitions and, where lawful and safe, confirmed malicious update pairs.
- Replicate blind review with larger, more diverse case sets and additional independent reviewers.
- Preserve the current holdout until a methodologically ready external-validation phase.
- Evaluate reviewer efficiency, explanation usefulness, and decision consistency.
- Study calibrated ML only after label quality, class support, and sample size improve.
- Strengthen cross-file, interprocedural, asynchronous, and semantic data-flow analysis.
- Improve endpoint canonicalization and distinguish occurrence counts from unique destinations.
- Audit cross-artifact feature representations and schema consistency.
- Explore optional sandboxed dynamic analysis under a separate threat model and containment design.
- Evaluate temporal and chronological protocols once sufficient review-worthy extension groups exist.

These are research directions, not completed features.

## 25. Conclusion

DriftWatch demonstrates a functional approach to explainable differential security analysis of browser-extension updates. It securely compares two supplied versions, represents heterogeneous security-sensitive drift, applies transparent deterministic prioritization, and presents evidence for manual review. DriftBench adds provenance, leakage controls, label-quality tracking, eligibility policy, exploratory evaluation, a protected holdout, independent blind human validation, governed adjudication, and explicit uncertainty handling.

The two reviewers agreed on 9 of 14 scoped cases, while five disagreements required adjudication. A separate four-record `MULTI_REVIEWER_ADJUDICATED` Gold Set preserves the strongest resulting provenance without rewriting frozen dataset history or authorizing training and tuning. These governance contributions make uncertainty and evidence lineage explicit, but they do not establish objective ground truth or malware-detection accuracy. The corpus remains small, imbalanced, open-source biased, and predominantly provisionally labeled; the Gold Set is very small and single-class; and external validation is incomplete. DriftWatch is therefore an implemented and reproducibly governed foundation for version-aware security-review prioritization, not a system that certifies malware or safety.

## 26. References

No unverified external citation has been inserted. `LITERATURE_CITATION_GAPS.md` classifies the remaining source requirements and separates them from project-internal artifact claims. Replace the following placeholders with verified bibliographic entries only after executing `LITERATURE_REVIEW_PLAN.md`:

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
- `HUMAN_REVIEW_GOLD_SET_POLICY.md`
- `PAPER_EVIDENCE_MAP.md`
- `artifacts/driftbench/phase3h/`
- `artifacts/driftbench/phase3h5/`
- `artifacts/experiments/phase3e/`
- `artifacts/experiments/phase3f/`
- `artifacts/human_review/agreement/reviewer01_vs_reviewer02/`
- `artifacts/human_review/adjudication/final/`
- `artifacts/human_review/quality_promotion/driftwatch-human-review-quality-promotion-v1/`
- `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/`

---

# INTERNAL DRAFT STATUS — REMOVE BEFORE SUBMISSION

This matrix is internal project metadata and must not appear in a submitted manuscript.

| Paper section | Status | Blocking work |
|---|---|---|
| 1. Title | READY | Reconfirm after venue and literature positioning are selected |
| 2. Abstract | READY FOR LITERATURE FINALIZATION | Recheck length and terminology against venue requirements |
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
| 15. Independent Human Review and Adjudication | READY | Preserve descriptive, non-accuracy interpretation |
| 16. Governed Gold Set | READY | Preserve single-class and no-training/tuning boundaries |
| 17. Case Studies | READY | Preserve the Browserpass artifact discrepancy |
| 18. Failure Analysis | READY | Do not fabricate failure rates |
| 19. Results | READY FOR LITERATURE FINALIZATION | Preserve frozen metrics and human-validation boundaries |
| 20. Discussion | PARTIAL | Revisit after literature synthesis |
| 21. Reproducibility | READY | Update final commit and archival identifier at release |
| 22. Ethical and Governance Considerations | READY | Preserve privacy and non-malware claims boundaries |
| 23. Limitations | READY | Maintain claims discipline during shortening |
| 24. Future Work | PARTIAL | Align with final discussion and venue scope |
| 25. Conclusion | READY FOR LITERATURE FINALIZATION | Recheck against final cited positioning |
| 26. References | WAITING FOR LITERATURE | Replace every citation placeholder with verified sources |
| Repository/release metadata | WAITING FOR FINAL RELEASE | Freeze commit, artifact identifiers, availability statement, and archival link |
