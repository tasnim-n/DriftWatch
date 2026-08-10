# DriftBench Phase 3A Specification

DriftBench is the dataset layer for DriftWatch version-pair research. Phase 3A defines metadata, labels, provenance, validation, controlled mutations, and leakage-safe split generation. Phase 3B adds deterministic feature extraction and reproducible feature artifacts. These phases do not train machine-learning models and do not report detection metrics.

## Dataset Unit
Each record represents one transition from `V(t-1)` to `V(t)` for the same browser extension.

Required fields:
- `pair_id`
- `extension_id`
- `extension_name`
- `old_version`
- `new_version`
- `old_archive_path`
- `new_archive_path`
- `old_timestamp`
- `new_timestamp`
- `source`
- `license`
- `label`
- `label_rationale`
- `provenance`

Optional but supported fields:
- `controlled_mutation_type`
- `label_confidence`
- `feature_vector`
- `drift_vector`
- `split`
- `notes`

## Label Ontology
Labels are operational definitions, not claims of criminal intent.

- `benign_transition`: no meaningful new security or privacy-sensitive capability.
- `risky_transition`: introduces capability expansion requiring analyst review.
- `controlled_malicious_transition`: synthetic laboratory transition modeling malicious patterns without deployable malware.
- `needs_review`: insufficient or conflicting evidence; excluded from supervised training until reviewed.

`controlled_malicious_transition` and `needs_review` are not allowed for supervised training by default.

## Provenance
Every record must preserve:
- source type and URI
- collection timestamp
- license
- collector
- archive SHA-256 hashes when archives are available
- generation method for synthetic or controlled records
- notes for uncertainty or caveats

## Validator Rules
The Phase 3A validator checks:
- required fields
- valid labels and label confidence values
- timestamp format and old/new ordering
- archive path existence
- optional SHA-256 hash matches
- duplicate `pair_id`
- split leakage by `extension_id`
- controlled mutation metadata for controlled malicious records

The validator never executes extension JavaScript.

## Controlled Mutation Framework
The controlled mutation framework creates harmless synthetic extension updates from existing local samples. Supported mutation types:
- `permission_expansion`
- `host_expansion`
- `sensitive_api_introduction`
- `network_endpoint_introduction`
- `obfuscation_introduction`
- `background_worker_introduction`
- `remote_configuration_pattern`
- `source_to_sink_heuristic`
- `gradual_capability_expansion`

Generated code uses controlled sample text and localhost/test endpoints. It must not collect real credentials, execute payloads, or contact live infrastructure.

## Leakage-Safe Splits
Phase 3A supports:
- deterministic group-aware random splits by `extension_id`
- chronological group-aware splits ordered by each extension group's latest update timestamp

The same `extension_id` must not appear in multiple experiment splits. Controlled holdout records can be separated from real-world experimental splits.

## Phase 3A Verification
Implemented modules:
- `driftbench/labels.py`
- `driftbench/schema.py`
- `driftbench/provenance.py`
- `driftbench/validator.py`
- `driftbench/mutations.py`
- `driftbench/splits.py`

Tests:
- `tests/test_driftbench_phase3a.py`

Phase 3A intentionally does not include ML training, baseline metrics, dataset-size claims, or performance claims.

## Phase 3B Feature Artifacts
Feature schema version: `1.0`

Representations:
- `permission_only`
- `manifest_permission`
- `latest_version_static`
- `simple_differential`
- `full_driftwatch`

Artifact files:
- `feature_schema.json`
- `<representation>.csv`
- `<representation>.jsonl`
- `dataset_summary.json`
- `extraction_manifest.json`

Feature rows preserve metadata fields such as `record_id`, `extension_id`, versions, label, provenance ID, and split. Labels and splits are metadata only and must not be used as model input features.

Raw feature values are not normalized during extraction. Scaling belongs in future ML pipelines and must be fit only on training data.
