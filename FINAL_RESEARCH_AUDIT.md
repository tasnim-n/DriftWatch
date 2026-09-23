# DriftWatch Phase 7 Independent Final Research / Repository Audit

Audit date: 2026-09-23

Branch: `main`

Base commit: `3412522eb7c1ae8c05ac90b115cbf38032210577`
Final audit status: **BLOCKED**

## 1. Audit scope and method

This was an evidence-first audit of the repository, frozen research artifacts, human-validation chain, governed Gold Set, manuscript, literature registry, reproducibility documentation, privacy boundary, and publication hygiene. Claims were checked against local authoritative artifacts rather than accepted from prior reports. Frozen analyzers, feature definitions, scoring, weights, thresholds, labels, eligibility, holdout policy, experiments, human decisions, quality promotion, and Gold Set membership were not modified or regenerated.

Read-only checks included Git index/status inspection, SHA-256 recomputation, structured JSON parsing, source inspection, paper/reference counting, documentation searches, and the complete test suite. Private rationale text was not copied into this report.

## 2. Repository state

The audit began with no tracked or staged changes on `main` at commit `3412522eb7c1ae8c05ac90b115cbf38032210577`. The working tree did contain private/local material.

- Untracked and not locally ignored: the Stage A raw-return ZIP; Stage B package ZIP and checksum; Stage B raw-return ZIP; and 14 files under `reviewer_human_adjudicator_stage_b/`.
- Ignored/private: the virtual environment, local datasets, database/log/cache files, Reviewer 01 and Reviewer 02 archives and workspaces, the Stage A workspace, and local human-review agreement/adjudication/reviewer artifacts.
- Staged files: none.
- Tracked ZIPs: only the four controlled sample archives under `samples/`.
- Tracked private reviewer ZIPs, raw adjudication returns, alias mappings, validated raw submissions, final rationale-bearing resolutions, or private reviewer workspaces: none.
- `git diff --check` at the audit start: passed.

The private/local material that is untracked but not ignored is a release-hygiene blocker because a directory-based release bundle or an accidental add could include it.

## 3. Test audit

Command:

```powershell
.venv\Scripts\python.exe -m pytest tests\ -q -W default --basetemp=.pytest_tmp_phase7
```

Result: **203 passed, 0 failed, 0 errors, 0 skipped** in 18.81 seconds.

Warnings were non-failing: one Starlette/httpx deprecation warning, one NumPy/joblib deprecation warning, and one pytest cache-path warning caused by the inaccessible pre-existing `.pytest_cache` state. The dedicated Phase 7 basetemp was removed after its path was resolved and confirmed inside the repository.

## 4. Frozen artifact integrity

No tracked modifications were present under `analyzers/`, `risk_engine/`, `app/`, `driftbench/`, `research/`, datasets, experiment artifacts, or frozen research artifact paths at the start of the audit. The full test suite also exercised the frozen research-integrity checks.

Recorded Phase 3H references were recomputed and all matched:

| Artifact | Result |
|---|---|
| Phase 3H dataset manifest | PASS |
| Phase 3H experiment dataset snapshot | PASS |
| Phase 3H feature-extraction manifest | PASS |
| Phase 3H provenance manifest | PASS |
| External holdout manifest | PASS |
| Phase 3H.5 eligibility report | PASS |

The Phase 3H.5 reference values matched the files they identify. Phase 3E/3F experiment and evaluation artifacts were unchanged from `HEAD`; no training, evaluation regeneration, or tuning was performed.

For the local human-validation chain:

- Phase 5C agreement-summary hash: PASS.
- Five Stage A packet hashes recorded by final provenance: 5/5 PASS.
- Five Stage B released-case hashes: 5/5 PASS.
- Five Stage B blank-submission hashes: 5/5 PASS.
- Five Phase 5F validated Stage B hashes: 5/5 PASS.
- Five Phase 5F final-resolution hashes: 5/5 PASS.
- Six Phase 5F aggregate/provenance artifact hashes: 6/6 PASS.
- Six Phase 5G public promotion artifact hashes: 6/6 PASS.
- Phase 5H evidence-map file hashes and Gold Set manifest hash: PASS.

No protected mismatch was found and no historical evidence was regenerated.

## 5. Authoritative human artifact hashes

All five named archives were locally available and matched their expected SHA-256 values:

| Artifact | SHA-256 status |
|---|---|
| Reviewer 01 raw return | PASS — `E4843AE0A1241D4E69A70E2C16063DA447EB97BA82CFF2AAF92CF258D4668A5C` |
| Reviewer 02 raw return | PASS — `E9E19CDF330C5F41B794823FF9A5C02300F03A7EEEBE5139820521ACC5A57CDA` |
| Stage A raw return | PASS — `C66C3D5349F701BE4ECA75C049BB0382E105B79B801F2737D7069BDBD26A11DC` |
| Stage B released package | PASS — `F4703D89F32502770F428B744401466423F2152CBB1093B50109F7EF928C6C89` |
| Stage B raw return | PASS — `F5990ED098DE626A748EFABC4AF452C6994F1683375AB0E0E7E6361E2F00C843` |

The archives were not modified.

## 6. Gold Set audit

`artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_manifest.json` recomputed to:

`F83FF5276E26724200123FE0E64160C4397F71F289EC40E680D74086F46A9F60`

Verified facts:

- exactly 4 members;
- semantic distribution `risky_transition=4`;
- human-label distribution `RISKY_TRANSITION=4`;
- quality distribution `MULTI_REVIEWER_ADJUDICATED=4`;
- external-holdout overlap 0;
- adjudicated uncertain case excluded;
- all nine agreement-only cases excluded from promotion;
- training and tuning authorization false;
- restrictions explicitly prohibit training, fine-tuning, threshold/rule/weight/feature/model/hyperparameter selection without a separate governed authorization;
- validation records no private human text and no frozen dataset or Phase 5G mutation;
- the internal deterministic manifest hash is `d1984552f8298c9133f0988fe8e38fe499772ae8f2e20ccea2715730d1c0a7e1`.

The tracked Gold Set artifacts contain source hashes and pseudonymous workflow identifiers but no raw rationale, evidence-reference text, personal reviewer names, or private alias mapping.

## 7. Dataset and holdout claims

Authoritative Phase 3H/3H.5 artifacts confirm:

| Claim | Verified value |
|---|---:|
| Version-pair transitions | 76 |
| Unique extensions | 21 |
| Benign | 71 |
| Risky | 3 |
| Uncertain | 2 |
| Supervised eligible | 64 |
| Ineligible | 12 |
| External holdout | 10 records / 2 extensions |

The holdout manifest records `training_use_allowed=false` and `tuning_use_allowed=false`. Current documentation preserves the additional prohibition on threshold selection, rule development, feature redesign, and Gold Set construction.

Older corpus/test counts found in phase-specific sections are historical snapshots and are labeled by phase. No current-facing corpus-count conflict was found.

## 8. Human-validation claims

Local authoritative artifacts confirm:

- 14 common blind cases and 2 independent reviewers;
- 9 exact agreements and 5 disagreements;
- exact agreement `9/14 = 64.285714...%`, displayed as 64.29%;
- Reviewer 01 marginals 8 risky / 6 uncertain and Reviewer 02 marginals 3 risky / 11 uncertain;
- chance agreement `0.4591836735` and unweighted nominal Cohen's kappa `0.3396226415094341`;
- 5 Stage A and Stage B adjudication cases;
- 0 Stage A-to-Stage B label changes;
- final disagreement outcomes: 4 risky, 1 uncertain, 0 benign.

The paper reports these values consistently and treats agreement as descriptive rather than accuracy. Historical Phase 3H/3H.5 snapshots retain their then-correct zero-review/empty-Gold-Set state. Stale current-status statements in six current-facing documents were corrected during this audit.

## 9. Claim-language audit

No unsupported affirmative claim was found for malware-detection accuracy, objective ground truth, safety certification, production approval, sensitivity/specificity, population false-positive/false-negative rates, representative prevalence, external validation, generalization, or novelty superlatives.

Matches for those terms are research questions, historical descriptions, metric names for frozen tiny experiments, or explicit prohibitions/negations. The manuscript consistently states that review priority is not malware probability, source/sink evidence is heuristic, the Gold Set is not an accuracy set, and external validation is incomplete.

## 10. Paper audit

The manuscript's abstract, methods, result tables, discussion, limitations, and conclusion agree on the corpus, human-review, adjudication, holdout, and Gold Set counts. The kappa calculation and displayed confusion matrices are mathematically consistent with the frozen artifacts. The four-case Gold Set is explicitly excluded from classifier-performance inference.

The case-study text preserves the known Browserpass content-script-field discrepancy and does not silently resolve it. Experimental claims are framed as preliminary observations on tiny, imbalanced, provisionally labeled test sets.

Publication blocker: `PAPER_DRAFT.md` still contains the top-level section `INTERNAL DRAFT STATUS — REMOVE BEFORE SUBMISSION`, an internal readiness matrix, venue-dependent editing tasks, and a repository/release row marked `WAITING FOR FINAL RELEASE`. It also lists ignored local agreement/adjudication directories as repository evidence sources. The manuscript is therefore not submission-ready in its current file form.

## 11. Literature and reference audit

Independent local parsing found:

- 40 in-text citation occurrences;
- 22 distinct citation numbers;
- 22 sequential reference entries `[1]` through `[22]`;
- 0 missing references;
- 0 uncited references;
- 0 duplicate reference numbers;
- 0 citation-task placeholders in the manuscript.

Author, title, year, venue, and DOI/stable-URL text is consistent with `LITERATURE_VERIFIED_SOURCES.md`. The local literature records report 22 accepted sources, of which 21 are peer reviewed and 1 is an official primary technical report. `LITERATURE_AUDIT.md` and `LITERATURE_CITATION_GAPS.md` consistently record all 11 original gap families as resolved. This Phase 7 pass did not perform a fresh live-web metadata audit; it cross-checked the manuscript against the locally verified source registry and did not invent metadata changes.

## 12. Nearest-work and novelty audit

The manuscript identifies Pantelaios, Nikiforakis, and Kapravelos, *You've Changed: Detecting Malicious Browser Extensions through their Update Deltas* (CCS 2020), as the closest retrieved update-delta comparator. It does not claim that DriftWatch originated extension update-delta analysis.

Differentiation is limited to factual properties: heterogeneous static evidence, evidence-linked review prioritization, provenance/eligibility/holdout governance, explicit uncertainty, and scoped independent human review/adjudication. “First,” “only,” “unique,” and “unprecedented” appear only in disclaimers that reject those claims.

## 13. Paper evidence map audit

All listed paths exist in the local working copy. All 11 recorded file-level SHA-256 values recomputed successfully, and the separate internal Gold Set manifest hash matched its JSON field.

Release blocker: three mapped human-validation files are ignored local artifacts, not tracked repository evidence:

- `artifacts/human_review/agreement/reviewer01_vs_reviewer02/agreement_summary.json`
- `artifacts/human_review/adjudication/final/human_validation_summary.json`
- `artifacts/human_review/adjudication/final/stage_a_to_stage_b_comparison.json`

A clean clone therefore cannot follow these mappings. The comparison file also contains per-record `resolution_basis` fields and is inside the private rationale-bearing adjudication tree, so mapping it as public evidence violates the map's own no-private-rationale boundary. The same ignored directories are presented as public-safe/repository evidence in `DATASET_CARD.md`, `DATA_GOVERNANCE.md`, `RESEARCH.md`, and the manuscript's repository-evidence list.

Required action: under a separately approved publication step, generate or designate sanitized, rationale-free aggregate artifacts for agreement, adjudication completion, and the Stage A-to-Stage B change count; verify them; track only those public-safe aggregates; then update every evidence path and hash. Do not publish or mutate the private originals merely to satisfy the map.

## 14. Reproducibility audit

The verified local environment is Python 3.14.0 on Windows. `requirements-research-lock.txt` contains 49 exact pins; all 49 are installed at matching versions. The runbook explains setup, application/test commands, frozen-artifact non-regeneration, dataset boundaries, seed use, artifact locations, and the protected holdout.

The runbook now explicitly states that raw human submissions, identities/mappings, evidence references, and rationale-bearing workspaces are private and cannot be reproduced from a clean clone. It correctly limits clean-clone reproducibility to published code and public-safe derived artifacts.

The clean-clone evidence gap described above remains blocking: the paper's agreement and adjudication claims currently depend on local ignored aggregates. Private human review need not be reproduced, but the public claims need sanitized public evidence.

## 15. Documentation consistency

Corrected current-facing status text in `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `DEMO_GUIDE.md`, `REVIEWER_GUIDE.md`, and `REPRODUCIBILITY.md`. The corrections state that scoped human validation is complete, retain the non-ground-truth boundary, and keep external validation incomplete.

Occurrences of `157 passed` are dated Phase 2/environment snapshots tied to commit `54a4780...`, not claims about the current suite. Historical Phase 3H and Phase 3H.5 zero-review/empty-Gold-Set statements are acceptable where clearly phase-bounded or followed by a post-phase addendum. Counts `164`, `169`, `176`, `181`, `188`, and `195` were not found as current test claims.

## 16. Security and privacy audit

The tracked human-review surface contains only 14 Phase 5G/5H promotion and Gold Set files. No tracked private human ZIP, raw return, reviewer workspace, alias mapping, raw rationale, evidence-reference text, or rationale-bearing final resolution was found. No tracked credential, private-key marker, API token, or client secret was detected.

Thirteen tracked acquisition/test-fixture paths match an email-address pattern. They are public upstream GitHub metadata or a deliberately invalid URL test fixture, not reviewer contact data or secrets. Their retention should nevertheless be covered by the dataset release/privacy policy.

The original audit found absolute workspace examples in project/developer and demo instructions; no user-profile or private temporary path was tracked. Phase 7B replaced publication-facing examples with repository-relative wording while retaining the deliberate developer-only workspace instruction in `AGENTS.md`.

The privacy risk is operational rather than an index leak: the unignored Stage A/B private files listed in repository status could be captured by non-Git packaging.

## 17. Git publication audit

Tracked publication surface:

- no virtual environment, cache, pytest temp tree, local database, raw human archive, or private human workspace;
- only four controlled sample ZIPs are tracked;
- public Phase 5G/5H artifacts are tracked;
- `.env.example` contains configuration defaults only.

Local exclusion coverage is incomplete. `.git/info/exclude` protects Reviewer 01/02, Stage A workspaces, and the broad local `artifacts/human_review/` tree, but does not protect the current Stage A raw-return ZIP, Stage B archives/checksum, or `reviewer_human_adjudicator_stage_b/`. The public `.gitignore` also does not cover those private materials. Follow the project instruction not to expose sensitive filename patterns in public ignore rules automatically; add exact local exclusions or move the files to access-controlled storage before release packaging.

The inaccessible ignored `.pytest_cache/` and `.pytest_tmp/` directories produce status/test warnings but are not tracked.

## 18. Placeholder and draft audit

- **Publication blocker:** `PAPER_DRAFT.md` contains `INTERNAL DRAFT STATUS — REMOVE BEFORE SUBMISSION` and the associated internal status matrix.
- **Internal documentation only:** placeholder discussions in `LITERATURE_REVIEW_PLAN.md`, `LITERATURE_CITATION_GAPS.md`, and `LITERATURE_AUDIT.md` document completed screening/replacement work.
- No unresolved `TODO`, `TBD`, `FIXME`, `CITATION NEEDED`, or `DRAFT NOTE` marker was found in the manuscript body.

## 19. Architecture and implementation consistency

Source inspection confirms the documented operational flow: FastAPI routes call `AnalysisService`, secure extraction precedes `DriftEngine`, deterministic `RiskScorer` and explanation generation follow, and records feed HTML and JSON report routes. Analyzer files implement manifest, permission, host, API, network, obfuscation, package, structure, and JavaScript lexical processing. Risk scoring exposes the documented seven category contributions.

The source supports the static-only, partial-analyzer, no-production-ML, and heuristic source/sink boundaries described in `ARCHITECTURE.md` and the manuscript. The report routes `/report/{analysis_id}` and `/api/v1/analysis/{analysis_id}` exist; native PDF export is not implemented. The only architecture inconsistency found was stale “human review in progress” status text, corrected in this audit.

## 20. Findings and severity

| ID | Severity | Finding | Evidence | Required action |
|---|---|---|---|---|
| P7-B01 | BLOCKER | Human agreement/adjudication claims map to ignored, untracked local files; one mapped comparison includes private resolution-basis fields. | `PAPER_EVIDENCE_MAP.md`; Git index/ignore checks | Publish separately governed, sanitized aggregates and update all mappings/hashes. |
| P7-B02 | BLOCKER | Private Stage A/B archives and the Stage B workspace are untracked but not ignored. | `git status --short --untracked-files=all` | Add exact local exclusions or move to controlled private storage before any release bundle. |
| P7-B03 | BLOCKER | Manuscript contains an explicit remove-before-submission internal matrix and unresolved release/venue tasks. | `PAPER_DRAFT.md` lines 510 onward | Produce a submission copy after evidence release and venue decisions; remove internal metadata from that copy. |
| P7-M01 | MINOR | Current-status documentation still described human review as pending. | Six current-facing Markdown files | Corrected in this audit. |
| P7-M02 | MINOR | Dependency deprecations and inaccessible pytest cache paths produce warnings. | Full pytest output | Schedule dependency/cache maintenance without changing frozen research behavior. |
| P7-M03 | MINOR | Tracked upstream acquisition metadata contains public email-formatted strings. | 12 acquisition metadata paths; one test fixture path | Confirm necessity and disclosure basis in release/privacy review. |

## 21. Claims permitted

The evidence supports stating that DriftWatch:

- is a static, differential, explainable framework for security-review prioritization of supplied browser-extension version pairs;
- uses deterministic multi-signal rules and weights, not production ML, and does not output malware probability;
- has a frozen Phase 3H corpus of 76 transitions from 21 extensions with the verified label/eligibility counts above;
- protects a 10-record, 2-extension external holdout from training, tuning, rule/threshold development, and Gold Set construction;
- completed a scoped 14-case, two-reviewer blind validation with 9 agreements, 5 disagreements, 64.29% agreement, and nominal kappa approximately 0.3396;
- completed governed Stage A/Stage B adjudication for five disagreements with zero label changes and final outcomes of four risky and one uncertain;
- maintains a separate four-record, single-class, multi-reviewer-adjudicated Gold Set with zero holdout overlap and no training/tuning authorization;
- reports preliminary, frozen Phase 3E/3F observations with explicit sample-size and label-quality limitations.

## 22. Claims prohibited

The evidence does not support claims of malware detection or probability, objective ground truth, malicious intent, certified safety, production approval, population sensitivity/specificity/FPR/FNR, representative prevalence, completed external validation, generalization to all extensions, measured reviewer utility, model superiority, or “first/only/unique/unprecedented” novelty.

The Gold Set must not be described as a classifier-performance dataset or used for training, tuning, threshold/rule/weight/feature/model/hyperparameter selection under the current policy.

## 23. Release readiness by area

| Area | Status | Basis |
|---|---|---|
| A. Implementation | READY | Architecture matches code; frozen operational paths unchanged. |
| B. Tests | READY | 203 passed; no failures/errors/skips. |
| C. Reproducibility | BLOCKED | Public human-claim evidence is not available in a clean clone. |
| D. Research governance | READY | Holdout, frozen-history, eligibility, and no-tuning boundaries remain intact. |
| E. Human validation | READY WITH MINOR FIXES | Local chain and hashes verify, but sanitized public aggregates are required for release evidence. |
| F. Gold Set | READY | Hash, membership, provenance, restrictions, and privacy checks pass. |
| G. Paper | BLOCKED | Internal remove-before-submission section and unavailable evidence paths remain. |
| H. Literature | READY | 22/22 citation/reference accounting is consistent; nearest work is acknowledged. |
| I. Privacy | BLOCKED | Tracked surface is clean, but private Stage A/B material is unignored in the release working tree. |
| J. Repository hygiene | BLOCKED | Sensitive untracked/unignored files and inaccessible stale pytest temp/cache directories remain. |

## 24. Corrections made

Only verified documentation corrections were made:

- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `DEMO_GUIDE.md`
- `REVIEWER_GUIDE.md`
- `REPRODUCIBILITY.md`

This report, `FINAL_RESEARCH_AUDIT.md`, was created. No runtime code, test code, analyzer, feature, score, threshold, label, eligibility decision, holdout policy, experiment, human decision, promotion decision, or Gold Set artifact was changed.

## 25. Release blockers and next action

Do not publish or build a release from the current working directory.

1. Move the unignored private Stage A/B files to controlled private storage or add exact local-only exclusions, then verify a clean Git publication surface.
2. Approve and create rationale-free, public aggregate evidence for human agreement and adjudication; track it and replace every ignored/private evidence-map path and hash.
3. Create a submission copy of the paper after the evidence surface and venue requirements are finalized; remove the internal status matrix and repository-development notes from that copy.
4. Re-run the privacy scan, evidence-map hash audit, full tests, and `git diff --check` before release.

## 26. Final readiness decision

The implementation, tests, frozen research integrity, governed human chain, Gold Set, corpus claims, and literature accounting pass. Release is blocked by evidence availability, working-tree privacy hygiene, and an explicitly internal manuscript section.

**PHASE 7 BLOCKED — RELEASE ISSUES FOUND**

---

## Phase 7B remediation addendum — 2026-09-23

This addendum preserves the original Phase 7 findings above and records the separately authorized release-blocker remediation. It does not revise frozen research results, human decisions, promotion decisions, Gold Set membership, operational analysis, or scoring behavior.

### Private material inventory and exclusion audit

The human-review surface was classified as follows. File counts are recorded for directory-scoped entries so that every contained item inherits the stated classification; no private rationale text was opened or reproduced in this report.

| Classification | Path | Reason | Tracked | Ignored | Public-document reference after remediation |
|---|---|---|---:|---:|---|
| PUBLIC_SAFE | `artifacts/human_review/public_validation/` (3 files) | Strictly allowlisted aggregate evidence; no human reasoning, evidence references, confidence values, or identities | intended | no | Current paper/evidence/governance source |
| PUBLIC_SAFE | `artifacts/human_review/quality_promotion/` (6 files) | Previously governed rationale-free derived promotion metadata | yes | no | Current governance source |
| PUBLIC_SAFE | `artifacts/human_review/gold_set/` (8 files) | Previously governed public Gold Set artifacts and restrictions | yes | no | Current paper/governance source |
| PUBLIC_SAFE | `reviewer_b_blind/` (37 files) | Explicitly simulated/AI research material, not an independent human return or private identity map | yes | no | Not evidence for genuine human claims |
| PRIVATE_LOCAL | `reviewer_human_b/` (31 files) | Reviewer 01 delivery workspace and submission surface | no | yes | Named only as a local workspace in README/runbook; not an evidence dependency |
| PRIVATE_LOCAL | `reviewer_human_02/` (31 files) | Reviewer 02 delivery workspace and submission surface | no | yes | No current public evidence dependency |
| PRIVATE_LOCAL | `reviewer_human_adjudicator/` (31 files) | Stage A adjudicator workspace | no | yes | No current public evidence dependency |
| MIXED / MUST NOT PUBLISH | `reviewer_human_adjudicator_stage_b/` (14 files) | Stage B workspace includes human-opinion/adjudication fields | no | yes | No current public evidence dependency |
| PRIVATE_LOCAL | `DriftWatch_Independent_Human_Review_Package.zip` | Reviewer 01 delivery archive | no | yes | No current public evidence dependency |
| PRIVATE_LOCAL | `DriftWatch_Independent_Human_Review_Reviewer02_Package.zip` | Reviewer 02 delivery archive | no | yes | No current public evidence dependency |
| MIXED / MUST NOT PUBLISH | `DriftWatch_Human_Review_Raw_Return_Reviewer01_2026-09-22.zip` and `.sha256` | Immutable raw human return and its checksum | no | yes | Hash only is retained as anonymized provenance in the public manifest |
| MIXED / MUST NOT PUBLISH | `DriftWatch_Human_Review_Raw_Return_Reviewer02_2026-09-22.zip` and `.sha256` | Immutable raw human return and its checksum | no | yes | Hash only is retained as anonymized provenance in the public manifest |
| PRIVATE_LOCAL | `DriftWatch_Human_Adjudication_StageA_Package.zip` and `.sha256` | Controlled adjudicator delivery package and checksum | no | yes | No current public evidence dependency |
| MIXED / MUST NOT PUBLISH | `DriftWatch_Human_Adjudication_StageA_Raw_Return_2026-09-22.zip` | Raw Stage A adjudicator return | no | yes | Hash only is retained as provenance in the public manifest |
| MIXED / MUST NOT PUBLISH | `DriftWatch_Human_Adjudication_StageB_Package.zip` and `.sha256` | Controlled package contains de-identified prior human opinions | no | yes | Hash only is retained as provenance in the public manifest |
| MIXED / MUST NOT PUBLISH | `DriftWatch_Human_Adjudication_StageB_Raw_Return_2026-09-22.zip` | Raw final adjudicator return | no | yes | Hash only is retained as provenance in the public manifest |
| PRIVATE_LOCAL | `artifacts/human_review/reviewer01/` (18 files) | Derived Reviewer 01 integration records | no | yes | No current public evidence dependency |
| PRIVATE_LOCAL | `artifacts/human_review/reviewer02/` (19 files) | Derived Reviewer 02 integration records | no | yes | No current public evidence dependency |
| MIXED / MUST NOT PUBLISH | `artifacts/human_review/agreement/` (6 files) | Contains authoritative aggregates alongside detailed reviewer-comparison material | no | yes | Mentioned only by the preserved historical Phase 7 finding and source code; replaced in current mappings |
| PRIVATE_LOCAL | `artifacts/human_review/comparisons/` (2 files) | Human-versus-provisional comparison material outside the public claim surface | no | yes | No current public evidence dependency |
| MIXED / MUST NOT PUBLISH | `artifacts/human_review/adjudication/` (27 files) | Includes rationale-bearing final resolutions, validated wrappers, comparison prose, and source references | no | yes | Mentioned only by the preserved historical Phase 7 finding and source code; replaced in current mappings |

The former broad local exclusion for all of `artifacts/human_review/` was removed. Exact local-only exclusions now cover the five private human-review subtrees and all root workspaces/archives listed above, while `artifacts/human_review/public_validation/` remains visible for version control. No private item appears in `git status --short --untracked-files=all`.

### Public human-validation evidence

`research/human_review_publication.py` validates the three authoritative aggregate source hashes and five immutable archive hashes, rejects unexpected source/public schemas, derives aggregate values, applies exact output allowlists, recursively checks privacy constraints, and writes deterministic UTF-8/LF JSON. Generation requires controlled private inputs; verification requires only the public layer and tracked Gold Set.

Created artifacts:

| Artifact | SHA-256 | Privacy classification |
|---|---|---|
| `artifacts/human_review/public_validation/agreement_summary_public.json` | `4D6F6193E893B0A0DCEDF681CC74DA201A73FD95FDA5E61DF1A31F9062125D9F` | `PUBLIC_SAFE_AGGREGATE` |
| `artifacts/human_review/public_validation/adjudication_summary_public.json` | `1621346F09FF71055AFE709B5F7545AA5B4F82644AAC2BDE89A31DD497CEDA48` | `PUBLIC_SAFE_AGGREGATE` |
| `artifacts/human_review/public_validation/human_validation_public_manifest.json` | `583960955FEA321CCDDD9D19C9EDD9758569FB8FCCF9E6193AAAA34B316E5D46` | `PUBLIC_SAFE_AGGREGATE` |

The derived agreement artifact records 14 blind cases, 2 independent reviewers, 9 agreements, 5 disagreements, 64.29% exact agreement, observed agreement `0.6428571428571429`, expected agreement `0.4591836734693877`, and nominal unweighted Cohen's kappa `0.3396226415094341`. The derived adjudication artifact records five cases, complete Stage A/B, zero label changes, and final counts of zero benign, four risky, and one uncertain. It contains only the five record IDs and final labels—no confidence or human reasoning.

The clean-clone command `python -m research.human_review_publication verify` validates exact schemas, privacy constraints, byte hashes, agreement/kappa arithmetic, adjudication totals, the exact five-record set, and four-record Gold Set linkage. It reports `private_sources_required: false`. A clean clone can verify published aggregates and internal consistency; it cannot reconstruct intentionally withheld raw human reasoning.

### Evidence, documentation, and manuscript remediation

- `PAPER_EVIDENCE_MAP.md` now points agreement claims only to `agreement_summary_public.json`, adjudication claims only to `adjudication_summary_public.json`, and lineage to `human_validation_public_manifest.json`, with exact hashes. It no longer depends on the private Stage A/Stage B comparison.
- `DATASET_CARD.md`, `DATA_GOVERNANCE.md`, `FAILURE_ANALYSIS.md`, and the working manuscript now use the public evidence paths.
- `REPRODUCIBILITY.md` distinguishes public aggregate verification from controlled private audit and states the limits of both.
- `PAPER_SUBMISSION.md` contains the scholarly manuscript body and references but omits the repository-evidence appendix, internal status matrix, Git/release workflow, venue tasks, and private artifact notes. `PAPER_DRAFT.md` remains the working manuscript.
- A case-insensitive audit of `PAPER_SUBMISSION.md` found zero `TODO`, `TBD`, `FIXME`, `PLACEHOLDER`, `CITATION NEEDED`, `INSERT`, `DRAFT NOTE`, `INTERNAL ONLY`, or `REMOVE BEFORE SUBMISSION` markers and no internal readiness/release block.
- Manuscript claims remain exactly bounded to 14 cases, 2 reviewers, 9 agreements, 5 disagreements, 64.29%, kappa `0.3396226415`, five adjudicated disagreements, zero Stage A-to-B changes, four risky, one uncertain, and a four-record Gold Set. Agreement is not described as accuracy or ground truth.

### Release-surface, path, and metadata audit

A prospective release inventory consisting of the 727 currently tracked files plus the seven intended Phase 7B additions contains no raw reviewer/adjudication ZIP, Stage B package, private human workspace, private alias map, private human rationale, credential file, secret-bearing `.env`, or pytest temporary/cache directory. `.env.example` remains a defaults-only example. Tracked `reviewer_b_blind/` material is explicitly simulated/AI material and is not used as evidence for genuine human review.

Publication-facing documents and the public-validation tree contain no user-profile or repository absolute path. `AGENTS.md` retains a deliberate developer-only workspace instruction, and the new privacy tests contain deliberate synthetic path strings that prove rejection. README and demo setup wording is repository-relative.

The exact email-like metadata inventory contains 13 occurrences:

- eleven `git@github.com` values in `ssh_url` fields of tracked GitHub repository API snapshots; these are protocol-style repository URLs, not personal email metadata;
- one public upstream maintainer contact (`me@fregante.com`) in the captured body of Refined GitHub release `26.7`; this is upstream release metadata, not a DriftWatch participant identity; and
- one `example.com` address in an intake test fixture.

No local reviewer/adjudicator email or private personal identifier was found. The upstream release contact is retained to preserve the immutable acquisition snapshot; its classification is public upstream metadata, not unnecessary project-authored personal data.

### Frozen integrity and verification

`git diff --name-only HEAD` reports no change under analyzers, risk engine, DriftBench datasets, Phase 3H/3H.5, holdout, experiments, quality promotion, or Gold Set artifacts. Authoritative human source/archive hashes remain:

- Reviewer 01 raw archive: `E4843AE0A1241D4E69A70E2C16063DA447EB97BA82CFF2AAF92CF258D4668A5C`
- Reviewer 02 raw archive: `E9E19CDF330C5F41B794823FF9A5C02300F03A7EEEBE5139820521ACC5A57CDA`
- Stage A raw return: `C66C3D5349F701BE4ECA75C049BB0382E105B79B801F2737D7069BDBD26A11DC`
- Stage B released package: `F4703D89F32502770F428B744401466423F2152CBB1093B50109F7EF928C6C89`
- Stage B raw return: `F5990ED098DE626A748EFABC4AF452C6994F1683375AB0E0E7E6361E2F00C843`
- Phase 5C agreement aggregate: `369FFA3352E11542574618EBEECD3095271DA7DCDA4029E79C0231C3C5D10089`
- Phase 5F validation summary: `076ED1350680853540184CC22208CA53ACCE548D0C4ED241EF1714AD8C8354B2`
- Phase 5F comparison: `A94A77E84E5596F95CA3FCC5C5EEC1A008CDA53DB749CC28A801AC578B548D8E`

The complete suite passed: `223 passed, 3 warnings in 32.14s`. The warnings are the previously observed Starlette/httpx deprecation, NumPy/joblib deprecation, and inaccessible pytest-cache write warning; no test failed or skipped.

### Blocker disposition and readiness reassessment

| Finding | Remediation evidence | Residual limitation | Status |
|---|---|---|---|
| P7-B01: clean-clone human evidence gap/private comparison dependency | Three tracked-intended public artifacts, deterministic verifier, strict tests, updated evidence map | Raw human reasoning remains intentionally private and cannot be reconstructed by a clean clone | RESOLVED |
| P7-B02: unexcluded private Stage A/B material | Exact `.git/info/exclude` rules; private items absent from full untracked status; no broad public-tree exclusion | Exclusions are local Git metadata and must be preserved or private files moved before cloning/releasing elsewhere | RESOLVED FOR THIS RELEASE WORKTREE |
| P7-B03: internal submission metadata | `PAPER_SUBMISSION.md`; zero blocking marker/internal-status hits | Venue-specific formatting may still be applied without changing claims | RESOLVED |
| P7-M02: dependency/cache warnings | Full suite passes | Three non-failing maintenance warnings remain | MINOR, UNRESOLVED |
| P7-M03: email-formatted metadata | Exact 13-occurrence classification above | One public upstream contact remains in an immutable source snapshot | RESOLVED AS NON-PRIVATE METADATA |

| Area | Phase 7B status | Basis |
|---|---|---|
| Reproducibility | READY | Clean-clone aggregate verifier and explicit private-audit boundary |
| Paper | READY | Clean submission manuscript and public evidence mappings |
| Privacy | READY | Strict public allowlist/tests and locally excluded private source material |
| Repository hygiene | READY WITH MINOR FIXES | Release inventory is clean; non-failing cache/dependency warnings remain |
| Human validation publication evidence | READY | Deterministic aggregate layer, provenance hashes, privacy manifest, and Gold linkage |

Phase 7B resolves all three release blockers. No staging, commit, push, history rewrite, research regeneration, or frozen-artifact modification was performed.
