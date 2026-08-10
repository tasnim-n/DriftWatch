import os
import re
import math
from typing import Dict, Any, List
from analyzers.javascript_parser import JavaScriptParser

class ObfuscationAnalyzer:
    """
    Detects dynamic code execution, string encoding, high Shannon entropy strings,
    hexadecimal/unicode escaping, and WebAssembly introduction across extension versions.
    """

    @staticmethod
    def calculate_shannon_entropy(text: str) -> float:
        """Calculate Shannon entropy H = - sum(p_i * log2(p_i))."""
        if not text:
            return 0.0
        length = len(text)
        counts = {}
        for char in text:
            counts[char] = counts.get(char, 0) + 1
        
        entropy = 0.0
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        return round(entropy, 3)

    OBFUSCATION_PATTERNS = [
        {"name": "eval_call", "pattern": r"\beval\s*\(", "score": 25, "desc": "Dynamic code evaluation via eval()."},
        {"name": "new_function", "pattern": r"\bnew\s+Function\s*\(", "score": 25, "desc": "Dynamic function instantiation via new Function()."},
        {"name": "string_timer", "pattern": r"\b(?:setTimeout|setInterval)\s*\(\s*['\"`]", "score": 15, "desc": "String-based timer execution."},
        {"name": "atob_decode", "pattern": r"\batob\s*\(", "score": 10, "desc": "Base64 decoding via atob()."},
        {"name": "from_char_code", "pattern": r"\bString\.fromCharCode\s*\(", "score": 10, "desc": "Char code decoding via String.fromCharCode()."},
        {"name": "hex_escaping", "pattern": r"(?:\\x[0-9a-fA-F]{2}){4,}", "score": 15, "desc": "Hexadecimal string escaping sequence."},
        {"name": "unicode_escaping", "pattern": r"(?:\\u[0-9a-fA-F]{4}){4,}", "score": 15, "desc": "Unicode string escaping sequence."},
        {"name": "dynamic_script_creation", "pattern": r"document\.createElement\s*\(\s*['\"`]script['\"`]\s*\)", "score": 15, "desc": "Dynamic DOM script tag creation."},
        {"name": "dynamic_import", "pattern": r"\bimport\s*\(", "score": 10, "desc": "Dynamic JavaScript module import."},
        {"name": "wasm_usage", "pattern": r"\bWebAssembly\.(?:compile|instantiate)", "score": 20, "desc": "WebAssembly binary execution."}
    ]

    @classmethod
    def scan_file_obfuscation(cls, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        results = []
        parsed_lines = JavaScriptParser.parse_code_lines(code)

        # 1. Pattern matching on code lines
        for line_item in parsed_lines:
            line_num = line_item["line"]
            clean_text = line_item["clean"]

            for target in cls.OBFUSCATION_PATTERNS:
                if re.search(target["pattern"], clean_text):
                    results.append({
                        "file": rel_path,
                        "line": line_num,
                        "type": target["name"],
                        "score": target["score"],
                        "description": target["desc"],
                        "snippet": clean_text.strip()[:100]
                    })

        # 2. String literal analysis (Base64 & High Entropy)
        string_literals = JavaScriptParser.extract_string_literals(code)
        for s in string_literals:
            val = s["value"]
            if len(val) >= 40:
                entropy = cls.calculate_shannon_entropy(val)
                if entropy >= 5.0:
                    results.append({
                        "file": rel_path,
                        "line": s["line"],
                        "type": "high_entropy_string",
                        "score": 15,
                        "description": f"High Shannon entropy string detected (H={entropy:.2f}).",
                        "snippet": val[:60] + "..."
                    })
                elif len(val) >= 60 and re.match(r'^[A-Za-z0-9+/=]+$', val):
                    results.append({
                        "file": rel_path,
                        "line": s["line"],
                        "type": "long_base64_string",
                        "score": 10,
                        "description": "Long Base64 encoded string detected.",
                        "snippet": val[:60] + "..."
                    })

        return results

    @classmethod
    def analyze_directory_obfuscation(cls, extension_dir: str) -> List[Dict[str, Any]]:
        indicators = []
        for root, _, files in os.walk(extension_dir):
            for file in files:
                if file.endswith(".js"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, extension_dir).replace("\\", "/")
                    indicators.extend(cls.scan_file_obfuscation(full_path, rel_path))
                elif file.endswith(".wasm"):
                    rel_path = os.path.relpath(os.path.join(root, file), extension_dir).replace("\\", "/")
                    indicators.append({
                        "file": rel_path,
                        "line": 1,
                        "type": "wasm_file",
                        "score": 25,
                        "description": "WebAssembly binary file introduced in package.",
                        "snippet": file
                    })
        return indicators

    @classmethod
    def compare_obfuscation_drift(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        v1_ind = cls.analyze_directory_obfuscation(v1_dir)
        v2_ind = cls.analyze_directory_obfuscation(v2_dir)

        v1_keys = {(i["file"], i["type"], i.get("line")) for i in v1_ind}
        v2_keys = {(i["file"], i["type"], i.get("line")) for i in v2_ind}

        added_keys = v2_keys - v1_keys
        added_indicators = [i for i in v2_ind if (i["file"], i["type"], i.get("line")) in added_keys]

        added_obfuscation_score = sum(i["score"] for i in added_indicators)

        return {
            "v1_indicator_count": len(v1_ind),
            "v2_indicator_count": len(v2_ind),
            "added_indicators": added_indicators,
            "added_obfuscation_score": added_obfuscation_score,
            "is_obfuscation_drift": len(added_indicators) > 0 and added_obfuscation_score > 0
        }
