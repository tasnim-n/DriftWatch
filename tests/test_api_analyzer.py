import os
import tempfile
import shutil
from analyzers.api_analyzer import APIAnalyzer

def test_api_call_detection_no_comment_false_positives():
    js_code = """
// chrome.cookies.getAll({}, callback);
/* chrome.history.search({}, callback); */
console.log("Usage of chrome.webRequest.onBeforeRequest string literal");

function fetchCookies() {
    chrome.cookies.get({ url: "https://example.com" }, (c) => {});
    fetch("https://example.com/api");
}
"""
    dir_path = tempfile.mkdtemp()
    file_path = os.path.join(dir_path, "background.js")
    with open(file_path, "w") as f:
        f.write(js_code)

    apis = APIAnalyzer.scan_file_for_apis(file_path, "background.js")
    api_names = [a["api_name"] for a in apis]

    # Only executable calls should be matched
    assert "chrome.cookies" in api_names
    assert "fetch" in api_names
    # Comments and plain strings should not trigger extra calls
    assert len(apis) == 2
    assert apis[0]["line"] == 7
    assert apis[1]["line"] == 8

    shutil.rmtree(dir_path, ignore_errors=True)
