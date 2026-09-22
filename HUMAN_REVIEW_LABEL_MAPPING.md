# Human-Review Label Mapping Policy

## Policy identity

- Mapping version: `driftwatch-human-review-label-mapping-v1`
- Status: prospective governed integration policy
- Applies to: derived comparisons between Phase 3H.5 independent human-review submissions and the DriftBench dataset ontology
- Source ontologies: `research.phase3h5.ALLOWED_REVIEW_LABELS` and `driftbench.labels.LABEL_ONTOLOGY`

This policy is based only on semantic compatibility between the documented label definitions. It was not selected or adjusted to improve observed Reviewer 01 concordance.

## Canonical mapping

| Human-review label | Dataset comparison label | Comparable | Rationale |
|---|---|---:|---|
| `BENIGN_TRANSITION` | `benign_transition` | Yes | Both describe a transition judged not to introduce a meaningful unsupported security-sensitive change. |
| `RISKY_TRANSITION` | `risky_transition` | Yes | Both describe a security- or privacy-relevant transition warranting analyst review without requiring malicious intent. |
| `UNCERTAIN` | `uncertain` | Yes | Both retain a transition when evidence is insufficient, contradictory, or ambiguous. |
| `MALICIOUS_TRANSITION` | `malicious_transition` | Yes | Both require strong evidence that intentionally harmful behaviour was introduced. This mapping does not relax that evidence requirement. |
| `EXCLUDED` | `excluded` | Yes | Both identify a record as methodologically unsuitable rather than assigning a behavioural class. |

Any human-review label not listed above maps to `NOT_COMPARABLE`. Unknown labels must not be coerced into a known category. In particular, malicious labels must not be collapsed into risky labels, and excluded labels must not be collapsed into uncertain labels.

Dataset-only labels without a human-review equivalent, including `controlled_malicious_transition` and `needs_review`, are `NOT_COMPARABLE` under this mapping version.

## Intended uses

This mapping may be used to:

- construct a separate human-vs-provisional comparison artifact;
- mark individual records as comparable or not comparable;
- calculate descriptive exact concordance over comparable records only; and
- produce category cross-tabulations that retain both original labels.

The required terminology is **human-vs-provisional label concordance**. Existing DriftBench labels remain provisional and are not a documented independent second human rating.

## Prohibited uses

This mapping must not be used to:

- overwrite either the human judgement or the frozen dataset label;
- claim human-human inter-rater agreement, reviewer consensus, or Cohen's kappa;
- treat the human label as automatic ground truth;
- adjudicate a disagreement;
- create or qualify a Gold Set;
- change training eligibility or external-holdout membership;
- tune features, analyzers, scores, weights, thresholds, rules, or models; or
- reinterpret `RISKY_TRANSITION` as proven maliciousness.

## Preservation and versioning

Original reviewer labels must be preserved verbatim in validated-submission artifacts. Mapped labels may appear only in explicitly derived comparison artifacts. Applying this policy does not alter raw reviewer evidence, original reviewer wording, frozen dataset labels, or frozen Phase 3H/3H.5 artifacts.

Any semantic change requires a new mapping version and a written rationale. Prior comparison artifacts must retain the mapping version under which they were generated.
