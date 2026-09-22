# DriftWatch Failure Analysis

## Scope and terminology

This document synthesizes frozen Phase 3E, Phase 3F, Phase 3H, and Phase 3H.5 artifacts. It does not rerun experiments, change labels, or treat simulated review as human evidence.

An error against a `SINGLE_REVIEWER_PROVISIONAL` label is not definitive. Accordingly:

- **Provisional apparent false positive** means a deterministic system prioritized a transition whose current provisional dataset label is `benign_transition`.
- **Provisional apparent false negative** means an exploratory model did not prioritize a transition whose current provisional dataset label is review-worthy.
- Neither term establishes the transition's final ground truth.

Risk scores are review-priority signals, not malware probabilities. Exploratory ML outputs are research probabilities for the experiment target, not operational scores.

## A. Apparent deterministic false alarms

### Existing held-out observations

The frozen Phase 3E held-out error analysis records four provisional apparent false positives for the deterministic scorer:

| Transition | Deterministic result | Static features recorded in the error artifact |
|---|---:|---|
| `subtidex_1_5_0_to_1_5_1` | REVIEW_WORTHY, score 60 | 15 new external-network indicators, obfuscation score 30, 2 source/sink heuristics |
| `ublock_origin_1_70_0_to_1_71_0` | REVIEW_WORTHY, score 60 | 16 network indicators, obfuscation score 95, 3 source/sink heuristics |
| `ublock_origin_1_71_0_to_1_72_0` | REVIEW_WORTHY, score 60 | 10 network indicators, obfuscation score 75, 3 source/sink heuristics |
| `ublock_origin_1_72_2_to_1_73_0` | REVIEW_WORTHY, score 60 | 5 network indicators, obfuscation score 45, 3 source/sink heuristics |

Phase 3F repeats those four observations in its expanded held-out study and adds four Stylus transitions, producing eight provisional apparent false positives in that phase. The added Stylus scores range from 54 to 60 and are likewise associated with network indicators, obfuscation scores, and source/sink heuristics. Counts from Phase 3E and Phase 3F must not be summed as independent errors because some records are intentionally preserved across both studies.

### Likely mechanisms requiring investigation

- **Large benign or maintenance updates:** legitimate feature additions can touch many files and introduce numerous strings, functions, and listeners.
- **Bundled dependencies and generated code:** build output can repeat endpoints, dynamic-code idioms, or high-entropy strings.
- **Network-indicator inflation:** static literals and sink arguments may be counted even if unreachable or never used at runtime.
- **Minification/obfuscation ambiguity:** compressed distribution bundles can resemble concealment techniques.
- **Heuristic source/sink co-occurrence:** sources and sinks in one file can trigger review without proving a connected data flow.

These mechanisms explain why deterministic prioritization can have a high false-alert cost. They do not prove that every alert is erroneous; the labels used for this comparison remain provisional.

## B. Exploratory ML misses

Both frozen pilot and replication error artifacts identify the same held-out case: `katex-github-chrome-extension_0_1_0_to_0_2_0`.

| Experiment | Method | Exploratory output | Experiment classification |
|---|---|---:|---|
| Phase 3E | Logistic Regression | 0.262991 | BENIGN |
| Phase 3E | Random Forest | 0.109542 | BENIGN |
| Phase 3F | Logistic Regression | 0.332308 | BENIGN |
| Phase 3F | Random Forest | 0.155 | BENIGN |
| Phase 3E and Phase 3F | Deterministic rule engine | 70.5/100 | Critical / REVIEW_WORTHY |

The available static drift included host-scope-score delta 90, permission-risk delta 10, one introduced service worker, 822 new external-network indicators, and added-obfuscation score 530. The deterministic rule engine highlighted the combination, while both exploratory models assigned probabilities below their classification threshold.

This is a narrow pilot observation, not evidence that exploratory ML is generally inferior. The corpus is small, class-imbalanced, and provisionally labeled; model behavior may reflect limited risky-class support, representation choice, regularization, or unstable decision boundaries. Production ML integration remains unjustified, and the Phase 3F replication conclusion is `INCONCLUSIVE`.

## C. Ambiguous transitions

Two transitions remain explicitly unresolved and training-ineligible:

1. `save-sora_2_0_355_to_3_0_0`
2. `save-sora_3_0_0_to_3_0_10`

The Phase 3H.5 unresolved-record artifact says both were carried forward from the frozen pilot with insufficient evidence to strengthen the label. It identifies the missing evidence as:

- an independent reviewer assessment;
- maintainer or vendor clarification; and
- corroborating public security reporting or issue discussion.

The first transition has no permission, host, or network-count delta but still records an added API, obfuscation score 295, 1,239 added functions, and one source/sink heuristic. The second records three added APIs, 470 new external-network indicators, obfuscation score 280, 1,269 added functions, and two source/sink heuristics. Those static signals justify examination but do not resolve intent or impact. Their status remains `UNCERTAIN`, and neither record is eligible for supervised training.

## D. Signal-specific limitations

### Endpoint and network counts

Static network counts can include repeated strings, bundled libraries, source maps, generated assets, examples, tests, dead code, and multiple syntactic occurrences of the same destination. A “new external” indicator means it was observed in V2 and not matched in V1 under the analyzer's comparison logic; it does not mean a runtime request occurred. Addition counts can exceed net count deltas when additions and removals coexist.

### Obfuscation and minification

Dynamic execution, encoded strings, entropy, and minified structures are review signals, not intent evidence. Legitimate build pipelines can introduce them. Added-obfuscation score and net obfuscation-count delta answer different questions and can move in opposite directions, as seen in the Save Sora flagship case.

### Source-to-sink heuristics

The current structural signal is same-file source/sink co-occurrence. It does not establish control flow, data dependence, reachability, sanitization behavior, or an actual outbound transfer. It must be described as a heuristic indicator, never proven exfiltration.

### Structural churn

Added-function, event-listener, modified-file, and size deltas can be dominated by refactoring, formatter changes, bundle regeneration, or dependency churn. Added counts and net deltas are not interchangeable. For example, a transition can contain many newly matched functions while the total function count decreases.

### Permission and API changes

Permission or host expansion is observable and security-relevant, but legitimate features may require it. API-introduction flags require line-level and release-context review. Conversely, unchanged permissions do not imply unchanged behavior: Refined GitHub and Browserpass demonstrate code-level signals without permission expansion.

### Cross-artifact representation differences

For Browserpass 3.11.0 → 3.12.0, the Phase 3H full feature row records `content_script_changed=1`, while the Phase 3H.5 review packet records `content_scripts_changed=false`. The discrepancy is preserved and disclosed rather than silently resolved. Conclusions should not depend on that field until the representations are audited.

## E. Label-quality limitations

All records in the Phase 3E and Phase 3F held-out error analyses use `SINGLE_REVIEWER_PROVISIONAL` labels. The label-sensitivity artifacts report no sufficiently large higher-confidence, multi-reviewer, or externally confirmed subset containing both target classes. The later governed Gold Set contains four `MULTI_REVIEWER_ADJUDICATED` risky transitions but no benign comparison class, and its policy does not authorize training or tuning. Therefore:

- an apparent rule error may instead be a provisional-label error;
- an apparent ML miss may change after independent review;
- error rates should not be generalized to a browser-store population;
- simulated reviewer output cannot be substituted for the completed genuine human workflow; and
- the protected external holdout remains unevaluated for formal external validation.

In the completed scoped human review, two independent reviewers disagreed on 5 of 14 cases despite seeing identical blind evidence. This is direct evidence that ambiguous behavioral deltas, incomplete semantic context, and benign-but-security-relevant changes can support different judgments. All five disagreements completed governed adjudication, but adjudication strengthens provenance rather than proving objective truth. The resulting four-record Gold Set is too small and single-class to estimate error rates. Formal external validation remains incomplete.

## Research implications

The deterministic system is useful as a transparent prioritizer but can over-prioritize feature-rich updates. Exploratory ML can suppress some false alerts but missed the only held-out provisionally review-worthy case in both frozen experiments. Human disagreement further shows that the review target itself contains uncertainty. The appropriate conclusion is not that one method is universally superior; it is that stronger and more diverse labels, larger class support, artifact-level audits, and analyst-facing evidence are necessary before broader performance or deployment claims.

## Evidence references

- `artifacts/experiments/phase3e/false_positive_analysis.json`
- `artifacts/experiments/phase3e/false_negative_analysis.json`
- `artifacts/experiments/phase3e/error_analysis.json`
- `artifacts/experiments/phase3e/label_sensitivity.json`
- `artifacts/experiments/phase3f/error_analysis.json`
- `artifacts/experiments/phase3f/replication_conclusion.json`
- `artifacts/experiments/phase3f/label_sensitivity.json`
- `artifacts/driftbench/phase3h5/unresolved_records.json`
- `artifacts/driftbench/phase3h_features/full_driftwatch.csv`
- `artifacts/human_review/agreement/reviewer01_vs_reviewer02/agreement_summary.json`
- `artifacts/human_review/adjudication/final/human_validation_summary.json`
- `artifacts/human_review/gold_set/driftwatch-human-gold-set-v1/gold_set_summary.json`
