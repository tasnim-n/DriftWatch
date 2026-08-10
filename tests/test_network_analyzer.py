import os
import tempfile
import shutil
import base64
from analyzers.network_analyzer import NetworkAnalyzer

def _scan_js(js_code: str):
    dir_path = tempfile.mkdtemp()
    file_path = os.path.join(dir_path, "net.js")
    with open(file_path, "w") as f:
        f.write(js_code)
    try:
        return NetworkAnalyzer.extract_network_indicators(file_path, "net.js")
    finally:
        shutil.rmtree(dir_path, ignore_errors=True)

def test_localhost_and_external_destination_classification():
    js_code = """
const localApi = "http://127.0.0.1:8000/test";
const testDomain = "http://analytics.untrusted-domain.com/collect";
const publicTarget = "https://api.external-service.com/v1/user";
const hardcodedIp = "192.168.1.50";
"""
    indicators = _scan_js(js_code)

    local_urls = [i["value"] for i in indicators if i["is_local"]]
    external_urls = [i["value"] for i in indicators if not i["is_local"]]

    assert "http://127.0.0.1:8000/test" in local_urls
    assert "http://analytics.untrusted-domain.com/collect" in local_urls
    assert "https://api.external-service.com/v1/user" in external_urls

def test_websocket_and_ipv6_loopback_detection():
    indicators = _scan_js("""
const wsLocal = "ws://localhost:9001/socket";
const secureWs = "wss://stream.example.com/feed";
const ipv6 = "http://[::1]:8000/test";
""")
    values = {item["value"]: item for item in indicators}

    assert values["ws://localhost:9001/socket"]["is_local"] is True
    assert values["wss://stream.example.com/feed"]["is_local"] is False
    assert values["http://[::1]:8000/test"]["is_local"] is True

def test_direct_network_sink_destinations_are_detected_once():
    indicators = _scan_js("""
fetch("https://api.example.com/v1/user");
const xhr = new XMLHttpRequest();
xhr.open("POST", "https://upload.example.net/collect");
const ws = new WebSocket("wss://socket.example.org/live");
navigator.sendBeacon("https://beacon.example.io/ping", "{}");
""")
    values = [item["value"] for item in indicators]

    assert "https://api.example.com/v1/user" in values
    assert "https://upload.example.net/collect" in values
    assert "wss://socket.example.org/live" in values
    assert "https://beacon.example.io/ping" in values
    assert values.count("https://api.example.com/v1/user") == 1

def test_bare_domain_and_ipv4_detection():
    indicators = _scan_js("""
const domain = "collector.example.com:8443/path";
const ip = "192.168.1.50";
""")
    values = {item["value"] for item in indicators}

    assert "collector.example.com:8443/path" in values
    assert "192.168.1.50" in values

def test_valid_base64_url_static_decoding():
    encoded = base64.b64encode(b"http://127.0.0.1:8000/test").decode()
    indicators = _scan_js(f'const target = atob("{encoded}");')
    decoded = [item for item in indicators if item.get("source") == "Decoded static endpoint indicator"]

    assert decoded
    assert decoded[0]["decoded_indicator"] == "http://127.0.0.1:8000/test"
    assert decoded[0]["encoding_type"] == "base64"
    assert decoded[0]["is_local"] is True

def test_invalid_base64_does_not_create_decoded_endpoint():
    indicators = _scan_js('const maybe = "not-valid-base64!!!!";')

    assert not [item for item in indicators if item.get("source") == "Decoded static endpoint indicator"]

def test_oversized_base64_is_not_decoded():
    oversized = "A" * (NetworkAnalyzer.MAX_ENCODED_LENGTH + 1)
    indicators = _scan_js(f'const huge = "{oversized}";')

    assert not [item for item in indicators if item.get("source") == "Decoded static endpoint indicator"]

def test_base64_without_endpoint_is_ignored_by_network_decoder():
    encoded = base64.b64encode(b"plain text that is not a url or a domain").decode()
    indicators = _scan_js(f'const data = "{encoded}";')

    assert not [item for item in indicators if item.get("source") == "Decoded static endpoint indicator"]
