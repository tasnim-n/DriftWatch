# Human-Review Derivation Policy

## Policy identity

- Policy version: `driftwatch-human-review-id-v1`
- Derived artifact schema: `driftwatch-validated-human-review-v1`
- Purpose: add deterministic integration metadata without changing immutable reviewer evidence

## Derived review-ID format

The canonical derived identifier is:

```text
HRV1::<reviewer_id>::<record_id>::<review_round>
```

For example:

```text
HRV1::human_reviewer_01::subtidex_1_5_0_to_1_5_1::INITIAL_BLIND
```

The identifier is:

- deterministic: the same input fields always produce the same value;
- unique within the governed review corpus when reviewer, record, and round are unique;
- reproducible without timestamps or random values;
- reviewer-aware;
- record-aware;
- review-round-aware; and
- versioned through the `HRV1` prefix and policy-version metadata.

Input identifiers must be nonempty and must not contain the `::` delimiter. Derived IDs are compared exactly and case-sensitively.

## Reviewer 01 legacy omission

The Reviewer 01 distribution template omitted `review_id` even though the canonical Phase 3H.5 reviewer schema declared it required. The immutable raw return must not be edited.

During governed integration, the derived layer records:

- `raw_source_sha256`;
- `raw_submission_filename`;
- `raw_submission_sha256`;
- `derived_review_id`;
- `reviewer_id`;
- `record_id`; and
- `review_round`.

The original submission object is preserved as submitted. The derived identifier is wrapper metadata, not a correction inserted into the raw human evidence.

## Reviewer 02 package and authoritative-return policy

Reviewer 02 submission files receive preassigned IDs using the same format and `human_reviewer_02`. These IDs appear in the new package before review and must not be changed by the reviewer.

The generic Reviewer 02 template includes the `review_id` field, while each case-specific submission contains its fully resolved unique value.

The authoritative first completed Reviewer 02 return contains blank `review_id` values. The immutable raw return is not corrected. The governed integration layer derives the expected `HRV1` identifier from `reviewer_id`, `record_id`, and `review_round`, preserves the blank submitted value inside `original_submission`, and records the derived value only as wrapper metadata.

Reviewer 02 confirmed that the timestamps in the authoritative first return were placeholders. The raw values remain preserved, while the derived layer marks them `PLACEHOLDER_CONFIRMED`. They must not be used to establish review identity, ordering, independence, elapsed time, or agreement validity.

The first completed Reviewer 02 return is the only authoritative Reviewer 02 input for agreement. Later redo or corrected attempts are provenance/history only and must be excluded from agreement, adjudication, Gold Set qualification, paper results, and label promotion.

## Validation requirements

The derived integration layer must:

- verify the raw source SHA-256 before reading submissions;
- calculate a SHA-256 for every source entry;
- validate reviewer, record, and review-round identity;
- enforce the declared substantive fields, status, blind-review flag, timestamp, label, confidence, rationale, and evidence references;
- reject duplicate record IDs or derived review IDs;
- fail rather than overwrite an existing derived-output directory; and
- keep mapped comparison fields outside validated-submission copies.

## Prohibited uses

Derived review IDs must not be used to imply a second reviewer, adjudication, reviewer consensus, Gold Set status, or dataset-label promotion. They are provenance identifiers only.
