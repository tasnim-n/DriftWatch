from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from research.human_review_publication import (
    DEFAULT_GOLD_MANIFEST,
    DEFAULT_PUBLIC_ROOT,
    EXPECTED_SOURCE_HASHES,
    HumanReviewPublicationError,
    PRIVACY_CLASSIFICATION,
    _json_bytes,
    _validate_public_privacy,
    verify_publication_layer,
)
from research.human_review_quality_promotion import PROMOTION_IDS, UNCERTAIN_RECORD_ID


def _load(name: str) -> dict:
    return json.loads((DEFAULT_PUBLIC_ROOT / name).read_text(encoding="utf-8"))


def test_public_agreement_claims_and_arithmetic() -> None:
    payload = _load("agreement_summary_public.json")
    assert payload["privacy_classification"] == PRIVACY_CLASSIFICATION
    assert payload["review_set"]["blind_case_count"] == 14
    assert payload["review_set"]["independent_reviewer_count"] == 2
    stats = payload["agreement"]
    assert stats["exact_agreements"] == 9
    assert stats["disagreements"] == 5
    assert stats["exact_agreements"] + stats["disagreements"] == 14
    assert stats["exact_agreement_percent"] == 64.29
    assert stats["observed_agreement"] == pytest.approx(9 / 14)


def test_public_kappa_components_recompute() -> None:
    payload = _load("agreement_summary_public.json")
    stats = payload["agreement"]
    distributions = payload["label_distributions"]
    expected = sum(
        distributions["review_1"].get(label, 0)
        * distributions["review_2"].get(label, 0)
        for label in set(distributions["review_1"]) | set(distributions["review_2"])
    ) / (14 * 14)
    observed = 9 / 14
    assert stats["expected_agreement"] == pytest.approx(expected)
    assert stats["cohens_kappa"] == pytest.approx(
        (observed - expected) / (1 - expected)
    )
    assert stats["cohens_kappa"] == pytest.approx(0.3396226415094341)


def test_public_adjudication_claims_and_exact_record_set() -> None:
    payload = _load("adjudication_summary_public.json")
    workflow = payload["workflow"]
    assert workflow == {
        "cases_entering_adjudication": 5,
        "stage_a_complete": True,
        "stage_b_complete": True,
        "stage_a_to_stage_b_changed_count": 0,
    }
    assert payload["final_label_distribution"] == {
        "BENIGN_TRANSITION": 0,
        "RISKY_TRANSITION": 4,
        "UNCERTAIN": 1,
    }
    by_id = {row["record_id"]: row["final_label"] for row in payload["records"]}
    assert set(by_id) == set(PROMOTION_IDS) | {UNCERTAIN_RECORD_ID}
    assert all(by_id[record_id] == "RISKY_TRANSITION" for record_id in PROMOTION_IDS)
    assert by_id[UNCERTAIN_RECORD_ID] == "UNCERTAIN"


@pytest.mark.parametrize(
    "payload",
    [
        {"nested": [{"human_rationale": "private"}]},
        {"nested": {"resolution_basis": "private"}},
        {"nested": {"evidence_reference": "private"}},
        {"nested": {"reviewer_id": "human_reviewer_01"}},
        {"nested": {"alias_mapping": {"review_1": "Reviewer A"}}},
    ],
)
def test_recursive_privacy_guard_rejects_prohibited_fields(payload: dict) -> None:
    with pytest.raises(HumanReviewPublicationError):
        _validate_public_privacy(payload)


@pytest.mark.parametrize(
    "value",
    [
        "person@example.org",
        "C:\\Users\\person\\private.json",
        "E:\\DriftWatch\\private.json",
        "/home/person/private.json",
        "human_reviewer_01",
        "Reviewer A",
    ],
)
def test_recursive_privacy_guard_rejects_private_values(value: str) -> None:
    with pytest.raises(HumanReviewPublicationError):
        _validate_public_privacy({"value": value})


def test_public_artifact_hashes_are_byte_deterministic() -> None:
    manifest = _load("human_validation_public_manifest.json")
    for name in ("agreement_summary_public.json", "adjudication_summary_public.json"):
        payload = _load(name)
        first = _json_bytes(payload)
        second = _json_bytes(payload)
        assert first == second == (DEFAULT_PUBLIC_ROOT / name).read_bytes()
        assert hashlib.sha256(first).hexdigest().upper() == manifest[
            "public_artifact_sha256"
        ][name]


def test_manifest_preserves_authoritative_hash_provenance() -> None:
    manifest = _load("human_validation_public_manifest.json")
    assert manifest["source_aggregate_sha256"] == EXPECTED_SOURCE_HASHES
    assert manifest["privacy_classification"] == PRIVACY_CLASSIFICATION
    assert set(manifest["public_artifact_sha256"]) == {
        "agreement_summary_public.json",
        "adjudication_summary_public.json",
    }


def test_gold_set_linkage_is_valid() -> None:
    manifest = _load("human_validation_public_manifest.json")
    gold = json.loads(DEFAULT_GOLD_MANIFEST.read_text(encoding="utf-8"))
    linkage = manifest["gold_set_linkage"]
    assert linkage["record_count"] == gold["record_count"] == 4
    assert linkage["record_ids"] == sorted(PROMOTION_IDS)
    assert linkage["record_ids"] == sorted(row["record_id"] for row in gold["records"])
    assert UNCERTAIN_RECORD_ID not in linkage["record_ids"]


def test_clean_clone_verification_does_not_require_private_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public_root = tmp_path / DEFAULT_PUBLIC_ROOT
    gold_path = tmp_path / DEFAULT_GOLD_MANIFEST
    gold_path.parent.mkdir(parents=True)
    shutil.copytree(DEFAULT_PUBLIC_ROOT, public_root)
    shutil.copy2(DEFAULT_GOLD_MANIFEST, gold_path)
    monkeypatch.chdir(tmp_path)

    result = verify_publication_layer()
    assert result["status"] == "VERIFIED"
    assert result["private_sources_required"] is False


def test_public_evidence_tree_contains_only_the_allowlisted_files() -> None:
    assert {path.name for path in DEFAULT_PUBLIC_ROOT.iterdir() if path.is_file()} == {
        "agreement_summary_public.json",
        "adjudication_summary_public.json",
        "human_validation_public_manifest.json",
    }
    for path in DEFAULT_PUBLIC_ROOT.iterdir():
        if path.is_file():
            _validate_public_privacy(json.loads(path.read_text(encoding="utf-8")))


def test_paper_evidence_map_uses_public_human_validation_paths() -> None:
    text = Path("PAPER_EVIDENCE_MAP.md").read_text(encoding="utf-8")
    for name in (
        "agreement_summary_public.json",
        "adjudication_summary_public.json",
        "human_validation_public_manifest.json",
    ):
        assert f"artifacts/human_review/public_validation/{name}" in text
    assert "stage_a_to_stage_b_comparison.json" not in text
