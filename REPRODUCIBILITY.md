# DriftWatch Reproducibility Runbook

This runbook distinguishes safe verification from artifact-generating research workflows. It is intended to help researchers inspect DriftWatch without silently changing frozen results.

## Environment

- Project metadata supports Python `>=3.10`.
- The environment verified on 2026-09-21 used Python `3.14.0` on Windows 11 (`Windows-11-10.0.26200-SP0`).
- Exact packages from that working environment are recorded in `requirements-research-lock.txt`.
- `requirements.txt` and `pyproject.toml` retain the project's broad minimum dependency policy; the research lock is a snapshot, not a replacement for that policy.

The documented commands use Windows PowerShell. The Python application may run on other operating systems, but this repository does not claim an equivalent verified research environment for them.

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

To recreate the verified research package set instead of resolving current minimum dependencies:

```powershell
python -m pip install -r requirements-research-lock.txt
```

Do not upgrade or downgrade an established research environment immediately before artifact verification.

## Application Run

With the virtual environment active:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

The implemented report surfaces are an HTML report route and a JSON API endpoint. PDF export is not implemented.

## Test Verification

```powershell
python -m pytest -q
```

Fresh verification on 2026-09-21 at commit `54a4780d58ac12b4c794145b773da5e2c15a6999` produced:

```text
157 passed in 32.55s
```

There were 0 failures, 0 skips, and no warnings reported under the repository's configured pytest warning filters.

A later Phase 7 audit on 2026-09-23, based on commit `3412522eb7c1ae8c05ac90b115cbf38032210577`, produced `203 passed`, 0 failures, and 0 skips. It reported two dependency deprecation warnings and one pytest cache-path warning; no application or research test failed.

The Phase 8A release-candidate audit on 2026-09-23 used source baseline `23ac32fdde3afecd9318f8d485ea7875fbc8b41e` and produced `223 passed`, 0 failures, 0 errors, and 0 skips. With default warning visibility enabled, it reported the same two dependency deprecation warnings and one pre-existing pytest cache-path warning.

## Repository Commit

- Branch at verification: `main`
- Commit: `54a4780d58ac12b4c794145b773da5e2c15a6999`
- Phase 8A source baseline: `23ac32fdde3afecd9318f8d485ea7875fbc8b41e`

Research conclusions should identify both the relevant artifact version and source commit. A later working-tree state must not be represented as this verified commit.

## Research Artifact Policy

### Safe to verify

The following operations read existing state and do not regenerate research outputs:

- `git status --short`
- `git rev-parse HEAD`
- parsing existing JSON, JSONL, CSV, and Markdown artifacts;
- hashing existing artifacts;
- running `python -m pytest -q` (tests use temporary output locations for generated experiment fixtures); and
- running the application on controlled local inputs, provided resulting database records are not represented as frozen experiment artifacts.

### Do not regenerate without an explicit research decision

Do not run the default Phase 3E, 3F, 3G, 3H, or 3H.5 module entry points merely to verify the repository. Their default paths generate or overwrite versioned research artifacts. Do not regenerate frozen phases to refresh timestamps, test counts, metrics, or documentation.

The protected external holdout must remain excluded from training, tuning, threshold selection, rule development, feature redesign, and Gold Set construction.

## Random Seeds

Existing Phase 3E and Phase 3F experiment artifacts use seed `1337`. This runbook does not introduce a new seed. Later phases that do not train models should not be described as seeded ML experiments.

## Dataset Availability

Raw incoming and validated archive directories are excluded from Git. A clean clone therefore does not contain every local corpus archive.

Raw human-review ZIPs, reviewer submissions, identity/alias mappings, evidence references, and rationale-bearing adjudication workspaces are intentionally local and are not reproducible from a clean clone. The tracked release surface contains a rationale-free public human-validation evidence layer, derived quality-promotion artifacts, and the Gold Set. A clean-clone researcher can verify those published aggregates, their internal arithmetic, their recorded source hashes, and their Gold Set linkage, but cannot reconstruct the original private human judgments from repository contents alone.

### Public reproducibility

A clean clone contains the implementation and tests, the aggregate human-validation evidence under `artifacts/human_review/public_validation/`, the governed Gold Set and promotion metadata, the literature audit, and `PAPER_EVIDENCE_MAP.md`. Verify the aggregate evidence without private inputs by running:

```powershell
python -m research.human_review_publication verify
```

This command validates strict public schemas and privacy allowlists, deterministic artifact hashes, agreement arithmetic and kappa components, adjudication totals, the exact public record set, and Gold Set linkage. It does not open or require private reviewer or adjudicator material.

Verify the release manifest and Gold Set manifest byte hashes with:

```powershell
$releaseExpected = (Get-Content RELEASE_MANIFEST.sha256).Split()[0]
$releaseActual = (Get-FileHash RELEASE_MANIFEST.json -Algorithm SHA256).Hash
if ($releaseActual -ne $releaseExpected) { throw "Release manifest checksum mismatch" }

$goldDirectory = "artifacts\human_review\gold_set\driftwatch-human-gold-set-v1"
$goldExpected = (Get-Content "$goldDirectory\gold_set_manifest.sha256").Split()[0]
$goldActual = (Get-FileHash "$goldDirectory\gold_set_manifest.json" -Algorithm SHA256).Hash
if ($goldActual -ne $goldExpected) { throw "Gold Set manifest checksum mismatch" }
```

### Private audit reproducibility

Raw review returns and rationale-bearing adjudication records are retained outside the public release surface for controlled-access audit. The generation mode validates their authoritative hashes and derives the public projection, but it is intentionally unavailable to a clean clone without those private inputs. Access to the public artifacts therefore supports verification of published aggregate claims and provenance commitments—not independent reconstruction of withheld human reasoning.

Existing acquisition, import, dataset, and provenance manifests include:

- `datasets/manifests/real_pilot_import_manifest.json`
- `datasets/manifests/phase3f_import_manifest.json`
- `datasets/manifests/phase3g_import_manifest.json`
- `datasets/manifests/phase3h_import_manifest.json`
- `artifacts/driftbench/phase3h/dataset_manifest.json`
- `artifacts/driftbench/phase3h/provenance_manifest.json`

These manifests document the existing sources and hashes. They do not guarantee that a remote release asset will remain available. Do not substitute different archives while claiming exact reproduction.

## Phase Commands

The following module entry points are verified from source, but they are artifact-generating commands and are listed for documentation only:

| Command | Behaviour | Default-output risk |
|---|---|---|
| `python -m research.phase3e` | Reads curated Phase 3E inputs, trains research-only models, and writes experiment/model artifacts | Overwrites or regenerates frozen Phase 3E outputs |
| `python -m research.phase3f` | Builds the Phase 3F replication corpus/features/evaluation | Overwrites or regenerates frozen Phase 3F outputs |
| `python -m research.phase3g` | Builds Phase 3G maturation artifacts | Overwrites or regenerates frozen Phase 3G outputs |
| `python -m research.phase3h` | Builds Phase 3H corpus, features, holdout, and readiness artifacts | Overwrites or regenerates frozen Phase 3H outputs |
| `python -m research.phase3h5` | Builds Phase 3H.5 review-workflow and eligibility artifacts | Overwrites or regenerates frozen Phase 3H.5 outputs |

The intake command also writes reports, including when `--dry-run` is used. Use a disposable output directory if independently testing intake behaviour:

```powershell
python -m driftbench.ingest --manifest datasets\manifests\import_manifest.example.json --dry-run --output <temporary-directory>
```

Do not point this command at an existing frozen artifact directory.

## Expected Outputs

Important existing outputs include:

| Purpose | Path |
|---|---|
| Phase 3H dataset statistics | `artifacts/driftbench/phase3h/dataset_statistics.json` |
| Phase 3H dataset manifest | `artifacts/driftbench/phase3h/dataset_manifest.json` |
| Protected external holdout | `artifacts/driftbench/phase3h/external_holdout_manifest.json` |
| Phase 3H feature artifacts | `artifacts/driftbench/phase3h_features/` |
| Phase 3H.5 eligibility | `artifacts/driftbench/phase3h5/eligibility_report.json` |
| Phase 3H.5 review queue | `artifacts/driftbench/phase3h5/review_queue.json` |
| Phase 3H.5 canonical review packets | `artifacts/driftbench/phase3h5/review_packets/` |
| Independent human-review delivery workspace | `reviewer_human_b/` |
| Public human-validation aggregate evidence | `artifacts/human_review/public_validation/` |

The human-review workspace is a scoped 14-record delivery package, not a replacement for the canonical 76-record Phase 3H.5 review scope.

## Verification-Only Workflow

The following sequence verifies key facts without running any phase generator:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short

$stats = Get-Content artifacts\driftbench\phase3h\dataset_statistics.json -Raw | ConvertFrom-Json
$holdout = Get-Content artifacts\driftbench\phase3h\external_holdout_manifest.json -Raw | ConvertFrom-Json
$eligibility = Get-Content artifacts\driftbench\phase3h5\eligibility_report.json -Raw | ConvertFrom-Json
$queue = Get-Content artifacts\driftbench\phase3h5\review_queue.json -Raw | ConvertFrom-Json

$stats | ConvertTo-Json -Depth 4
$holdout.record_count
$eligibility.eligible_for_supervised_training_count
$eligibility.ineligible_count
$queue.records.Count

python -m pytest -q
```

Expected frozen facts at the verified commit are 76 transitions, 10 protected holdout records, 64 supervised-training-eligible records, 12 ineligible records, and 76 canonical queue records. Treat discrepancies as an audit condition; do not regenerate artifacts to make them match.
