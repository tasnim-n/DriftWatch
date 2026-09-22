# DriftWatch Literature Citation Gaps

## Final status

- Resolved: **11**
- Partially resolved: **0**
- Unresolved: **0**
- Accepted verified sources: **22**
- In-text citation-task markers remaining in `PAPER_DRAFT.md`: **0**
- Reference-list task markers remaining in `PAPER_DRAFT.md`: **0**
- Fabricated or unverifiable citations found: **0**

All eleven historical gap entries are retained below. A gap is marked `RESOLVED` only for the qualified claim now made in the paper; resolution does not authorize stronger claims about maliciousness, accuracy, prevalence, generalization, or novelty.

## Gap audit and resolution

| Gap | Historical claim/topic requiring support | Preferred source type and minimum evidence | Source quantity | Paper location | Status and verified replacement |
|---|---|---|---|---|---|
| LIT-01 | Foundational browser-extension security and threat models: privileged roles, relevant adversaries, isolation, privilege boundaries, and unit of analysis. | Primary peer-reviewed browser-security papers whose full text explicitly studies extension architectures and threat boundaries. | Multiple sources appropriate because design and empirical limits are distinct. | Introduction; §6.1. | **RESOLVED** — BARTH2010 [1], CARLINI2012 [2], KAPRAVELOS2014 [4]. |
| LIT-02 | Browser-extension static, dynamic, and hybrid analysis: techniques, observable behaviors, semantic depth, scalability, and limitations. | Primary peer-reviewed system papers; verify analysis mode, target browser, supported flows/behaviors, and stated limitations. | Multiple sources required to represent all three modes. | §6.2. | **RESOLVED** — BANDHAKAVI2010 [3], KAPRAVELOS2014 [4], FASS2021 [5], WANG2018 [6]. |
| LIT-03 | Browser permission models and over-privilege: permission semantics, host access, warnings, and why permissions are incomplete evidence. | Peer-reviewed Chrome permission/architecture studies; claims restricted to the studied platform and period. | Multiple sources appropriate for permission measurement and architecture. | §6.3. | **RESOLVED** — FELT2011 [7], BARTH2010 [1], CARLINI2012 [2]. |
| LIT-04 | Malicious-extension detection datasets and methods: features, labels, targets, evaluation design, and limitations. | Primary peer-reviewed detection papers with accessible method and corpus descriptions; do not transfer their performance to DriftWatch. | Multiple sources appropriate because dynamic, hybrid, and deployment designs differ. | §6.1, §6.8. | **RESOLVED** — KAPRAVELOS2014 [4], WANG2018 [6], JAGPAL2015 [8]. |
| LIT-05 | Longitudinal extension evolution and update security: release histories, version-pair or delta analysis, and provenance. | Primary peer-reviewed longitudinal study where extension updates/deltas are central, not inferred from snapshots. | One strong nearest-work source is sufficient for the narrowed claim. | Motivation; §6.4; §6.5; §6.9. | **RESOLVED** — PANTELAIOS2020 [9]. |
| LIT-06 | Software-update, maintainer-compromise, and supply-chain security: delivery steps, repository compromise, provenance, and version ordering. | Peer-reviewed software-supply-chain/update work plus extension-specific update evidence; use as motivation only. | Multiple sources required to separate general supply-chain controls from extension updates. | §6.5. | **RESOLVED** — TORRESARIAS2019 [10], KUPPUSAMY2017 [11], PANTELAIOS2020 [9]. No DriftBench case is attributed to maintainer compromise. |
| LIT-07 | Differential program analysis and security regression: semantic/syntactic differences, affected behavior, guarantees, and bounds. | Primary peer-reviewed differencing/change-aware analysis papers whose object is a program change. | Multiple sources appropriate for complementary semantic and symbolic methods. | Motivation; §6.4. | **RESOLVED** — JACKSON1994 [12], PERSON2008 [13]. Paper wording is limited to change-aware analysis and does not claim security-regression guarantees. |
| LIT-08 | Behavioral drift and change detection: baseline choice, temporal meaning, and limits of relative comparison. | Peer-reviewed drift/change literature with explicit definitions; terminology must not conflate statistical concept drift and static release deltas. | One definition/survey plus the extension update-delta comparator. | §6.4. | **RESOLVED** — GAMA2014 [14], PANTELAIOS2020 [9]. The paper explicitly distinguishes statistical concept drift from DriftWatch's usage. |
| LIT-09 | Explainable cybersecurity and analyst decision support: faithful evidence, recipient usefulness, context, and limits. | Official explainability framework plus peer-reviewed human study of security alarms; distinguish principles from measured utility. | Multiple sources required for general principles and security-analyst evidence. | §6.6; §6.7. | **RESOLVED** — PHILLIPS2021 [15], ALAHMADI2022 [16]. DriftWatch does not claim measured explanation usefulness. |
| LIT-10 | Human-in-the-loop review, blind review, agreement, and adjudication: human task framing, nominal agreement, and interpretive limits. | Peer-reviewed security/usability framework and primary agreement methodology; numeric DriftWatch outcomes remain internally sourced. | Multiple sources appropriate for human-task and statistical claims. | §6.7; §15. | **RESOLVED** — CRANOR2008 [17], COHEN1960 [18], FEINSTEIN1990 [19]. The blind/adjudication procedure is described as a project method, not claimed as a literature-derived standard. |
| LIT-11 | Evaluation under imbalance, temporal shift, and leakage: skew, tuning bias, temporal change, and leakage prevention. | Peer-reviewed methodological papers/surveys matched to each stated limitation. | Multiple sources required because imbalance, drift, and leakage are different concerns. | §6.8; §14. | **RESOLVED** — HE2009 [20], VARMA2006 [21], KAPOOR2023 [22], GAMA2014 [14]. |

## Placeholder replacement record

| Original placeholder family | Verified replacement | Claim now supported |
|---|---|---|
| Security-sensitive software evolution and update review | [9], [12], [13] | Update deltas and program-version comparison can make change the analysis object. |
| Browser-extension security surveys/ecosystem studies | [1], [2], [4], [8] | Privilege boundaries, vulnerabilities, malicious behavior, and ecosystem-scale review. |
| Static or hybrid extension analysis | [3]–[6] | Static information flow, extension dependence graphs, dynamic elicitation, and hybrid features. |
| Permission systems and over-privilege | [1], [2], [7] | Permission declarations aid containment/triage but have granularity and warning limitations. |
| Differential analysis and behavioral change detection | [9], [12]–[14] | Program and extension change analysis, with an explicit concept-drift terminology boundary. |
| Security regression and software-update security | [9]–[13] | Update provenance/version order and change-aware analysis; no stronger regression guarantee asserted. |
| Explainable cybersecurity and analyst-facing alerts | [15]–[17] | Process-reflective explanations, contextual alarms, and human security tasks. |
| Security alert prioritization and risk scoring | [16], [17] | Contextual manual validation and human-task design; score remains an ordinal heuristic, not probability. |
| Malicious-extension detection and datasets | [4], [6], [8], [9] | Dynamic, hybrid, deployment, and delta-based detection designs. |
| Human review and agreement | [17]–[19] | Human-in-the-loop framing, nominal kappa, and marginal-imbalance caveat. |
| Imbalance, temporal shift, and leakage | [14], [20]–[22] | Class-skew, temporal change, tuning bias, and leakage limitations. |

## Project-internal claims remain separate

External citations do not replace repository evidence for corpus counts, eligibility, protected holdout, frozen experiments, human agreement, adjudication, quality promotion, or Gold Set membership. Those mappings remain in `PAPER_EVIDENCE_MAP.md`.

## Claims that remain prohibited

The completed literature review does not support claims of malware-detection accuracy, objective ground truth, representative prevalence, external validation, production safety, or generalization to all extensions. It also does not support “first,” “only,” “unique,” or “unprecedented” language for DriftWatch.
