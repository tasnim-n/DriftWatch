# DriftWatch 0.2.0 Research Release Candidate 1

## A. What DriftWatch is

DriftWatch is an explainable differential behavioural security-analysis framework for Chromium-extension version transitions. It prioritizes updates for manual security review. Its risk output is not malware probability, and it does not certify an extension as safe or malicious.

## B. Main capabilities

The system securely extracts two supplied extension archives, statically analyzes manifest, permission, host, API, network, obfuscation, package, and structural evidence, computes version-to-version differences, and applies deterministic rules to produce a review-priority score and evidence-linked explanation. Uploaded extension JavaScript is never executed.

## C. Dataset scope

The frozen DriftBench Phase 3H corpus contains 76 real version-pair transitions from 21 extensions: 71 benign, 3 risky, and 2 uncertain under the frozen dataset labels. Sixty-four records are eligible for supervised research use and 12 are ineligible. Ten records from two extensions form a protected external holdout.

## D. Explainability

Outputs retain V1/V2 context, changed evidence, category contributions, triggered rules, and analyst-facing recommendations. A high score means that an update warrants attention; it does not establish intent, runtime occurrence, exfiltration, or maliciousness.

## E. Human validation

Two independent reviewers assessed the same 14 blind cases with zero external-holdout overlap. They agreed exactly on 9 cases and disagreed on 5, for 64.29% exact agreement. Unweighted nominal Cohen's kappa was 0.339622641509434 and is descriptive of this small, marginally concentrated review set, not an accuracy result.

## F. Adjudication

All five disagreements completed governed Stage A and Stage B adjudication. No Stage A label changed at Stage B. Final outcomes were four `RISKY_TRANSITION`, one `UNCERTAIN`, and zero `BENIGN_TRANSITION`.

## G. Gold Set

Four definitive risky cases qualified for `driftwatch-human-gold-set-v1` (`GOLD1::367B78340517770D9DB1E5DABE1DCA63399829A5FA5B64756C820F7696EEA0B8`). All four are `MULTI_REVIEWER_ADJUDICATED`; external-holdout overlap is zero. The set is small and single-class. Training, tuning, threshold selection, rule development, weight tuning, feature selection, and model selection are prohibited without separate governed authorization.

## H. Reproducibility

The repository records the Python 3.14.0 verification environment, a package lock, test commands, frozen artifacts, public hashes, and a claim-to-artifact map. Public aggregate claims can be checked in a clean clone; raw human reasoning cannot be reconstructed from public content.

## I. Privacy and governance

The public validation layer contains aggregate facts, final labels for the five adjudicated disagreements, deterministic hashes, and governance linkage. It omits reviewer identities, raw submissions, rationale, private evidence references, and detailed adjudication records. The protected external holdout remains unavailable for training, tuning, threshold or rule selection, feature redesign, and Gold Set construction.

## J. Known limitations

The corpus is small and imbalanced, most frozen dataset labels remain provisional, the human-validation sample is 14 cases, and the Gold Set contains only four risky cases. Static evidence cannot determine intent or guarantee runtime behaviour. External validation remains incomplete, and reviewer utility was not measured.

## K. Unsupported claims

This release does not support claims of malware-detection accuracy, sensitivity, specificity, population false-positive or false-negative rates, representative prevalence, external validity, production safety, universal browser-extension coverage, or objective maliciousness ground truth. It also does not claim that DriftWatch is the first or only extension update-delta system.

## L. How to verify the release

From the repository root:

```powershell
python -m research.human_review_publication verify
python -m pytest -q

$releaseExpected = (Get-Content RELEASE_MANIFEST.sha256).Split()[0]
$releaseActual = (Get-FileHash RELEASE_MANIFEST.json -Algorithm SHA256).Hash
if ($releaseActual -ne $releaseExpected) { throw "Release manifest checksum mismatch" }

$goldDirectory = "artifacts\human_review\gold_set\driftwatch-human-gold-set-v1"
$goldExpected = (Get-Content "$goldDirectory\gold_set_manifest.sha256").Split()[0]
$goldActual = (Get-FileHash "$goldDirectory\gold_set_manifest.json" -Algorithm SHA256).Hash
if ($goldActual -ne $goldExpected) { throw "Gold Set manifest checksum mismatch" }
```

Read `PAPER_SUBMISSION.md`, `PAPER_EVIDENCE_MAP.md`, `REPRODUCIBILITY.md`, and `RELEASE_INVENTORY.md` for the manuscript, evidence boundary, verification details, and public archive scope.
