import csv
import json
from pathlib import Path


PHASE3G = Path("artifacts/experiments/phase3g")
PHASE3G_DRIFTBENCH = Path("artifacts/driftbench/phase3g")
PHASE3G_FEATURES = Path("artifacts/driftbench/phase3g_features")
PHASE3F = Path("artifacts/experiments/phase3f")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_phase3g_dataset_versioning_and_phase3f_immutability_reference():
    snapshot = read_json(PHASE3G / "dataset_snapshot.json")
    phase3f_snapshot = read_json(PHASE3F / "dataset_snapshot.json")
    baseline = snapshot["phase3f_frozen_baseline"]

    assert snapshot["dataset_version"] == "driftbench-real-maturation-phase3g-v1"
    assert snapshot["previous_dataset_version"] == "driftbench-real-replication-phase3f-v1"
    assert baseline["status"] == "FROZEN_PHASE3F_BASELINE"
    assert baseline["dataset_version"] == phase3f_snapshot["dataset_version"]
    assert baseline["preservation_policy"].endswith("writes only phase3g outputs.")


def test_phase3g_corpus_counts_and_labels_are_actual():
    snapshot = read_json(PHASE3G / "dataset_snapshot.json")

    assert snapshot["record_count"] == 58
    assert snapshot["real_record_count"] == 58
    assert snapshot["controlled_record_count"] == 0
    assert snapshot["new_phase3g_record_count"] == 12
    assert snapshot["unique_extension_count"] == 17
    assert snapshot["label_distribution"] == {
        "benign_transition": 53,
        "risky_transition": 3,
        "uncertain": 2,
    }
    assert snapshot["label_quality_distribution"] == {
        "SINGLE_REVIEWER_PROVISIONAL": 56,
        "UNCERTAIN": 2,
    }
    assert snapshot["training_eligible_count"] == 56


def test_phase3g_new_records_have_provenance_and_exclusions_are_honest():
    provenance = read_json(PHASE3G_DRIFTBENCH / "provenance_manifest.json")
    excluded = read_json(PHASE3G_DRIFTBENCH / "excluded_candidate_assets.json")
    new_records = [record for record in provenance["records"] if record["is_phase3g_record"]]

    assert provenance["provenance_complete_count"] == 58
    assert provenance["timestamp_complete_count"] == 58
    assert len(new_records) == 12
    assert {record["extension_id"] for record in new_records} == {
        "github:automaapp/automa",
        "github:libredirect/browser_extension",
        "github:web-scrobbler/web-scrobbler",
    }
    assert "github:iorate/ublacklist" in excluded["excluded"]
    assert "zip-bomb compression-ratio protection" in excluded["excluded"]["github:iorate/ublacklist"]["reason"]


def test_phase3g_duplicate_and_leakage_audits_pass():
    duplicate = read_json(PHASE3G_DRIFTBENCH / "duplicate_report.json")
    leakage = read_json(PHASE3G_DRIFTBENCH / "leakage_report.json")
    feature_leakage = read_json(PHASE3G / "feature_leakage_audit.json")

    assert duplicate["passed"] is True
    assert duplicate["duplicate_record_ids"] == []
    assert duplicate["duplicate_pairs"] == []
    assert duplicate["duplicate_package_hashes"] == {}
    assert leakage["passed"] is True
    assert leakage["violations"] == []
    assert feature_leakage["passed"] is True


def test_phase3g_uncertain_records_remain_training_ineligible_and_reviewed():
    label_quality = read_json(PHASE3G_DRIFTBENCH / "label_quality_report.json")
    packets = read_json(PHASE3G_DRIFTBENCH / "uncertain_review_packets.json")
    manifest = read_json(PHASE3G_DRIFTBENCH / "dataset_manifest.json")
    uncertain_records = [record for record in manifest["records"] if record["label"] == "uncertain"]

    assert label_quality["uncertain_count"] == 2
    assert label_quality["uncertain_training_eligible_count"] == 0
    assert {record["pair_id"] for record in uncertain_records} == {
        "save-sora_2_0_355_to_3_0_0",
        "save-sora_3_0_0_to_3_0_10",
    }
    assert all(record["eligible_for_supervised_training"] is False for record in uncertain_records)
    assert packets["packet_count"] == 2
    assert all(item["status"] == "remains_uncertain" for item in packets["records"])


def test_phase3g_reviewer_workflow_and_inter_rater_guard():
    schema = read_json(PHASE3G_DRIFTBENCH / "reviewer_schema.json")
    queue = read_json(PHASE3G_DRIFTBENCH / "second_review_queue.json")
    inter_rater = read_json(PHASE3G_DRIFTBENCH / "inter_rater_agreement.json")

    assert "reviewer_id" in schema["fields"]
    assert "adjudicated_label" in schema["fields"]
    assert queue["status"] == "created_no_second_reviewer_fabricated"
    assert queue["records"][0]["label"] == "risky_transition"
    assert inter_rater["status"] == "INTER_RATER_AGREEMENT_NOT_AVAILABLE"
    assert inter_rater["double_reviewed_record_count"] == 0
    assert inter_rater["cohens_kappa"] is None


def test_phase3g_split_quality_and_readiness_decision_are_honest():
    snapshot = read_json(PHASE3G / "dataset_snapshot.json")
    readiness = read_json(PHASE3G_DRIFTBENCH / "readiness.json")
    split_quality = read_json(PHASE3G_DRIFTBENCH / "split_quality_report.json")

    assert snapshot["split_distribution"] == {
        "train": 32,
        "validation": 16,
        "test": 10,
    }
    assert readiness["phase3g_complete"] is True
    assert readiness["recommended_next_phase"] == "DATASET STILL TOO WEAK - CONTINUE EXPANSION"
    assert "single-reviewer provisional labels still dominate" in readiness["warnings"]
    assert split_quality["leakage_passed"] is True
    assert split_quality["unique_extensions_per_split"] == {
        "test": 4,
        "train": 8,
        "validation": 5,
    }


def test_phase3g_feature_regeneration_schema_and_no_ml_deployment():
    feature_summary = read_json(PHASE3G_FEATURES / "dataset_summary.json")
    extraction = read_json(PHASE3G_FEATURES / "extraction_manifest.json")
    experiment = read_json(PHASE3G / "experiment_manifest.json")
    phase3f_schema = read_json(Path("artifacts/driftbench/phase3f_features/feature_schema.json"))
    phase3g_schema = read_json(PHASE3G_FEATURES / "feature_schema.json")

    assert feature_summary["record_count"] == 58
    assert feature_summary["phase3f_baseline_rows_reused"] == 46
    assert feature_summary["phase3g_new_rows_extracted"] == 12
    assert extraction["model_training_performed"] is False
    assert extraction["production_ml_integration"] is False
    assert experiment["model_training_performed"] is False
    assert experiment["production_ml_integration"] is False
    assert [feature["name"] for feature in phase3g_schema["features"]] == [
        feature["name"] for feature in phase3f_schema["features"]
    ]


def test_phase3g_dataset_comparison_artifact():
    rows = {row["metric"]: row for row in read_csv(PHASE3G / "phase3f_vs_phase3g_dataset.csv")}

    assert rows["total_real_records"]["phase3f"] == "46"
    assert rows["total_real_records"]["phase3g"] == "58"
    assert rows["unique_extensions"]["phase3f"] == "14"
    assert rows["unique_extensions"]["phase3g"] == "17"
    assert rows["provenance_completeness"]["phase3g"] == "58/58"
