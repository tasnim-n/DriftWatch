# DriftWatch Research Release Inventory

## Scope

This inventory describes the intended `0.2.0-research-rc1` public release surface. It combines the 735 paths tracked at source commit `23ac32fdde3afecd9318f8d485ea7875fbc8b41e` with the six Phase 8A release-metadata paths listed below. Once those paths are reviewed and committed, the candidate contains 741 files.

Counts are mutually exclusive. Paths are classified by function, with the three public human-validation evidence trees classified before their parent `artifacts/` tree.

| Category | Files | Included content |
|---|---:|---|
| Application/source | 19 | FastAPI application, risk engine, architecture/security guidance, and top-level project entry documentation |
| Analyzers | 10 | Static manifest, permission, host, API, network, obfuscation, and structural analyzers |
| Tests | 31 | Unit, integration, governance, privacy, and public-verification tests |
| Research methodology | 61 | DriftBench and research modules plus methodology, governance, review-policy, case-study, failure-analysis, and audit documents |
| Public dataset/governance artifacts | 562 | Tracked dataset, feature, experiment, provenance, readiness, and simulated-workflow artifacts outside the three evidence classes below |
| Public human-validation evidence | 3 | Rationale-free agreement summary, adjudication summary, and public validation manifest |
| Quality-promotion evidence | 6 | Derived quality-promotion view, manifests, governance summary, readiness assessment, and validation report |
| Gold Set | 8 | Governed four-record Gold Set manifest, checksum, restrictions, provenance, audits, summary, and assessment |
| Reproducibility/environment | 14 | Environment and dependency records, repository controls, reproducibility runbook, and Phase 8A release metadata |
| Literature | 5 | Search plan, verified and rejected sources, citation-gap record, and literature audit |
| Manuscript | 4 | Draft, submission-clean manuscript, evidence map, and figure plan |
| Demo/sample artifacts | 18 | Controlled synthetic extension samples and demonstration guide |
| **Total intended release** | **741** | **735 baseline tracked paths + 6 Phase 8A paths** |

## Phase 8A additions

- `RELEASE_INVENTORY.md`
- `RELEASE_MANIFEST.json`
- `RELEASE_MANIFEST.sha256`
- `RELEASE_NOTES.md`
- `PAPER_FIGURE_PLAN.md`
- `RELEASE_CHECKLIST.md`

`README.md` and `.gitattributes` are updated tracked paths, not additions. The latter applies LF normalization only to governed human-validation evidence and the checksummed release-manifest pair.

## Intentionally excluded private categories

The public release excludes:

- raw Reviewer 01 and Reviewer 02 return ZIPs;
- raw Stage A and Stage B returns and the Stage B reviewer package;
- reviewer and adjudicator workspaces;
- reviewer identity or alias mappings;
- rationale-bearing human submissions and adjudication records;
- private evidence references and identity-bearing notes;
- local acquisition archives and other ignored raw-corpus material; and
- credentials, secret-bearing environment files, local virtual environments, caches, pytest temporary output, and clean-clone scratch directories.

The tracked `reviewer_b_blind/` directory is a clearly identified simulated/AI-assisted workflow demonstration, not private human-review evidence and not independent ground truth.

## Archive boundary

The eventual public archive should be created from the reviewed release commit with `git archive`, not by compressing a developer workspace. This makes the inventory boundary the Git tree and prevents ignored private/local material from entering the archive.
