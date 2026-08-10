import os
import tempfile
import shutil
from analyzers.package_analyzer import PackageAnalyzer

def test_package_analyzer_diff():
    dir_v1 = tempfile.mkdtemp()
    dir_v2 = tempfile.mkdtemp()

    # V1 files
    with open(os.path.join(dir_v1, "manifest.json"), "w") as f:
        f.write('{"version": "1.0"}')
    with open(os.path.join(dir_v1, "script.js"), "w") as f:
        f.write('console.log("v1");')

    # V2 files (modifies script.js, adds background.js)
    with open(os.path.join(dir_v2, "manifest.json"), "w") as f:
        f.write('{"version": "2.0"}')
    with open(os.path.join(dir_v2, "script.js"), "w") as f:
        f.write('console.log("v2 updated");')
    with open(os.path.join(dir_v2, "background.js"), "w") as f:
        f.write('console.log("background worker");')

    diff = PackageAnalyzer.compare_packages(dir_v1, dir_v2)

    assert diff["v1_file_count"] == 2
    assert diff["v2_file_count"] == 3
    assert diff["added_files"] == ["background.js"]
    assert len(diff["modified_files"]) == 2 # manifest.json and script.js modified

    shutil.rmtree(dir_v1, ignore_errors=True)
    shutil.rmtree(dir_v2, ignore_errors=True)
