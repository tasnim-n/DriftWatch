# DriftWatch Phase 6B Literature Audit

## Audit scope

Phase 6B audited external literature only. It did not modify runtime code, analyzers, features, weights, thresholds, datasets, frozen labels, eligibility, holdout policy, experiments, human-review artifacts, adjudication records, quality promotion, or Gold Set membership.

Audit dates: **2026-09-22 to 2026-09-23**.

## Source accounting

| Measure | Result |
|---|---:|
| Sources considered | 32 |
| Sources accepted | 22 |
| Sources rejected | 10 |
| Peer-reviewed conference/journal sources accepted | 21 |
| Official technical reports accepted | 1 |
| Other reputable sources used as evidence | 0 |

Accepted-source format distribution:

| Source type | Count |
|---|---:|
| Peer-reviewed conference/workshop proceedings | 14 |
| Peer-reviewed journal/survey articles | 7 |
| Official government technical reports | 1 |

## Search and screening record

Searches prioritized publisher and conference records from ACM, IEEE, USENIX, NDSS, NIST, Springer/BMC, ScienceDirect, SAGE, and PubMed. Discovery queries covered:

- browser-extension security architecture, vulnerabilities, permissions, and over-privilege;
- static, dynamic, hybrid, source-to-sink, and information-flow analysis;
- malicious-extension datasets and classifiers;
- extension version history, update deltas, ownership/maintainer compromise, and update security;
- software supply-chain provenance, repository compromise, rollback, and version ordering;
- semantic differencing, differential symbolic execution, and change-aware analysis;
- behavioral/concept drift and temporal evaluation;
- explainable cybersecurity, SOC alarm validation, and human-in-the-loop security;
- nominal Cohen's kappa and marginal-distribution limitations; and
- class imbalance, cross-validation selection bias, and dataset leakage.

Sources were accepted only after title, author, year, venue/report, stable identifier, and claim fit were checked against a publisher, venue, standards-body, or full-text record. Search-result snippets and citation aggregators were not treated as manuscript evidence. `LITERATURE_VERIFIED_SOURCES.md` contains the source-level verification record; `LITERATURE_REJECTED_SOURCES.md` preserves exclusions.

## Citation-gap resolution

| Status | Count |
|---|---:|
| Resolved | 11 |
| Partially resolved | 0 |
| Unresolved | 0 |

The resolution is claim-bounded. It means every external claim retained in the paper has appropriate support; it does not mean the search proves exhaustive absence of other systems.

## Placeholder audit

- Original in-text citation-task markers: 9.
- Original reference-list task markers: 11.
- Remaining citation-task markers in the manuscript: 0.
- Approximate or guessed substitutions: 0.
- Every replacement is documented in `LITERATURE_CITATION_GAPS.md`.

## Reference audit

| Check | Result |
|---|---:|
| In-text citation occurrences | 40 |
| Distinct in-text citation numbers | 22 |
| Reference entries | 22 |
| In-text citations missing a reference | 0 |
| Reference entries uncited in text | 0 |
| Duplicate reference numbers | 0 |
| Duplicate accepted sources | 0 |
| Conflicting author spellings | 0 |
| Conflicting publication years | 0 |
| Duplicate or conflicting DOI values | 0 |
| Dangling citation keys | 0 |
| Fabricated citations found | 0 |

All 22 reference entries have a DOI or a stable official publisher/conference URL. Numbered citations are a temporary consistent style pending venue selection.

## Claim-to-source audit

- Extension privilege and threat claims are limited to architectures, vulnerabilities, and malicious behavior demonstrated by [1], [2], [4], and [8].
- Static/dynamic/hybrid descriptions match the methods described by [3]–[6].
- Permission claims are limited to the studied Chrome models and periods in [1], [2], and [7].
- The extension-update claim is tied directly to the longitudinal delta method in [9], rather than inferred from snapshot studies.
- Supply-chain sources [10] and [11] motivate provenance/version ordering only; they do not diagnose any DriftBench transition.
- Differential-analysis sources [12] and [13] support change-aware analysis concepts, not DriftWatch correctness guarantees.
- Concept drift [14] is explicitly distinguished from DriftWatch's static “behavioural drift.”
- Explainability and analyst sources [15]–[17] support design principles and context needs; the paper retains that reviewer utility was not measured.
- Kappa sources [18] and [19] support the coefficient and marginal-imbalance caveat; the paper assigns no qualitative kappa category.
- Evaluation sources [20]–[22] support general imbalance, tuning-bias, and leakage cautions; they do not replace project experiment artifacts.

No citation stretching was found after these qualifications.

## Nearest-work finding

Pantelaios, Nikiforakis, and Kapravelos, *You've Changed: Detecting Malicious Browser Extensions through their Update Deltas* (CCS 2020) [9], is the strongest retrieved comparator. It studies 922,684 extension versions over six years and makes added-code deltas central to malicious-extension discovery. Its system uses rating/comment anomalies and added-JavaScript API sequences to locate and cluster suspicious updates.

DriftWatch differs in documented properties: a supplied version pair is analyzed across heterogeneous static signal families; the operational output is evidence-linked review priority rather than maliciousness classification; and the research workflow includes provenance, eligibility, a protected external holdout, explicit uncertainty, independent blind review, two-stage adjudication, and a separately governed Gold Set. These are scope and integration differences, not a verified “first” claim.

## Novelty-language audit

Allowed:

- “DriftWatch differs from prior work by...” with an explicit property comparison;
- “DriftWatch is positioned as...”;
- description of the implemented combination of differential evidence, prioritization, governance, uncertainty, and human review.

Not supported and excluded as contribution claims:

- first, only, unique, unprecedented, or no previous system;
- superiority to snapshot or update-delta systems without a governed comparative experiment;
- the claim that DriftWatch originated browser-extension update-delta analysis.

Negative matches for those priority claims that remain in the draft occur only in explicit disclaimers, not as claims.

## Metadata validation

- Exact title checked: 22/22.
- Author list checked: 22/22.
- Publication year checked: 22/22.
- Venue, journal, or report checked: 22/22.
- DOI checked where assigned: 12/12.
- Stable official URL checked for entries without a DOI: 10/10.
- Full text or sufficiently complete official method record checked for claim fit: 22/22.

## Remaining scholarly risk

No unresolved citation gap remains for the current text. Residual risks are:

1. The search is rigorous and documented but is not claimed to be a PRISMA-style exhaustive systematic review.
2. Browser-extension platforms and store policies evolve; historical findings are not generalized to every current Manifest V3 detail.
3. The nearest-work conclusion is bounded to the retrieved and screened literature; it is not an absence proof.
4. The numbered reference format may need conversion after a publication venue is chosen.
5. External literature cannot strengthen the small-corpus, label-quality, holdout, human-sample, or Gold Set limitations of the project evidence.

## Repository verification

- Test command: `.venv\Scripts\python.exe -m pytest -q --basetemp=".pytest_tmp_phase6b"`
- Test result: **203 passed in 18.32s**.
- `git diff --check`: **passed**; only Git's informational LF-to-CRLF working-copy warnings were emitted.
- Modified tracked paths: `LITERATURE_CITATION_GAPS.md`, `LITERATURE_REVIEW_PLAN.md`, `PAPER_DRAFT.md`, and `PAPER_EVIDENCE_MAP.md`.
- Created Phase 6B paths: `LITERATURE_VERIFIED_SOURCES.md`, `LITERATURE_REJECTED_SOURCES.md`, and `LITERATURE_AUDIT.md`.
- Frozen runtime, dataset, experiment, human-review, adjudication, and Gold Set paths changed: **0**.
- Commit created: **no**.
- Push performed: **no**.

## Integrity result

- External literature is used only for background, prior work, and methodological context.
- Project artifacts remain the evidence for all DriftWatch-specific empirical claims.
- New DriftWatch measurements introduced: 0.
- Frozen implementation or governed research artifacts modified: 0.
- Runtime behavior modified: 0.
