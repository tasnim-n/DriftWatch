import os
import re
from typing import Dict, Any, List, Set
from analyzers.javascript_parser import JavaScriptParser

class APIAnalyzer:
    """
    Extracts sensitive browser API calls from JavaScript files in an extension package.
    Attributes file name, line number, API name, category, and severity.
    Ensures comments and string literals are not mistaken for API calls.
    """

    TARGET_APIS = [
        {"pattern": r"\bchrome\.cookies(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.cookies", "category": "Cookies", "severity": "Critical"},
        {"pattern": r"\bchrome\.history(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.history", "category": "History", "severity": "Critical"},
        {"pattern": r"\bchrome\.tabs(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.tabs", "category": "Tabs", "severity": "High"},
        {"pattern": r"\bchrome\.webRequest(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.webRequest", "category": "Network Interception", "severity": "Critical"},
        {"pattern": r"\bchrome\.downloads(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.downloads", "category": "Downloads", "severity": "High"},
        {"pattern": r"\bchrome\.proxy(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.proxy", "category": "Proxy Control", "severity": "Critical"},
        {"pattern": r"\bchrome\.debugger(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.debugger", "category": "Debugger Access", "severity": "Critical"},
        {"pattern": r"\bchrome\.identity(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.identity", "category": "Identity", "severity": "High"},
        {"pattern": r"\bchrome\.storage(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.storage", "category": "Storage", "severity": "Moderate"},
        {"pattern": r"\bchrome\.scripting(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.scripting", "category": "Code Injection", "severity": "Critical"},
        {"pattern": r"\bchrome\.management(?:\.[a-zA-Z0-9_]+)+", "name": "chrome.management", "category": "Management", "severity": "High"},
        {"pattern": r"\bnavigator\.clipboard(?:\.[a-zA-Z0-9_]+)+", "name": "navigator.clipboard", "category": "Clipboard", "severity": "High"},
        {"pattern": r"\bfetch\s*\(", "name": "fetch", "category": "Network Request", "severity": "Moderate"},
        {"pattern": r"\bnew\s+XMLHttpRequest\s*\(", "name": "XMLHttpRequest", "category": "Network Request", "severity": "Moderate"},
        {"pattern": r"\bnew\s+WebSocket\s*\(", "name": "WebSocket", "category": "WebSocket", "severity": "Moderate"},
        {"pattern": r"\bnavigator\.sendBeacon\s*\(", "name": "sendBeacon", "category": "Telemetry Sink", "severity": "Moderate"},
        {"pattern": r"\blocalStorage\b", "name": "localStorage", "category": "Local Storage", "severity": "Low"},
        {"pattern": r"\bindexedDB\b", "name": "indexedDB", "category": "Database Storage", "severity": "Low"},
    ]

    @classmethod
    def scan_file_for_apis(cls, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        if not file_path.endswith(".js"):
            return []

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        parsed_lines = JavaScriptParser.parse_code_lines(code)
        found_apis = []
        seen = set()

        for line_item in parsed_lines:
            line_num = line_item["line"]
            clean_text = line_item["clean"]
            if not clean_text.strip():
                continue

            # Strip string literals before searching for executable API calls.
            code_only = JavaScriptParser.mask_string_literals(clean_text)

            for target in cls.TARGET_APIS:
                for match in re.finditer(target["pattern"], code_only):
                    key = (rel_path, target["name"], line_num)
                    if key in seen:
                        continue
                    seen.add(key)
                    found_apis.append({
                        "file": rel_path,
                        "line": line_num,
                        "matched_text": match.group(0),
                        "api_name": target["name"],
                        "category": target["category"],
                        "severity": target["severity"],
                        "snippet": clean_text.strip()[:100]
                    })

        return found_apis

    @classmethod
    def analyze_directory_apis(cls, extension_dir: str) -> List[Dict[str, Any]]:
        results = []
        for root, _, files in os.walk(extension_dir):
            for file in files:
                if file.endswith(".js"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, extension_dir).replace("\\", "/")
                    results.extend(cls.scan_file_for_apis(full_path, rel_path))
        return results

    @classmethod
    def compare_api_drift(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        v1_apis = cls.analyze_directory_apis(v1_dir)
        v2_apis = cls.analyze_directory_apis(v2_dir)

        v1_set = {(a["file"], a["api_name"]) for a in v1_apis}
        v2_set = {(a["file"], a["api_name"]) for a in v2_apis}

        added_api_keys = v2_set - v1_set
        removed_api_keys = v1_set - v2_set

        added_apis = []
        seen_added = set()
        for api in v2_apis:
            key = (api["file"], api["api_name"])
            if key in added_api_keys and key not in seen_added:
                seen_added.add(key)
                added_apis.append(api)
        retained_apis = [a for a in v2_apis if (a["file"], a["api_name"]) in (v1_set & v2_set)]

        # Unique added API names
        unique_added_names = sorted(list({a["api_name"] for a in added_apis}))

        # Max severity of added APIs
        severity_rank = {"Low": 1, "Moderate": 2, "High": 3, "Critical": 4}
        max_severity = "Low"
        for a in added_apis:
            if severity_rank.get(a["severity"], 1) > severity_rank.get(max_severity, 1):
                max_severity = a["severity"]

        return {
            "v1_api_count": len(v1_apis),
            "v2_api_count": len(v2_apis),
            "v2_apis": v2_apis,
            "added_apis": added_apis,
            "retained_apis": retained_apis,
            "unique_added_api_names": unique_added_names,
            "max_added_api_severity": max_severity if added_apis else "None",
            "is_api_drift": len(added_apis) > 0
        }
