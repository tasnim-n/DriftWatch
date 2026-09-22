from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from driftbench.label_quality import LABEL_QUALITY_TIERS
from research.human_review_adjudication import (
    DEFAULT_ADJUDICATOR_ID,
    EXPECTED_DISAGREEMENT_IDS,
    STAGE_A,
    STAGE_B,
    HumanReviewAdjudicationError,
    _stage_b_submission,
    derive_adjudication_review_id,
)
from research.human_review_final_adjudication import (
    EXPECTED_STAGE_B_JUDGMENTS,
    STAGE_B_TIMESTAMP_PROVENANCE,
    assess_gold_set_eligibility,
    assess_quality_tier_eligibility,
    build_stage_a_to_stage_b_comparison,
    load_and_validate_stage_b_return,
    validate_reviewer_opinion_source_linkage,
    write_final_adjudication_layer,
)
from research.human_review_integration import (
    HumanReviewIntegrationError,
    sha256_bytes,
    sha256_file,
)


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _stage_a_bundle() -> dict:
    records = []
    for index, record_id in enumerate(EXPECTED_DISAGREEMENT_IDS):
        label, confidence = EXPECTED_STAGE_B_JUDGMENTS[record_id]
        packet = {"record_id": record_id, "signal": {"value": index}}
        submission = {
            "review_id": derive_adjudication_review_id(
                DEFAULT_ADJUDICATOR_ID, record_id, STAGE_A
            ),
            "adjudicator_id": DEFAULT_ADJUDICATOR_ID,
            "record_id": record_id,
            "review_round": STAGE_A,
            "adjudicator_initial_label": label,
            "adjudicator_initial_confidence": confidence,
            "adjudicator_initial_rationale": f"Stage A rationale {index}",
            "evidence_references": ["signal.value=observed"],
            "blind_review": True,
            "review_status": "SUBMITTED",
            "review_timestamp": "2026-09-22T12:00:00Z",
            "review_timestamp_provenance": "actual file-finalization time",
        }
        submission_raw = _json_bytes(submission)
        records.append(
            {
                "record_id": record_id,
                "review_id": submission["review_id"],
                "entry_name": f"submissions/{record_id}.json",
                "entry_sha256": sha256_bytes(submission_raw),
                "submission": submission,
                "packet_sha256": sha256_bytes(_json_bytes(packet)),
                "packet": packet,
            }
        )
    return {
        "raw_source_filename": "stage_a.zip",
        "raw_source_sha256": "A" * 64,
        "records": records,
    }


def _stage_b_archives(tmp_path: Path, *, mutate_case: bool = False):
    stage_a = _stage_a_bundle()
    released = tmp_path / "released.zip"
    returned = tmp_path / "returned.zip"
    released_entries = {
        "PACKAGE_MANIFEST.md": b"manifest\n",
        "REVIEW_INSTRUCTIONS.md": b"instructions\n",
    }
    returned_entries = dict(released_entries)
    for index, record in enumerate(stage_a["records"]):
        record_id = record["record_id"]
        case = {
            "schema_version": "test",
            "record_id": record_id,
            "sections": {
                "ORIGINAL_BLIND_EVIDENCE": record["packet"],
                "MY_STAGE_A_ASSESSMENT": {
                    "source_review_id": record["review_id"],
                    "source_submission_sha256": record["entry_sha256"],
                    "assessment": record["submission"],
                },
                "REVIEWER_A_OPINION": {
                    "label": "RISKY_TRANSITION",
                    "confidence": "MEDIUM",
                    "rationale": f"Reviewer A rationale {index}",
                    "evidence_references": ["signal.value=observed"],
                },
                "REVIEWER_B_OPINION": {
                    "label": "UNCERTAIN",
                    "confidence": "LOW",
                    "rationale": f"Reviewer B rationale {index}",
                    "evidence_references": ["signal.value=observed"],
                },
            },
        }
        case_raw = _json_bytes(case)
        released_entries[f"cases/{record_id}.json"] = case_raw
        returned_entries[f"cases/{record_id}.json"] = case_raw
        blank = _stage_b_submission(
            record_id,
            DEFAULT_ADJUDICATOR_ID,
            stage_a_submission_sha256=record["entry_sha256"],
        )
        completed = dict(blank)
        label, confidence = EXPECTED_STAGE_B_JUDGMENTS[record_id]
        completed.update(
            {
                "final_adjudicated_label": label,
                "adjudication_confidence": confidence,
                "adjudication_rationale": f"Final rationale {index}",
                "adjudication_evidence_references": ["signal.value=observed"],
                "initial_label_changed": False,
                "change_reason": "",
                "resolution_basis": f"Resolution basis {index}",
                "review_status": "SUBMITTED",
                "review_timestamp": "2026-09-22T18:00:00+06:00",
            }
        )
        released_entries[f"submissions/{record_id}.json"] = _json_bytes(blank)
        returned_entries[f"submissions/{record_id}.json"] = _json_bytes(completed)
    if mutate_case:
        first = f"cases/{EXPECTED_DISAGREEMENT_IDS[0]}.json"
        returned_entries[first] += b" "
    for path, entries in ((released, released_entries), (returned, returned_entries)):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in entries.items():
                archive.writestr(name, raw)
    return stage_a, released, returned


def _validate_fixture(tmp_path: Path):
    stage_a, released, returned = _stage_b_archives(tmp_path)
    bundle = load_and_validate_stage_b_return(
        returned,
        released_package_path=released,
        stage_a_bundle=stage_a,
        expected_raw_sha256=sha256_file(returned),
        expected_package_sha256=sha256_file(released),
    )
    return stage_a, bundle, released, returned


def _reviewer_source_fixture(tmp_path: Path):
    reviewer01 = {"raw_zip_path": "reviewer01.zip", "raw_source_sha256": "1" * 64, "records": []}
    reviewer02 = {"raw_zip_path": "reviewer02.zip", "raw_source_sha256": "2" * 64, "records": []}
    mapping_records = []
    for index, record_id in enumerate(EXPECTED_DISAGREEMENT_IDS):
        aliases = {}
        for alias, bundle, reviewer_id, label, confidence in (
            ("Reviewer A", reviewer01, "human_reviewer_01", "RISKY_TRANSITION", "MEDIUM"),
            ("Reviewer B", reviewer02, "human_reviewer_02", "UNCERTAIN", "LOW"),
        ):
            derived_review_id = f"HRV1::{reviewer_id}::{record_id}::INITIAL_BLIND"
            entry_name = f"submissions/{record_id}.json"
            entry_sha256 = f"{index + (1 if alias == 'Reviewer A' else 20):064x}"
            bundle["records"].append(
                {
                    "record_id": record_id,
                    "derived_review_id": derived_review_id,
                    "raw_submission_entry_name": entry_name,
                    "raw_submission_sha256": entry_sha256,
                    "raw_packet_sha256": "A" * 64,
                    "packet_source_sha256": "A" * 64,
                    "submission": {
                        "independent_label": label,
                        "confidence": confidence,
                        "rationale": f"{alias} rationale {index}",
                        "evidence_references": ["signal.value=observed"],
                    },
                }
            )
            aliases[alias] = {
                "reviewer_id": reviewer_id,
                "raw_submission_entry_name": entry_name,
                "raw_submission_sha256": entry_sha256,
                "derived_review_id": derived_review_id,
            }
        mapping_records.append({"record_id": record_id, "aliases": aliases})
    mapping_path = tmp_path / "aliases.json"
    mapping_path.write_text(json.dumps({"records": mapping_records}), encoding="utf-8")
    return reviewer01, reviewer02, mapping_path


def _policy_fixture(tmp_path: Path, comparison: dict):
    agreed_ids = [f"agreed_{index:02d}" for index in range(9)]
    all_ids = list(EXPECTED_DISAGREEMENT_IDS) + agreed_ids
    phase3h = tmp_path / "phase3h.json"
    phase3h.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "record_id": record_id,
                        "label": "benign_transition",
                        "label_quality": "SINGLE_REVIEWER_PROVISIONAL",
                        "review_status": "provisional",
                        "old_sha256": f"{index:064x}",
                        "new_sha256": f"{index + 100:064x}",
                        "provenance_id": f"source:{record_id}",
                    }
                    for index, record_id in enumerate(all_ids)
                ]
            }
        ),
        encoding="utf-8",
    )
    agreement = tmp_path / "comparison.json"
    agreement.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "record_id": record_id,
                        "exact_match": record_id in agreed_ids,
                        "reviewer01_original_label": "UNCERTAIN",
                    }
                    for record_id in all_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    quality = assess_quality_tier_eligibility(
        comparison,
        phase3h_provenance_path=phase3h,
        agreement_comparison_path=agreement,
    )
    gold_policy = tmp_path / "gold.json"
    gold_policy.write_text(
        json.dumps(
            {
                "gold_set_version": "phase3h5-gold-set-methodology-v1",
                "gold_set_policy": "Only qualifying canonical tiers with complete provenance.",
            }
        ),
        encoding="utf-8",
    )
    holdout = tmp_path / "holdout.json"
    holdout.write_text(json.dumps({"records": []}), encoding="utf-8")
    return quality, phase3h, agreement, gold_policy, holdout


def test_stage_b_raw_hash_and_exact_released_package_linkage(tmp_path):
    stage_a, bundle, released, returned = _validate_fixture(tmp_path)

    assert bundle["submission_count"] == 5
    assert bundle["unique_review_id_count"] == 5
    assert bundle["immutable_entries_match"] is True
    assert bundle["stage_a_linkage_valid"] is True
    assert bundle["evidence_hashes_unchanged"] is True
    assert {row["timestamp_provenance"] for row in bundle["records"]} == {
        STAGE_B_TIMESTAMP_PROVENANCE
    }
    with pytest.raises(HumanReviewIntegrationError, match="SHA-256 mismatch"):
        load_and_validate_stage_b_return(
            returned,
            released_package_path=released,
            stage_a_bundle=stage_a,
            expected_raw_sha256="0" * 64,
            expected_package_sha256=sha256_file(released),
        )


def test_stage_b_rejects_mutated_case_and_missing_or_extra_entries(tmp_path):
    stage_a, released, returned = _stage_b_archives(tmp_path, mutate_case=True)
    with pytest.raises(HumanReviewAdjudicationError, match="immutable Stage B"):
        load_and_validate_stage_b_return(
            returned,
            released_package_path=released,
            stage_a_bundle=stage_a,
            expected_raw_sha256=sha256_file(returned),
            expected_package_sha256=sha256_file(released),
        )

    clean = tmp_path / "clean"
    clean.mkdir()
    stage_a, released, returned = _stage_b_archives(clean)
    missing = tmp_path / "missing.zip"
    with zipfile.ZipFile(returned) as source, zipfile.ZipFile(missing, "w") as target:
        for name in source.namelist()[1:]:
            target.writestr(name, source.read(name))
    with pytest.raises(HumanReviewAdjudicationError, match="exact governed package set"):
        load_and_validate_stage_b_return(
            missing,
            released_package_path=released,
            stage_a_bundle=stage_a,
            expected_raw_sha256=sha256_file(missing),
            expected_package_sha256=sha256_file(released),
        )


def test_stage_a_to_stage_b_comparison_is_five_retained_zero_changed(tmp_path):
    stage_a, bundle, _, _ = _validate_fixture(tmp_path)
    comparison = build_stage_a_to_stage_b_comparison(stage_a, bundle)

    assert comparison["record_count"] == 5
    assert comparison["retained_stage_a_label_count"] == 5
    assert comparison["changed_stage_a_label_count"] == 0
    assert all(not row["changed"] for row in comparison["records"])
    assert all(row["stage_a_source_sha256"] for row in comparison["records"])
    assert all(row["stage_b_source_sha256"] for row in comparison["records"])


def test_reviewer_opinions_are_verbatim_and_hash_linked_to_raw_sources(tmp_path):
    _, bundle, _, _ = _validate_fixture(tmp_path)
    reviewer01, reviewer02, mapping = _reviewer_source_fixture(tmp_path)

    result = validate_reviewer_opinion_source_linkage(
        bundle,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
        alias_mapping_path=mapping,
    )

    assert result["status"] == "VALID"
    assert result["opinion_count"] == 10
    assert result["opinion_material_verbatim"] is True
    assert result["source_hash_linkage_valid"] is True


def test_quality_assessment_uses_only_canonical_tiers_and_preserves_uncertain(tmp_path):
    stage_a, bundle, _, _ = _validate_fixture(tmp_path)
    comparison = build_stage_a_to_stage_b_comparison(stage_a, bundle)
    quality, *_ = _policy_fixture(tmp_path, comparison)

    assert set(quality["canonical_tiers"]) == LABEL_QUALITY_TIERS
    assert quality["invented_quality_tier"] is False
    assert quality["eligible_for_promotion_count"] == 4
    assert quality["promotion_performed"] is False
    uncertain = next(
        row for row in quality["records"] if row["final_human_label"] == "UNCERTAIN"
    )
    assert uncertain["canonical_assessed_tier"] == "UNCERTAIN"
    assert uncertain["eligible_for_multi_reviewer_adjudicated"] is False
    agreed = quality["agreed_nine_read_only_assessment"]
    assert agreed["record_count"] == 9
    assert agreed["records_changed"] == 0
    assert {row["assessment"] for row in agreed["records"]} == {
        "FUTURE_GOVERNED_POLICY_CHANGE_OR_ADDITIONAL_ADJUDICATION_REQUIRED"
    }


def test_gold_assessment_is_read_only_excludes_uncertain_and_holdout(tmp_path):
    stage_a, bundle, _, _ = _validate_fixture(tmp_path)
    comparison = build_stage_a_to_stage_b_comparison(stage_a, bundle)
    quality, phase3h, _, gold_policy, holdout = _policy_fixture(tmp_path, comparison)
    assessment = assess_gold_set_eligibility(
        quality,
        phase3h_provenance_path=phase3h,
        holdout_manifest_path=holdout,
        gold_manifest_path=gold_policy,
    )

    assert assessment["eligible_candidate_count"] == 4
    assert assessment["noneligible_count"] == 1
    assert assessment["uncertain_exclusion_count"] == 1
    assert assessment["external_holdout_overlap_count"] == 0
    assert assessment["gold_set_created"] is False
    assert all(row["currently_gold_eligible"] is False for row in assessment["records"])

    holdout.write_text(
        json.dumps({"records": [{"record_id": EXPECTED_DISAGREEMENT_IDS[0]}]}),
        encoding="utf-8",
    )
    protected = assess_gold_set_eligibility(
        quality,
        phase3h_provenance_path=phase3h,
        holdout_manifest_path=holdout,
        gold_manifest_path=gold_policy,
    )
    assert protected["eligible_candidate_count"] == 3
    assert protected["external_holdout_overlap_count"] == 1
    row = next(
        row for row in protected["records"] if row["record_id"] == EXPECTED_DISAGREEMENT_IDS[0]
    )
    assert "EXTERNAL_HOLDOUT_FORBIDDEN" in row["exclusion_reasons"]


def test_final_layer_is_derived_provenanced_and_does_not_modify_sources(tmp_path):
    stage_a, bundle, released, returned = _validate_fixture(tmp_path)
    comparison = build_stage_a_to_stage_b_comparison(stage_a, bundle)
    quality, phase3h, agreement, gold_policy, holdout = _policy_fixture(
        tmp_path, comparison
    )
    gold = assess_gold_set_eligibility(
        quality,
        phase3h_provenance_path=phase3h,
        holdout_manifest_path=holdout,
        gold_manifest_path=gold_policy,
    )
    agreement_root = tmp_path / "agreement"
    agreement_root.mkdir()
    for name in ("agreement_summary.json", "comparison_table.json", "disagreements.json"):
        source = agreement if name == "comparison_table.json" else None
        (agreement_root / name).write_text(
            source.read_text(encoding="utf-8") if source else "{}\n", encoding="utf-8"
        )
    reviewer01, reviewer02, mapping = _reviewer_source_fixture(tmp_path)
    for index, record_id in enumerate(EXPECTED_DISAGREEMENT_IDS):
        reviewer01["records"][index]["raw_packet_sha256"] = stage_a["records"][index][
            "packet_sha256"
        ]
        reviewer02["records"][index]["packet_source_sha256"] = stage_a["records"][index][
            "packet_sha256"
        ]
    linkage = validate_reviewer_opinion_source_linkage(
        bundle,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
        alias_mapping_path=mapping,
    )
    bundle["reviewer_opinion_source_linkage_valid"] = linkage["status"] == "VALID"
    before = {path: sha256_file(path) for path in (released, returned, phase3h, holdout)}
    output = tmp_path / "final"
    report = write_final_adjudication_layer(
        output_root=output,
        stage_a_bundle=stage_a,
        stage_b_bundle=bundle,
        comparison=comparison,
        quality_assessment=quality,
        gold_assessment=gold,
        reviewer01_bundle=reviewer01,
        reviewer02_bundle=reviewer02,
        agreement_root=agreement_root,
        phase3h_provenance_path=phase3h,
        holdout_manifest_path=holdout,
        gold_manifest_path=gold_policy,
    )

    assert report["status"] == "VALIDATED"
    assert len(list((output / "validated_stage_b_submissions").glob("*.json"))) == 5
    assert len(list((output / "final_resolutions").glob("*.json"))) == 5
    provenance = json.loads((output / "provenance_manifest.json").read_text())
    assert provenance["record_count"] == 5
    assert provenance["gold_set_created"] is False
    assert provenance["dataset_modified"] is False
    assert provenance["public_safe_no_human_rationale_text"] is True
    assert {path: sha256_file(path) for path in before} == before
