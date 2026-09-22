# DriftWatch Literature Review Plan

> **Purpose:** This document defines the evidence-gathering plan for positioning DriftWatch academically. It names research areas and required evidence without inventing papers or citations. Any source added to the manuscript must be retrieved, read, and checked against the claim it supports.

## 1. Review objectives

The review will establish what prior work says about browser-extension security, software-update risk, differential analysis, explainability, and analyst-centered review. It will also determine whether DriftWatch's combination of consecutive-version comparison, heterogeneous static drift, deterministic review prioritization, and evidence-centered reporting is already represented in the literature.

The review must answer four cross-cutting questions:

1. What units of analysis have prior browser-extension security systems used: a single snapshot, an ecosystem, a release history, or an explicit version pair?
2. Which security-sensitive change signals have been studied, and how were they represented and validated?
3. How have prior systems communicated uncertainty and evidence to human reviewers?
4. Which claims about DriftWatch's motivation, design choices, evaluation, and positioning require external support?

No novelty claim may be finalized until this review is complete.

## 2. Search and screening protocol

### 2.1 Priority sources

Search peer-reviewed security, software-engineering, programming-languages, and human-computer-interaction venues first. Supplement them with primary browser-vendor documentation, standards, official incident reports, and first-party technical reports where they provide facts not covered by peer-reviewed work. Surveys may identify terminology and foundational studies but should not replace the original sources for central claims.

Suggested indexes and libraries include ACM Digital Library, IEEE Xplore, USENIX proceedings, NDSS proceedings, SpringerLink, ScienceDirect, DBLP, Google Scholar, and backward/forward citation search. Search dates, query strings, result counts, and screening decisions should be logged.

### 2.2 Inclusion criteria

Include a source when it:

- directly studies browser extensions, security-sensitive software updates, differential/change analysis, explainable security, or human security review;
- describes a method, dataset, evaluation, threat model, user study, or documented incident relevant to a DriftWatch claim;
- provides enough methodological detail to assess the evidence;
- is a primary source or a rigorous synthesis; and
- has stable bibliographic metadata and an accessible full text.

### 2.3 Exclusion criteria

Exclude or use only as discovery leads:

- unsourced marketing material, listicles, and duplicated summaries;
- papers whose only overlap is generic malware classification without relevance to extension updates, differential features, explainability, or review;
- claims visible only in an abstract when the full method cannot be checked;
- sources that conflate static indicators with observed runtime behaviour or intent; and
- retracted, superseded, or unverifiable work unless discussed explicitly as historical context.

### 2.4 Extraction record

For every included source, record:

- full citation and persistent identifier;
- publication type, venue, year, and peer-review status;
- research question and unit of analysis;
- extension ecosystem or software domain;
- data provenance, sample size, time range, and labels;
- static, dynamic, hybrid, differential, or human-review method;
- feature families and whether version history is modeled;
- baselines, split strategy, leakage controls, and metrics;
- explanation or analyst-study design;
- principal findings and stated limitations;
- exact DriftWatch claim(s) the source can support;
- important differences that prevent direct comparison; and
- reviewer notes, quality assessment, and inclusion decision.

## 3. Topic-specific search plan

### 3.1 Browser-extension malware detection

**Research question:** How have prior systems detected or classified malicious browser extensions, which features and labels did they use, and did they analyze a single package or change across releases?

**Useful keywords:** `browser extension malware detection`, `malicious Chrome extension classification`, `web extension malware machine learning`, `browser add-on abuse detection`, `Chrome Web Store malicious extension dataset`, `extension temporal evaluation`.

**Sources needed:** Peer-reviewed detection papers; primary dataset papers; ecosystem measurement studies; browser-vendor reports describing malicious-extension enforcement; papers that document temporal splits, class imbalance, family leakage, or concept drift.

**Relation to DriftWatch:** This literature provides the closest classification-oriented comparator while clarifying that DriftWatch's operational output is review priority, not a maliciousness prediction. Extract whether studies use latest-version snapshots, release histories, or explicit deltas.

**Claims requiring citation:** Existing systems commonly use static, dynamic, or hybrid features; datasets and labels vary in reliability; malicious-extension classification faces imbalance and temporal/generalization risks; snapshot classification differs from version-pair review. The frequency of snapshot-oriented designs must be established empirically, not assumed.

### 3.2 Permission analysis

**Research question:** What is known about browser-extension permission models, over-privilege, permission warnings, host permissions, and permission changes over time?

**Useful keywords:** `browser extension permission analysis`, `Chrome extension overprivilege`, `host permission extension security`, `optional permissions browser extension`, `extension permission warning usability`, `longitudinal permission change`.

**Sources needed:** Peer-reviewed security and usability studies; formal or empirical permission-model analyses; primary Chromium/WebExtensions documentation for permission semantics; longitudinal studies of permission evolution.

**Relation to DriftWatch:** Permissions and host scope are two differential signal families and also form a restricted baseline. Literature should establish both their value and why they cannot alone characterize an update.

**Claims requiring citation:** Permissions mediate security-sensitive capabilities; broad host access affects exposure; users or reviewers may struggle with warnings; permission-only analysis has known blind spots; permission changes can be security relevant without establishing malicious intent.

### 3.3 Browser-extension static analysis

**Research question:** Which program-analysis techniques have been adapted to extension manifests and JavaScript, and what evidence and limitations do they expose?

**Useful keywords:** `browser extension static analysis`, `Chrome extension JavaScript analysis`, `extension taint analysis`, `WebExtensions data flow`, `content script static analysis`, `extension API usage analysis`, `browser extension source sink`.

**Sources needed:** Primary static-analysis and hybrid-analysis papers; extension-specific program models; taint/data-flow work; empirical evaluations of bundled or obfuscated JavaScript; authoritative platform architecture documentation.

**Relation to DriftWatch:** DriftWatch applies bounded static analyzers to both versions and includes same-file source/sink heuristics. Prior work will contextualize its semantic depth, scalability, and claims boundary.

**Claims requiring citation:** Extension architectures complicate analysis across contexts; static analysis can observe code and configuration but not runtime occurrence or intent; dynamic construction, indirect flows, remote behavior, and bundling can limit precision and recall.

### 3.4 Extension update security

**Research question:** How has security research studied extension evolution, release histories, update mechanisms, security regressions, and malicious or compromised updates?

**Useful keywords:** `browser extension update security`, `Chrome extension version history security`, `extension evolution longitudinal`, `malicious extension update`, `browser add-on update compromise`, `extension security regression`.

**Sources needed:** Longitudinal ecosystem studies; version-history analyses; papers comparing extension releases; primary browser-store update-policy documentation; verified incident analyses involving extension updates.

**Relation to DriftWatch:** This is the most direct literature for its version-pair unit of analysis. The review must identify whether prior work explicitly derives heterogeneous security deltas between consecutive packages and how it validates them.

**Claims requiring citation:** Extensions evolve through updates; security-relevant capabilities may change between releases; update mechanisms or release transitions can be abused; an explicit delta may provide different evidence from a latest-version snapshot. The final wording must match the strength of retrieved evidence.

### 3.5 Extension ownership and maintainer compromise

**Research question:** What evidence exists that ownership transfer, maintainer-account compromise, or ecosystem incentives can precede harmful extension changes?

**Useful keywords:** `browser extension ownership transfer security`, `Chrome extension maintainer compromise`, `extension acquisition malicious update`, `browser add-on supply chain compromise`, `developer account takeover extension`.

**Sources needed:** Peer-reviewed ecosystem or supply-chain studies; official browser-vendor disclosures; primary incident reports; independently corroborated investigations with version and timeline evidence.

**Relation to DriftWatch:** Maintainer or ownership compromise is one plausible change scenario in the threat model, not an inference produced by the analyzer. Literature can justify including the scenario while preserving that boundary.

**Claims requiring citation:** Ownership or maintainer changes can create update risk; documented incidents have involved previously benign extensions; code drift alone cannot identify who caused a change or establish compromise.

### 3.6 Software-update security

**Research question:** How does broader software-security research model trusted updates, compromised release pipelines, dependency changes, and security regression?

**Useful keywords:** `software update security`, `secure software update framework`, `update system compromise`, `software supply chain malicious update`, `dependency update security risk`, `security regression detection`, `release pipeline compromise`.

**Sources needed:** Foundational and recent peer-reviewed work; applicable standards; primary analyses of supply-chain incidents; secure-update framework documentation; software-evolution studies measuring vulnerability introduction or regression.

**Relation to DriftWatch:** This literature supplies general concepts for update provenance and change risk. It should be used carefully because browser extensions have platform-specific permissions, contexts, and distribution mechanisms.

**Claims requiring citation:** Updates are a security boundary; release and dependency pipelines can introduce risk; provenance and rollback/version ordering matter; general software-update findings may motivate but do not directly validate DriftWatch.

### 3.7 Differential program analysis

**Research question:** Which techniques compare program versions to identify semantic, structural, or security-relevant change, and how do they represent heterogeneous deltas?

**Useful keywords:** `differential program analysis`, `semantic diff security`, `program change impact analysis`, `software differencing security`, `binary diff vulnerability`, `regression analysis program versions`, `change-aware static analysis`.

**Sources needed:** Primary programming-languages and software-engineering papers; semantic-diff and change-impact techniques; security regression tools; surveys that provide terminology and taxonomies.

**Relation to DriftWatch:** This literature grounds the conceptual expression `D_t = F(V_t) - F(V_{t-1})` and helps distinguish set, count, Boolean, ordinal, and structural differences from ordinary numeric subtraction.

**Claims requiring citation:** Version differencing can focus analysis on changed behavior or code; syntactic and semantic differencing offer different guarantees; change-aware analysis has precision, scalability, and dependency limitations.

### 3.8 Behavioural drift and change detection

**Research question:** How are drift and change detection defined in security and software monitoring, especially when the baseline itself may be unsafe?

**Useful keywords:** `behavioural drift cybersecurity`, `security behavior change detection`, `concept drift malware detection`, `baseline anomaly security`, `software behavior drift`, `temporal security monitoring`.

**Sources needed:** Peer-reviewed security monitoring and change-detection studies; concept-drift work relevant to ML evaluation; longitudinal behavior modeling; work discussing contaminated or untrusted baselines.

**Relation to DriftWatch:** The review will refine use of “behavioural drift” and avoid conflating static version differences with observed runtime behavior or statistical concept drift.

**Claims requiring citation:** Change detection depends on baseline choice; a historical baseline need not be trusted safe; unchanged harmful behavior may be invisible to a delta; temporal shift can undermine learned models. Terminology must be reconciled across disciplines.

### 3.9 Explainable cybersecurity

**Research question:** What makes a security explanation useful, faithful, actionable, and appropriately uncertain for an analyst?

**Useful keywords:** `explainable cybersecurity`, `interpretable security alerts`, `security analyst explanation`, `actionable alert evidence`, `XAI intrusion detection limitations`, `human centered security analytics`.

**Sources needed:** Peer-reviewed explainable-security papers; human-centered evaluations; studies of alert triage and explanation quality; critiques of post-hoc explanations; transparent rule-system evaluations.

**Relation to DriftWatch:** DriftWatch links deterministic contributions to concrete version evidence and reviewer actions. Literature is needed to define and eventually evaluate usefulness rather than assuming that visible rules are sufficient.

**Claims requiring citation:** Explanations can support analyst reasoning only when they are faithful and contextual; post-hoc feature importance differs from direct evidence; explanation utility requires human evaluation; uncertainty and limitations should be communicated.

### 3.10 Human-in-the-loop security review

**Research question:** How should independent security review, blind labeling, confidence, rationale, disagreement, and adjudication be designed and reported?

**Useful keywords:** `human in the loop security review`, `security analyst alert triage study`, `blind annotation cybersecurity`, `inter-rater agreement security labels`, `expert annotation malware dataset`, `security decision support usability`.

**Sources needed:** Peer-reviewed analyst studies; dataset-labeling methodology; annotation and adjudication guidance; empirical work on security expertise, workload, trust, and alert fatigue; statistical guidance for agreement under imbalance.

**Relation to DriftWatch:** This literature will support the independent blind-review protocol and determine appropriate interpretation of future reviewer outcomes. Simulated review must remain excluded from human evidence.

**Claims requiring citation:** Independent review can reduce confirmation bias; blind protocols should conceal model outputs and prior labels; confidence and rationale add context; agreement statistics depend on design and prevalence; adjudicated labels are not automatically objective ground truth.

## 4. Cross-topic synthesis questions

After topic screening, construct an evidence matrix answering:

- Does the source analyze explicit consecutive version pairs?
- Are changes manifest-level, code-level, behavioral, or runtime-observed?
- Are heterogeneous deltas combined, and if so, how?
- Is the output detection, classification, ranking, triage, explanation, or a report?
- Does the system expose raw evidence and distinguish observation from interpretation?
- Are scores probabilistic, calibrated, heuristic, ordinal, or unspecified?
- How are labels sourced, blinded, reviewed, and adjudicated?
- Are splits extension-group-safe and temporal where appropriate?
- Are holdouts protected from feature, rule, threshold, and label development?
- Is analyst utility evaluated with genuine participants?

The synthesis should separate direct predecessors from adjacent work and prevent comparisons between incompatible tasks or datasets.

## 5. Quality and claims controls

For each manuscript claim, maintain a claim-to-source ledger with one of these states:

- **Repository evidence:** supported by inspected code, documentation, or frozen artifacts.
- **External evidence verified:** supported by a read primary source and page/section note.
- **Interpretation:** explicitly labeled as the authors' synthesis.
- **Citation required:** placeholder retained; claim not submission-ready.
- **Remove or weaken:** available evidence does not support the current wording.

Do not infer a paper's findings from its title, abstract snippet, citations by others, or search-result text. Do not cite a survey for a precise primary result when the original paper is available. Record contradictory evidence and negative findings rather than selecting only sources favorable to DriftWatch.

## 6. Novelty audit

Before making any novelty statement:

1. Identify the nearest systems in extension security, longitudinal extension analysis, and differential security analysis.
2. Compare unit of analysis, signals, scoring objective, explanations, governance, evaluation, and human validation in a structured table.
3. Search the terminology used by those systems, then repeat searches with their cited predecessors and citing work.
4. Ask whether each purported distinction is a new method, an integration, an application to extensions, or simply an implementation choice.
5. Retain cautious wording such as “DriftWatch is positioned as” unless the evidence supports a narrower, defensible novelty claim.

The final paper must not say “first,” “novel,” or an equivalent priority claim solely because no match appeared in an initial search.

## 7. Current citation inventory

`LITERATURE_CITATION_GAPS.md` is the controlled Phase 6 gap register. As of this integration:

- no external paper citation has been verified for manuscript use;
- no fabricated bibliographic citation was found;
- 11 structured external source requirements remain;
- project-specific corpus, evaluation, human-review, adjudication, and Gold Set claims are mapped to repository evidence in `PAPER_EVIDENCE_MAP.md`; and
- the manuscript retains visible citation tasks rather than invented bibliographic entries.

The gap register should be updated as sources pass full-text verification. A search result, title, abstract snippet, or secondary citation does not move an item to **External evidence verified**.

## 8. Deliverables and completion criteria

The literature phase is complete only when it produces:

- a reproducible search log;
- a deduplicated source library with stable identifiers;
- screening decisions and exclusion reasons;
- completed extraction and quality records;
- a cross-topic evidence matrix;
- a nearest-work comparison table;
- a claim-to-source ledger covering every external claim in `PAPER_DRAFT.md`;
- verified bibliographic entries replacing every citation placeholder; and
- a final claims and novelty audit.

Until then, the Related Work and References sections of `PAPER_DRAFT.md` remain **WAITING FOR LITERATURE**.
