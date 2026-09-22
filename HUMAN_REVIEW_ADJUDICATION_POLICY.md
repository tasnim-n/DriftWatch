# Human-Review Adjudication Policy

## Policy identity and scope

- Policy version: `driftwatch-human-adjudication-v1`
- Review-ID policy: `driftwatch-adjudication-id-v1`
- Applies to: governed resolution of disagreements between documented independent human reviewers
- Current scope: the five Reviewer 01 / Reviewer 02 disagreements in the 14-case blind review set

Adjudication resolves a documented disagreement; it does not determine malware probability, prove maliciousness, overwrite an original review, or authorize system tuning.

## Adjudicator independence

The adjudicator should be a third human who:

- was not Reviewer 01 or Reviewer 02;
- did not create the original provisional dataset labels;
- did not design or tune DriftWatch features, analyzers, scoring weights, thresholds, rules, or models for the reviewed cases;
- has no personal, employment, authorship, financial, or other material conflict affecting the reviewed extensions or their maintainers;
- did not see human-human agreement results, Cohen's kappa, or either reviewer's decisions before completing Stage A; and
- declares any newly discovered conflict before continuing.

If no suitably independent human is available, adjudication remains pending. A project author may not silently substitute for an independent adjudicator.

The prospective neutral identifier for the first assigned adjudicator is `human_adjudicator_01`. This identifier reserves a workflow role; it does not assert that a person has been assigned or that adjudication has occurred.

## Exactly two adjudication stages

### Stage A — independent third assessment

Stage A uses `review_round=ADJUDICATION_STAGE_A`. The adjudicator receives only the original blind evidence packet for each disagreement case and independently records:

- `adjudicator_initial_label`;
- `adjudicator_initial_confidence`;
- `adjudicator_initial_rationale`;
- packet-field `evidence_references`;
- `blind_review=true`;
- `review_status`;
- `review_timestamp`;
- `adjudicator_id`;
- `record_id`; and
- a prospectively assigned `review_id`.

All five Stage A submissions must be complete, validated, hashed, and preserved before Stage B is releasable. Stage A records become immutable when accepted by the release gate.

Stage A must not expose Reviewer 01 or Reviewer 02 labels, confidence, rationales, or evidence references; provisional project labels; DriftWatch scores, severities, recommendations, or rule output; ML output; agreement statistics; Cohen's kappa; Gold Set status; simulated-review material; or later analysis.

### Stage B — governed resolution

Stage B uses `review_round=ADJUDICATION_STAGE_B`. It is released only after the programmatic Stage A gate reports `RELEASABLE` for all five cases. The adjudicator receives de-identified `Reviewer A` and `Reviewer B` opinions containing each original label, confidence, verbatim rationale, and evidence references. Personal reviewer identities and the private A/B source mapping remain hidden.

Stage B records:

- `final_adjudicated_label`;
- `adjudication_confidence`;
- `adjudication_rationale`;
- `adjudication_evidence_references`;
- `initial_label_changed`;
- `change_reason`;
- `resolution_basis`;
- `review_timestamp`;
- `review_status=SUBMITTED`; and
- `review_round=ADJUDICATION_STAGE_B`.

The final record is a new linked adjudication record. Stage A and both source reviews remain immutable.

## Permissible evidence

Stage A permits only evidence already present in the original blind packet. No regenerated analyzer output, new project interpretation, system result, or reviewer opinion may be added.

Stage B permits:

- the unchanged Stage A record;
- the original blind packet;
- the two de-identified source opinions with verbatim rationales and evidence references;
- the governed label definitions and evidence hierarchy; and
- provenance metadata needed to establish integrity without revealing personal reviewer identities.

No simulated reviewer material may be used.

## Label ontology and confidence

Permitted labels are exactly:

- `BENIGN_TRANSITION`
- `RISKY_TRANSITION`
- `UNCERTAIN`
- `MALICIOUS_TRANSITION`
- `EXCLUDED`

Permitted confidence values are `HIGH`, `MEDIUM`, and `LOW`. Confidence is not probability.

`UNCERTAIN` remains valid when evidence is insufficient or contradictory. It must not be forced to benign or risky. `RISKY_TRANSITION` means security review is warranted and does not imply maliciousness. `MALICIOUS_TRANSITION` requires strong supplied evidence of intentionally harmful behaviour; disagreement alone is never sufficient.

## Provenance and immutability

Every adjudication artifact must retain the source record ID, deterministic review ID, review round, source hashes, policy versions, and timestamps. Raw reviewer returns, original submissions, Stage A submissions, and reviewer wording must not be rewritten, merged, summarized as replacements, or deleted. Corrections require a new linked artifact with explicit provenance.

Reviewer A/B aliases are derived deterministically and recorded only in private provenance metadata. The adjudicator-facing Stage B material must not reveal the source mapping.

## Unresolved cases

If evidence remains insufficient after Stage B, the final label may remain `UNCERTAIN`. If the adjudicator has a conflict, required evidence is missing, source integrity fails, or the Stage A gate fails, the case remains unresolved and no label-quality promotion occurs.

## Label quality and Gold Set relationship

Two-reviewer agreement alone does not satisfy the current `MULTI_REVIEWER_ADJUDICATED` tier because no adjudication occurred. The repository currently defines no `MULTI_REVIEWER_AGREED` tier. A future derived quality state may distinguish genuine agreement, but introducing it requires a separately reviewed policy and must not mutate frozen dataset labels.

After valid Stage B completion, a disagreement case may be assessed prospectively for `MULTI_REVIEWER_ADJUDICATED`. Qualification requires complete provenance, preserved source reviews and Stage A, a valid Stage B record, an allowed final label, a nonblank rationale and evidence references, and explicit governed promotion. `UNCERTAIN` and `EXCLUDED` do not qualify for the existing Gold Set. Promotion is not automatic.

Gold Set inclusion is a separate decision. Under the frozen Phase 3H.5 policy, only `EXTERNAL_CONFIRMED`, genuine `MULTI_REVIEWER_ADJUDICATED`, or explicitly separated `CONTROLLED_GROUND_TRUTH` records with complete provenance and a qualifying non-uncertain label may qualify. External-holdout records remain excluded from Gold Set construction under the current protected policy.

## Prohibition on tuning and automatic promotion

Adjudication results must not be used to tune feature extraction, analyzers, deterministic scoring, risk weights, thresholds, rules, review selection, or ML experiments. They must not automatically change dataset labels, training eligibility, external-holdout membership, label-quality tiers, or Gold Set membership. Any later promotion requires an explicit, versioned, audited governance phase.
