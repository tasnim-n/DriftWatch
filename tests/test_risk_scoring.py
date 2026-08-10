import json
import os
import shutil
import tempfile

from analyzers.drift_engine import DriftEngine
from analyzers.network_analyzer import NetworkAnalyzer
from risk_engine.scoring import RiskScorer


def _extension_dir(manifest: dict, files: dict[str, str]) -> str:
    directory = tempfile.mkdtemp()
    with open(os.path.join(directory, "manifest.json"), "w") as f:
        json.dump(manifest, f)
    for path, content in files.items():
        full_path = os.path.join(directory, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    return directory


def _score(v1_manifest, v2_manifest, v1_files=None, v2_files=None):
    v1_dir = _extension_dir(v1_manifest, v1_files or {})
    v2_dir = _extension_dir(v2_manifest, v2_files or {})
    try:
        drift = DriftEngine.compute_behavioral_drift(v1_dir, v2_dir)
        return drift, RiskScorer.calculate_risk_score(drift)
    finally:
        shutil.rmtree(v1_dir, ignore_errors=True)
        shutil.rmtree(v2_dir, ignore_errors=True)


BASE_MANIFEST = {
    "manifest_version": 3,
    "name": "Test",
    "version": "1.0.0",
    "permissions": ["storage"],
    "host_permissions": ["https://notes.local/*"],
}


def test_score_never_exceeds_100_for_severe_sample():
    drift = DriftEngine.compute_behavioral_drift("samples/v1_safe_note", "samples/v2_risky_note")
    result = RiskScorer.calculate_risk_score(drift)

    assert result["risk_score"] <= 100
    assert result["raw_score_before_cap"] >= result["risk_score"]


def test_localhost_endpoint_alone_cannot_produce_critical():
    v2_manifest = dict(BASE_MANIFEST, version="1.0.1")
    _, result = _score(
        BASE_MANIFEST,
        v2_manifest,
        {"popup.js": ""},
        {"popup.js": 'fetch("http://127.0.0.1:8000/test");'},
    )

    assert result["risk_classification"] != "Critical"
    assert result["score_breakdown"]["network_contribution"] <= 2.0


def test_formatting_only_update_remains_low_risk():
    _, result = _score(
        BASE_MANIFEST,
        dict(BASE_MANIFEST, version="1.0.1"),
        {"popup.js": "function saveNote() { console.log('save'); }"},
        {"popup.js": "// comment\nfunction saveNote() {\n  console.log('save');\n}"},
    )

    assert result["risk_classification"] == "Low"


def test_benign_sample_does_not_become_critical():
    drift = DriftEngine.compute_behavioral_drift("samples/v1_note_benign", "samples/v2_note_benign")
    result = RiskScorer.calculate_risk_score(drift)

    assert result["risk_classification"] in {"Low", "Moderate"}


def test_severe_multi_signal_update_can_still_be_critical():
    drift = DriftEngine.compute_behavioral_drift("samples/v1_safe_note", "samples/v2_risky_note")
    result = RiskScorer.calculate_risk_score(drift)

    assert result["risk_classification"] == "Critical"
    assert result["score_breakdown"]["permission_contribution"] > 0
    assert result["score_breakdown"]["host_contribution"] > 0
    assert result["score_breakdown"]["structural_contribution"] > 0


def test_duplicate_network_findings_do_not_inflate_score():
    v1_dir = _extension_dir(BASE_MANIFEST, {"popup.js": ""})
    v2_dir = _extension_dir(
        dict(BASE_MANIFEST, version="1.0.1"),
        {"popup.js": 'fetch("https://dup.example.com/a");\nfetch("https://dup.example.com/a");'},
    )
    try:
        network = NetworkAnalyzer.compare_network_drift(v1_dir, v2_dir)
        drift = DriftEngine.compute_behavioral_drift(v1_dir, v2_dir)
        result = RiskScorer.calculate_risk_score(drift)
    finally:
        shutil.rmtree(v1_dir, ignore_errors=True)
        shutil.rmtree(v2_dir, ignore_errors=True)

    assert len(network["new_external_destinations"]) == 1
    assert result["score_breakdown"]["network_contribution"] == 8.0


def test_confidence_reflects_optional_analyzer_completeness():
    drift = DriftEngine.compute_behavioral_drift("samples/v1_safe_note", "samples/v2_risky_note")
    full_result = RiskScorer.calculate_risk_score(drift)

    drift_with_error = dict(drift)
    drift_with_error["analyzer_errors"] = {"api_analyzer": "forced failure"}
    partial_result = RiskScorer.calculate_risk_score(drift_with_error)

    assert full_result["confidence_score"] == 1.0
    assert partial_result["confidence_score"] == 0.75
    assert partial_result["confidence_breakdown"]["meaning"] == "Static-analysis completeness score; not a malware probability."
