from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftbench.label_quality import LABEL_QUALITY_TIERS
from research.human_review_adjudication import EXPECTED_DISAGREEMENT_IDS
from research.human_review_final_adjudication import FINAL_ADJUDICATION_SCHEMA_VERSION
from research.human_review_integration import sha256_file
from research.human_review_quality_promotion import (
    PROMOTED_TIER,
    PROMOTION_IDS,
    PROMOTION_POLICY_VERSION,
    UNCERTAIN_RECORD_ID,
    UNCERTAIN_TIER,
    HumanReviewQualityPromotionError,
    build_promotion_artifacts,
    validate_phase5f_promotion_inputs,
    write_promotion_layer,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path):
    root = tmp_path / "phase5f"
    final_dir = root / "final_resolutions"
    wrapper_dir = root / "validated_stage_b_submissions"
    final_dir.mkdir(parents=True)
    wrapper_dir.mkdir()
    source_paths = {}
    expected_source_hashes = {}
    source_names = (
        "reviewer01_raw_zip",
        "reviewer02_raw_zip",
        "stage_a_raw_zip",
        "stage_b_released_package",
        "stage_b_raw_return",
    )
    for index, name in enumerate(source_names):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(f"source-{index}".encode())
        source_paths[name] = path
        expected_source_hashes[name] = sha256_file(path)

    phase3h = tmp_path / "phase3h.json"
    frozen_rows = []
    for index, record_id in enumerate(EXPECTED_DISAGREEMENT_IDS):
        frozen_rows.append(
            {
                "record_id": record_id,
                "label": "benign_transition",
                "label_quality": "SINGLE_REVIEWER_PROVISIONAL",
                "review_status": "provisional",
                "provenance_id": f"source:{record_id}",
                "old_sha256": f"{index + 1:064x}",
                "new_sha256": f"{index + 101:064x}",
            }
        )
    _write_json(phase3h, {"records": frozen_rows})
    holdout = tmp_path / "holdout.json"
    _write_json(holdout, {"records": []})
    disagreements = tmp_path / "disagreements.json"
    _write_json(
        disagreements,
        {"records": [{"record_id": record_id} for record_id in EXPECTED_DISAGREEMENT_IDS]},
    )

    quality_rows = []
    provenance_rows = []
    for record_id in EXPECTED_DISAGREEMENT_IDS:
        uncertain = record_id == UNCERTAIN_RECORD_ID
        final_label = "UNCERTAIN" if uncertain else "RISKY_TRANSITION"
        semantic_label = "uncertain" if uncertain else "risky_transition"
        canonical_tier = UNCERTAIN_TIER if uncertain else PROMOTED_TIER
        resolution_path = final_dir / f"{record_id}.json"
        wrapper_path = wrapper_dir / f"{record_id}.json"
        _write_json(
            resolution_path,
            {
                "record_id": record_id,
                "final_resolution_status": "ADJUDICATION_COMPLETE",
                "final_adjudicated_label": final_label,
            },
        )
        _write_json(wrapper_path, {"record_id": record_id, "status": "VALIDATED"})
        quality_rows.append(
            {
                "record_id": record_id,
                "final_human_label": final_label,
                "final_semantic_label": semantic_label,
                "current_frozen_quality_tier": "SINGLE_REVIEWER_PROVISIONAL",
                "current_frozen_review_status": "provisional",
                "canonical_assessed_tier": canonical_tier,
                "eligible_for_multi_reviewer_adjudicated": not uncertain,
                "assessment_status": (
                    "NOT_ELIGIBLE_SEMANTIC_LABEL_UNCERTAIN"
                    if uncertain
                    else "ELIGIBLE_FOR_PROMOTION"
                ),
            }
        )
        provenance_rows.append(
            {
                "record_id": record_id,
                "reviewer01": {"raw_submission_sha256": "1" * 64},
                "reviewer02": {"raw_submission_sha256": "2" * 64},
                "stage_a": {"raw_submission_sha256": "A" * 64},
                "stage_b": {"raw_submission_sha256": "B" * 64},
                "derived": {
                    "final_resolution_sha256": sha256_file(resolution_path),
                    "validated_submission_sha256": sha256_file(wrapper_path),
                },
            }
        )
    agreed_rows = [
        {
            "record_id": f"agreed_{index}",
            "promotion_performed": False,
        }
        for index in range(9)
    ]
    _write_json(
        root / "validation_report.json",
        {
            "status": "VALIDATED",
            "immutable_package_material_match": True,
            "stage_a_linkage_valid": True,
            "evidence_hashes_unchanged": True,
            "reviewer_opinion_source_linkage_valid": True,
            "valid_submission_count": 5,
            "invalid_submission_count": 0,
            "external_holdout_overlap_count": 0,
            "dataset_modified": False,
            "gold_set_created": False,
        },
    )
    _write_json(
        root / "quality_tier_eligibility_assessment.json",
        {
            "canonical_tiers": sorted(LABEL_QUALITY_TIERS),
            "invented_quality_tier": False,
            "promotion_performed": False,
            "records": quality_rows,
            "agreed_nine_read_only_assessment": {
                "record_count": 9,
                "records_changed": 0,
                "new_tier_created": False,
                "records": agreed_rows,
            },
        },
    )
    _write_json(root / "gold_set_eligibility_assessment.json", {"gold_set_created": False})
    _write_json(root / "stage_a_to_stage_b_comparison.json", {"records": []})
    _write_json(root / "human_validation_summary.json", {"gold_set_created": False})
    _write_json(
        root / "provenance_manifest.json",
        {
            "schema_version": FINAL_ADJUDICATION_SCHEMA_VERSION,
            "source_artifacts": {
                **{
                    name: {"sha256": expected_source_hashes[name]}
                    for name in source_names
                },
                "disagreement_selection": {"sha256": sha256_file(disagreements)},
            },
            "records": provenance_rows,
        },
    )
    return {
        "phase5f_root": root,
        "phase3h_provenance_path": phase3h,
        "holdout_manifest_path": holdout,
        "disagreement_path": disagreements,
        "source_paths": source_paths,
        "expected_source_hashes": expected_source_hashes,
    }


def _validate(paths: dict):
    return validate_phase5f_promotion_inputs(**paths)


def test_canonical_tier_and_exact_four_record_promotion_set_are_reverified(tmp_path):
    validation = _validate(_fixture(tmp_path))

    assert validation["canonical_tier_verified"] is True
    assert PROMOTED_TIER in validation["canonical_tiers"]
    assert set(validation["promotion_ids"]) == set(PROMOTION_IDS)
    assert len(validation["promotion_ids"]) == 4
    assert validation["external_holdout_overlap"] == []


def test_missing_stage_a_or_stage_b_provenance_fails_closed(tmp_path):
    paths = _fixture(tmp_path)
    provenance_path = paths["phase5f_root"] / "provenance_manifest.json"
    provenance = json.loads(provenance_path.read_text())
    del provenance["records"][0]["stage_a"]
    _write_json(provenance_path, provenance)

    with pytest.raises(HumanReviewQualityPromotionError, match="stage_a provenance missing"):
        _validate(paths)


def test_uncertain_is_not_promoted_and_agreed_nine_remain_untouched(tmp_path):
    validation = _validate(_fixture(tmp_path))
    artifacts = build_promotion_artifacts(
        validation, decision_timestamp="2026-09-22T20:00:00Z"
    )
    manifest = artifacts["promotion_manifest"]
    uncertain = next(
        row for row in manifest["records"] if row["record_id"] == UNCERTAIN_RECORD_ID
    )

    assert uncertain["final_adjudicated_semantic_label"] == "uncertain"
    assert uncertain["target_quality_tier"] == UNCERTAIN_TIER
    assert uncertain["promotion_decision"] == "NOT_QUALIFYING"
    assert manifest["approved_promotion_count"] == 4
    assert manifest["agreed_nine_promoted_count"] == 0


def test_external_holdout_overlap_blocks_promotion(tmp_path):
    paths = _fixture(tmp_path)
    _write_json(
        paths["holdout_manifest_path"],
        {"records": [{"record_id": PROMOTION_IDS[0]}]},
    )

    with pytest.raises(HumanReviewQualityPromotionError, match="overlap external holdout"):
        _validate(paths)


def test_promotion_manifest_is_deterministic_for_fixed_inputs_and_timestamp(tmp_path):
    validation = _validate(_fixture(tmp_path))
    timestamp = "2026-09-22T20:00:00Z"

    first = build_promotion_artifacts(validation, decision_timestamp=timestamp)
    second = build_promotion_artifacts(validation, decision_timestamp=timestamp)

    assert first == second
    assert first["promotion_manifest"]["promotion_policy_version"] == PROMOTION_POLICY_VERSION
    assert first["promotion_manifest"]["decision_id"].startswith("QPD1::")
    assert first["promoted_label_quality_view"]["frozen_dataset_modified"] is False
    assert all(
        row["lineage_status"] == "DERIVED_DOES_NOT_REWRITE_FROZEN_ROW"
        for row in first["promoted_label_quality_view"]["records"]
    )


def test_gold_readiness_is_four_but_no_gold_set_is_created(tmp_path):
    validation = _validate(_fixture(tmp_path))
    artifacts = build_promotion_artifacts(
        validation, decision_timestamp="2026-09-22T20:00:00Z"
    )
    readiness = artifacts["gold_set_readiness_assessment"]

    assert readiness["ready_candidate_count"] == 4
    assert readiness["non_ready_count"] == 1
    assert readiness["external_holdout_overlap_count"] == 0
    assert readiness["gold_set_created"] is False
    uncertain = next(
        row for row in readiness["records"] if row["record_id"] == UNCERTAIN_RECORD_ID
    )
    assert "UNCERTAIN_SEMANTIC_LABEL_EXCLUDED" in uncertain["non_ready_reasons"]


def test_written_layer_preserves_sources_and_contains_only_governance_outputs(tmp_path):
    paths = _fixture(tmp_path)
    validation = _validate(paths)
    artifacts = build_promotion_artifacts(
        validation, decision_timestamp="2026-09-22T20:00:00Z"
    )
    protected = [
        paths["phase3h_provenance_path"],
        paths["holdout_manifest_path"],
        paths["disagreement_path"],
        *paths["source_paths"].values(),
    ]
    before = {path: sha256_file(path) for path in protected}
    output = tmp_path / "promotion"

    report = write_promotion_layer(output, artifacts)

    assert report["approved_record_count"] == 4
    assert report["gold_set_ready_candidate_count"] == 4
    assert report["gold_set_created"] is False
    assert len(list(output.glob("*.json"))) == 6
    assert not (output / "gold_set.json").exists()
    assert {path: sha256_file(path) for path in protected} == before
    combined = "\n".join(path.read_text() for path in output.glob("*.json"))
    assert "adjudication_rationale" not in combined
    assert "risk_score" not in combined
    assert "threshold" not in combined.lower()
