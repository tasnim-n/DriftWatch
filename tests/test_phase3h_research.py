import csv
import json
from pathlib import Path


PHASE3H = Path("artifacts/experiments/phase3h")
PHASE3H_DRIFTBENCH = Path("artifacts/driftbench/phase3h")
PHASE3H_FEATURES = Path("artifacts/driftbench/phase3h_features")
PHASE3G = Path("artifacts/experiments/phase3g")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_phase3h_versioning_and_phase3g_frozen_reference():
    snapshot = read_json(PHASE3H / "dataset_snapshot.json")
    phase3g_snapshot = read_json(PHASE3G / "dataset_snapshot.json")

    assert snapshot["dataset_version"] == "driftbench-real-adjudication-holdout-phase3h-v1"
    assert snapshot["previous_dataset_version"] == "driftbench-real-maturation-phase3g-v1"
    assert snapshot["phase3g_frozen_baseline"]["status"] == "FROZEN_PHASE3G_BASELINE"
    assert snapshot["phase3g_frozen_baseline"]["dataset_version"] == phase3g_snapshot["dataset_version"]
    assert snapshot["provenance_schema_version"] == "phase3h-provenance-v1"


def test_phase3h_corpus_counts_labels_and_quality_are_actual():
    snapshot = read_json(PHASE3H / "dataset_snapshot.json")

    assert snapshot["record_count"] == 76
    assert snapshot["real_record_count"] == 76
    assert snapshot["controlled_record_count"] == 0
    assert snapshot["new_phase3h_record_count"] == 18
    assert snapshot["unique_extension_count"] == 21
    assert snapshot["label_distribution"] == {
        "benign_transition": 71,
        "risky_transition": 3,
        "uncertain": 2,
    }
    assert snapshot["label_quality_distribution"] == {
        "SINGLE_REVIEWER_PROVISIONAL": 74,
        "UNCERTAIN": 2,
    }
    assert snapshot["training_eligible_count"] == 74


def test_phase3h_provenance_duplicate_and_leakage_audits_pass():
    provenance = read_json(PHASE3H_DRIFTBENCH / "provenance_manifest.json")
    duplicate = read_json(PHASE3H_DRIFTBENCH / "duplicate_report.json")
    leakage = read_json(PHASE3H_DRIFTBENCH / "leakage_report.json")
    feature_leakage = read_json(PHASE3H / "feature_leakage_audit.json")

    assert provenance["provenance_complete_count"] == 76
    assert provenance["timestamp_complete_count"] == 76
    assert duplicate["passed"] is True
    assert duplicate["duplicate_record_ids"] == []
    assert duplicate["duplicate_pairs"] == []
    assert duplicate["duplicate_package_hashes"] == {}
    assert leakage["passed"] is True
    assert feature_leakage["passed"] is True


def test_phase3h_new_records_and_source_diversity():
    provenance = read_json(PHASE3H_DRIFTBENCH / "provenance_manifest.json")
    new_records = [record for record in provenance["records"] if record["is_phase3h_record"]]

    assert len(new_records) == 18
    assert {record["extension_id"] for record in new_records} == {
        "github:bitwarden/clients-browser",
        "github:clearurls/addon",
        "github:firefoxbar/headereditor",
        "github:ruffle-rs/ruffle",
    }
    assert {record["source_family"] for record in new_records} == {"public_github_release_assets"}


def test_phase3h_external_holdout_is_locked_and_excluded_from_features():
    holdout = read_json(PHASE3H_DRIFTBENCH / "external_holdout_manifest.json")
    feature_summary = read_json(PHASE3H_FEATURES / "dataset_summary.json")
    feature_rows = read_csv(PHASE3H_FEATURES / "full_driftwatch.csv")
    holdout_ids = {record["record_id"] for record in holdout["records"]}

    assert holdout["holdout_name"] == "EXTERNAL_REPLICATION_HOLDOUT"
    assert holdout["record_count"] == 10
    assert holdout["unique_extension_count"] == 2
    assert holdout["training_use_allowed"] is False
    assert holdout["tuning_use_allowed"] is False
    assert feature_summary["record_count"] == 66
    assert holdout_ids.isdisjoint({row["record_id"] for row in feature_rows})


def test_phase3h_gold_set_is_honest_empty_without_strong_labels():
    gold = read_json(PHASE3H_DRIFTBENCH / "gold_set_manifest.json")

    assert gold["gold_record_count"] == 0
    assert gold["records"] == []
    assert "No real Phase 3H records currently have external confirmation" in gold["exclusion_reason"]


def test_phase3h_reviewer_adjudication_and_inter_rater_guards():
    reviewer_schema = read_json(PHASE3H_DRIFTBENCH / "reviewer_schema.json")
    adjudication = read_json(PHASE3H_DRIFTBENCH / "adjudication_report.json")
    inter_rater = read_json(PHASE3H_DRIFTBENCH / "inter_rater_agreement.json")
    queue = read_json(PHASE3H_DRIFTBENCH / "second_review_queue.json")

    assert "blind_review_status" in reviewer_schema["fields"]
    assert "adjudicated_label" in reviewer_schema["fields"]
    assert adjudication["adjudicated_count"] == 0
    assert inter_rater["status"] == "INTER_RATER_AGREEMENT_NOT_AVAILABLE"
    assert queue["status"] == "created_no_second_reviewer_fabricated"


def test_phase3h_feature_schema_preserved_and_no_ml_integration():
    phase3g_schema = read_json(Path("artifacts/driftbench/phase3g_features/feature_schema.json"))
    phase3h_schema = read_json(PHASE3H_FEATURES / "feature_schema.json")
    extraction = read_json(PHASE3H_FEATURES / "extraction_manifest.json")
    experiment = read_json(PHASE3H / "experiment_manifest.json")

    assert [feature["name"] for feature in phase3h_schema["features"]] == [
        feature["name"] for feature in phase3g_schema["features"]
    ]
    assert extraction["model_training_performed"] is False
    assert extraction["production_ml_integration"] is False
    assert experiment["model_training_performed"] is False
    assert experiment["production_ml_integration"] is False


def test_phase3h_quality_reports_and_next_decision():
    readiness = read_json(PHASE3H_DRIFTBENCH / "readiness.json")
    quality = read_json(PHASE3H_DRIFTBENCH / "dataset_quality_report.json")
    analyzer = read_json(PHASE3H_DRIFTBENCH / "analyzer_health.json")

    assert readiness["phase3h_complete"] is True
    assert readiness["recommended_next_phase"] == "CONTINUE INDEPENDENT LABEL REVIEW / ADJUDICATION"
    assert quality["dimensions"]["gold_set_size"] == 0
    assert quality["dimensions"]["external_holdout_size"] == 10
    assert analyzer["total_missingness_count"] == 0


def test_phase3g_vs_phase3h_dataset_comparison():
    rows = {row["metric"]: row for row in read_csv(PHASE3H / "phase3g_vs_phase3h_dataset.csv")}

    assert rows["total_real_records"]["phase3g"] == "58"
    assert rows["total_real_records"]["phase3h"] == "76"
    assert rows["unique_extensions"]["phase3g"] == "17"
    assert rows["unique_extensions"]["phase3h"] == "21"
    assert rows["external_holdout_size"]["phase3h"] == "10"
