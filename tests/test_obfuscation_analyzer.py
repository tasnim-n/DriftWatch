import os
import tempfile
import shutil
from analyzers.obfuscation_analyzer import ObfuscationAnalyzer

def test_shannon_entropy_calculation():
    low_entropy = "AAAAAAABBBBBBCCCCCC"
    high_entropy = "4k8g!9@L#q$Z%m^P&x*W"
    
    e_low = ObfuscationAnalyzer.calculate_shannon_entropy(low_entropy)
    e_high = ObfuscationAnalyzer.calculate_shannon_entropy(high_entropy)

    assert e_low < 3.0
    assert e_high > 4.0

def test_obfuscation_indicator_detection():
    js_code = """
eval("console.log('eval test')");
const fn = new Function("a", "return a + 1");
const decoded = atob("aHR0cDovL2V4YW1wbGUuY29t");
"""
    dir_path = tempfile.mkdtemp()
    file_path = os.path.join(dir_path, "obf.js")
    with open(file_path, "w") as f:
        f.write(js_code)

    indicators = ObfuscationAnalyzer.scan_file_obfuscation(file_path, "obf.js")
    types = [i["type"] for i in indicators]

    assert "eval_call" in types
    assert "new_function" in types
    assert "atob_decode" in types

    shutil.rmtree(dir_path, ignore_errors=True)
