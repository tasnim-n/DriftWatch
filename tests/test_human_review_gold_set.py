from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.human_review_adjudication import EXPECTED_DISAGREEMENT_IDS
from research.human_review_gold_set import (
    CANONICAL_QUALIFYING_TIERS,
    GOLD_SET_POLICY_VERSION,
    GOLD_SET_VERSION,
    HumanReviewGoldSetError,
    build_gold_set_artifacts,
    validate_gold_set_inputs,
    write_gold_set_layer,
)
from research.human_review_integration import sha256_file
from research.human_review_quality_promotion import (
    PROMOTED_TIER,
    PROMOTION_IDS,
    PROMOTION_POLICY_VERSION,
    UNCERTAIN_RECORD_ID,
)
from research.phase3h5 import PHASE3H5_GOLD_SET_VERSION, build_gold_set_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _canonical_hash(value: object) -> str:
    import hashlib

    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest().upper()


def _fixture(tmp_path: Path) -> dict:
    promotion_root = tmp_path / "promotion"
    phase5f_root = tmp_path / "phase5f"
    promotion_root.mkdir()
    (phase5f_root / "final_resolutions").mkdir(parents=True)
    source_paths = {}
    source_hashes = {}
    for index, name in enumerate(
        (
            "reviewer01_raw_zip",
            "reviewer02_raw_zip",
            "stage_a_raw_zip",
            "stage_b_released_package",
            "stage_b_raw_return",
        )
    ):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(f"source-{index}".encode())
        source_paths[name] = path
        source_hashes[name] = sha256_file(path)

    phase3h_path = tmp_path / "phase3h.json"
    frozen_rows = []
    promotion_rows = []
    view_rows = []
    readiness_rows = []
    for index, record_id in enumerate(EXPECTED_DISAGREEMENT_IDS):
        uncertain = record_id == UNCERTAIN_RECORD_ID
        semantic = "uncertain" if uncertain else "risky_transition"
        human = "UNCERTAIN" if uncertain else "RISKY_TRANSITION"
        frozen = {
            "record_id": record_id,
            "extension_id": f"github:example/{index}",
            "extension_name": f"Extension {index}",
            "repository": f"https://example.test/{index}",
            "old_version": f"{index}.0",
            "new_version": f"{index}.1",
            "old_sha256": f"{index + 1:064x}",
            "new_sha256": f"{index + 101:064x}",
            "provenance_id": f"source:{record_id}",
            "label": "benign_transition",
            "label_quality": "SINGLE_REVIEWER_PROVISIONAL",
        }
        frozen_rows.append(frozen)
        resolution_path = phase5f_root / "final_resolutions" / f"{record_id}.json"
        _write_json(
            resolution_path,
            {
                "record_id": record_id,
                "final_resolution_status": "ADJUDICATION_COMPLETE",
                "final_adjudicated_label": human,
                "adjudication_confidence": "HIGH" if not uncertain else "MEDIUM",
            },
        )
        source_artifact_hashes = {
            "frozen_row_sha256": _canonical_hash(frozen),
            "final_resolution_sha256": sha256_file(resolution_path),
            "reviewer01_submission_sha256": "1" * 64,
            "reviewer02_submission_sha256": "2" * 64,
            "stage_a_submission_sha256": "A" * 64,
            "stage_b_submission_sha256": "B" * 64,
            "validated_stage_b_submission_sha256": "C" * 64,
        }
        promotion_rows.append(
            {
                "record_id": record_id,
                "final_adjudicated_label": human,
                "final_adjudicated_semantic_label": semantic,
                "phase5f_adjudication_status": "ADJUDICATION_COMPLETE",
                "target_quality_tier": "UNCERTAIN" if uncertain else PROMOTED_TIER,
                "promotion_decision": "NOT_QUALIFYING" if uncertain else "APPROVED",
                "provenance_complete": True,
                "source_artifact_hashes": source_artifact_hashes,
            }
        )
        view_rows.append(
            {
                "record_id": record_id,
                "frozen_row": frozen,
                "frozen_row_sha256": _canonical_hash(frozen),
                "promotion_applied": not uncertain,
                "derived_quality_tier": "UNCERTAIN" if uncertain else PROMOTED_TIER,
            }
        )
        readiness_rows.append(
            {
                "record_id": record_id,
                "gold_set_ready_candidate": not uncertain,
                "non_ready_reasons": (
                    [
                        "NOT_APPROVED_FOR_DEFINITIVE_QUALITY_PROMOTION",
                        "UNCERTAIN_SEMANTIC_LABEL_EXCLUDED",
                    ]
                    if uncertain
                    else []
                ),
            }
        )
    _write_json(phase3h_path, {"records": frozen_rows})
    holdout_path = tmp_path / "holdout.json"
    _write_json(holdout_path, {"records": []})
    disagreement_path = tmp_path / "disagreements.json"
    _write_json(
        disagreement_path,
        {"records": [{"record_id": record_id} for record_id in EXPECTED_DISAGREEMENT_IDS]},
    )
    agreed_rows = [
        {"record_id": f"agreed_{index}", "promotion_performed": False}
        for index in range(9)
    ]
    quality_path = phase5f_root / "quality_tier_eligibility_assessment.json"
    _write_json(
        quality_path,
        {
            "records": [],
            "agreed_nine_read_only_assessment": {
                "records": agreed_rows,
                "record_count": 9,
                "records_changed": 0,
            },
        },
    )
    phase5f_provenance_path = phase5f_root / "provenance_manifest.json"
    _write_json(phase5f_provenance_path, {"records": []})
    decision_id = "QPD1::" + "D" * 64
    _write_json(
        promotion_root / "promotion_manifest.json",
        {
            "decision_id": decision_id,
            "promotion_policy_version": PROMOTION_POLICY_VERSION,
            "records": promotion_rows,
            "gold_set_created": False,
            "frozen_dataset_modified": False,
            "tuning_authorized": False,
        },
    )
    _write_json(promotion_root / "promoted_label_quality_view.json", {"records": view_rows})
    _write_json(
        promotion_root / "gold_set_readiness_assessment.json",
        {"records": readiness_rows, "gold_set_created": False},
    )
    _write_json(
        promotion_root / "human_validation_governance_summary.json",
        {"governed_quality_promotions": 4},
    )
    _write_json(
        promotion_root / "validation_report.json",
        {
            "status": "VALIDATED_AND_RECORDED",
            "source_provenance_complete": True,
            "external_holdout_overlap_count": 0,
            "agreed_nine_promoted_count": 0,
        },
    )
    _write_json(
        promotion_root / "provenance_manifest.json",
        {
            "source_hashes": source_hashes,
            "promotion_policy_document_sha256": sha256_file(
                "HUMAN_REVIEW_QUALITY_PROMOTION_POLICY.md"
            ),
            "canonical_label_quality_policy_sha256": sha256_file(
                "driftbench/label_quality.py"
            ),
            "phase5f_artifact_hashes": {
                "quality": sha256_file(quality_path),
                "provenance": sha256_file(phase5f_provenance_path),
            },
            "disagreement_selection_sha256": sha256_file(disagreement_path),
            "phase3h_provenance_sha256": sha256_file(phase3h_path),
            "holdout_manifest_sha256": sha256_file(holdout_path),
        },
    )
    canonical_policy_path = tmp_path / "canonical_gold.json"
    _write_json(
        canonical_policy_path,
        {
            "gold_set_version": PHASE3H5_GOLD_SET_VERSION,
            "gold_set_policy": "Only EXTERNAL_CONFIRMED, genuine MULTI_REVIEWER_ADJUDICATED, or CONTROLLED_GROUND_TRUTH records qualify.",
        },
    )
    return {
        "promotion_root": promotion_root,
        "phase5f_root": phase5f_root,
        "phase3h_provenance_path": phase3h_path,
        "holdout_manifest_path": holdout_path,
        "disagreement_path": disagreement_path,
        "canonical_gold_manifest_path": canonical_policy_path,
        "source_paths": source_paths,
        "expected_decision_id": decision_id,
    }


def test_canonical_builder_enforces_tier_label_and_provenance_rules():
    records = [
        {
            "pair_id": "included",
            "label": "risky_transition",
            "label_quality_tier": "MULTI_REVIEWER_ADJUDICATED",
            "extension_id": "x",
        },
        {
            "pair_id": "uncertain",
            "label": "uncertain",
            "label_quality_tier": "MULTI_REVIEWER_ADJUDICATED",
            "extension_id": "x",
        },
        {
            "pair_id": "weak-tier",
            "label": "risky_transition",
            "label_quality_tier": "SINGLE_REVIEWER_PROVISIONAL",
            "extension_id": "x",
        },
        {
            "pair_id": "missing-provenance",
            "label": "risky_transition",
            "label_quality_tier": "MULTI_REVIEWER_ADJUDICATED",
            "extension_id": "x",
        },
    ]
    provenance = {
        "included": {"old_sha256": "a", "new_sha256": "b"},
        "uncertain": {"old_sha256": "a", "new_sha256": "b"},
        "weak-tier": {"old_sha256": "a", "new_sha256": "b"},
        "missing-provenance": {"old_sha256": "a"},
    }

    manifest = build_gold_set_manifest(records, provenance, {"records": []})

    assert {row["record_id"] for row in manifest["records"]} == {"included"}
    assert set(CANONICAL_QUALIFYING_TIERS) == {
        "CONTROLLED_GROUND_TRUTH",
        "EXTERNAL_CONFIRMED",
        "MULTI_REVIEWER_ADJUDICATED",
    }


def test_exact_promoted_candidates_are_revalidated_from_policy(tmp_path):
    validation = validate_gold_set_inputs(**_fixture(tmp_path))

    assert {row["pair_id"] for row in validation["candidate_records"]} == set(
        PROMOTION_IDS
    )
    assert validation["canonical_manifest"]["gold_record_count"] == 4
    assert validation["external_holdout_overlap_count"] == 0
    assert validation["canonical_rules"]["canonical_builder_mutates_sources"] is False
    assert validation["canonical_rules"]["governed_wrapper_rejects_duplicates"] is True


def test_uncertain_and_agreement_only_records_are_excluded(tmp_path):
    validation = validate_gold_set_inputs(**_fixture(tmp_path))
    exclusions = {row["record_id"]: row for row in validation["exclusions"]}

    assert UNCERTAIN_RECORD_ID in exclusions
    assert "UNCERTAIN_SEMANTIC_LABEL_EXCLUDED" in exclusions[UNCERTAIN_RECORD_ID][
        "reasons"
    ]
    assert len(
        [
            row
            for row in validation["exclusions"]
            if row["category"] == "AGREEMENT_ONLY_NOT_CANONICALLY_PROMOTED"
        ]
    ) == 9


def test_holdout_overlap_fails_closed(tmp_path):
    paths = _fixture(tmp_path)
    _write_json(
        paths["holdout_manifest_path"],
        {"records": [{"record_id": PROMOTION_IDS[0]}]},
    )
    provenance_path = paths["promotion_root"] / "provenance_manifest.json"
    provenance = json.loads(provenance_path.read_text())
    provenance["holdout_manifest_sha256"] = sha256_file(paths["holdout_manifest_path"])
    _write_json(provenance_path, provenance)

    with pytest.raises(HumanReviewGoldSetError, match="overlaps external holdout"):
        validate_gold_set_inputs(**paths)


def test_broken_promotion_or_final_resolution_linkage_fails_closed(tmp_path):
    paths = _fixture(tmp_path)
    manifest_path = paths["promotion_root"] / "promotion_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["records"][0]["source_artifact_hashes"][
        "final_resolution_sha256"
    ] = "0" * 64
    _write_json(manifest_path, manifest)

    with pytest.raises(HumanReviewGoldSetError, match="final resolution hash differs"):
        validate_gold_set_inputs(**paths)


def test_gold_manifest_is_deterministic_versioned_and_complete(tmp_path):
    validation = validate_gold_set_inputs(**_fixture(tmp_path))
    first = build_gold_set_artifacts(validation)
    second = build_gold_set_artifacts(validation)
    manifest = first["gold_set_manifest"]

    assert first == second
    assert manifest["gold_set_version"] == GOLD_SET_VERSION
    assert manifest["gold_set_policy_version"] == GOLD_SET_POLICY_VERSION
    assert manifest["record_count"] == 4
    assert manifest["manifest_hash"] == second["gold_set_manifest"]["manifest_hash"]
    assert all(row["external_holdout_overlap"] is False for row in manifest["records"])
    assert all(row["source_submission_hashes"] for row in manifest["records"])


def test_usage_restrictions_deny_training_tuning_and_holdout_contamination(tmp_path):
    validation = validate_gold_set_inputs(**_fixture(tmp_path))
    usage = build_gold_set_artifacts(validation)["USAGE_RESTRICTIONS"]

    assert usage["training_authorized"] is False
    assert usage["tuning_authorized"] is False
    assert usage["external_holdout_use_authorized"] is False
    prohibited = set(usage["prohibited_without_separate_governed_authorization"])
    assert {
        "TRAINING",
        "FINE_TUNING",
        "THRESHOLD_SELECTION",
        "RULE_DEVELOPMENT",
        "SCORING_WEIGHT_TUNING",
        "FEATURE_SELECTION",
        "HYPERPARAMETER_TUNING",
        "EXTERNAL_HOLDOUT_CONTAMINATION",
    } <= prohibited


def test_written_gold_layer_hashes_manifest_and_preserves_sources(tmp_path):
    paths = _fixture(tmp_path)
    validation = validate_gold_set_inputs(**paths)
    artifacts = build_gold_set_artifacts(validation)
    protected = [
        paths["phase3h_provenance_path"],
        paths["holdout_manifest_path"],
        paths["disagreement_path"],
        *paths["source_paths"].values(),
    ]
    before = {path: sha256_file(path) for path in protected}
    output = tmp_path / "gold"

    report = write_gold_set_layer(
        output,
        artifacts,
        creation_timestamp="2026-09-22T21:00:00Z",
        git_commit="abc123",
    )

    assert report["record_count"] == 4
    assert report["manifest_sha256"] == sha256_file(output / "gold_set_manifest.json")
    assert (output / "gold_set_manifest.sha256").read_text().startswith(
        report["manifest_sha256"]
    )
    assert len(list(output.glob("*.json"))) == 7
    assert {path: sha256_file(path) for path in protected} == before
    text = "\n".join(path.read_text() for path in output.glob("*.json"))
    assert "adjudication_rationale" not in text
    assert "evidence_references" not in text
    assert '"training_authorized": true' not in text.lower()
