import os
import json
import tempfile
import shutil
from analyzers.manifest_analyzer import ManifestAnalyzer

def test_manifest_analyzer_v3():
    dir_v1 = tempfile.mkdtemp()
    dir_v2 = tempfile.mkdtemp()

    m1 = {
        "manifest_version": 3,
        "name": "Test Extension",
        "version": "1.0.0",
        "permissions": ["storage"],
        "host_permissions": ["https://example.com/*"]
    }

    m2 = {
        "manifest_version": 3,
        "name": "Test Extension",
        "version": "2.0.0",
        "permissions": ["storage", "cookies"],
        "host_permissions": ["<all_urls>"],
        "background": {"service_worker": "background.js"}
    }

    with open(os.path.join(dir_v1, "manifest.json"), "w") as f:
        json.dump(m1, f)
    with open(os.path.join(dir_v2, "manifest.json"), "w") as f:
        json.dump(m2, f)

    diff = ManifestAnalyzer.compare_manifests(dir_v1, dir_v2)

    assert diff["v1_permissions"] == ["storage"]
    assert diff["v2_permissions"] == ["storage", "cookies"]
    assert diff["v1_hosts"] == ["https://example.com/*"]
    assert diff["v2_hosts"] == ["<all_urls>"]
    assert diff["background_added"] is True

    shutil.rmtree(dir_v1, ignore_errors=True)
    shutil.rmtree(dir_v2, ignore_errors=True)
