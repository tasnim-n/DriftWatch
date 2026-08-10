import os
import re
from typing import Dict, Any, List, Set
from analyzers.javascript_parser import JavaScriptParser

class StructureAnalyzer:
    """
    Analyzes structural code drift, function additions/deletions, event listeners,
    and sensitive source-to-sink heuristic patterns while resisting whitespace and formatting changes.
    """

    SOURCES = [
        {"name": "cookies", "pattern": r"\bchrome\.cookies\.(?:get|getAll)\b"},
        {"name": "history", "pattern": r"\bchrome\.history\.(?:search|getVisits)\b"},
        {"name": "clipboard", "pattern": r"\bnavigator\.clipboard\.readText\b"},
        {"name": "tabs", "pattern": r"\bchrome\.tabs\.(?:query|get)\b"},
        {"name": "storage", "pattern": r"\bchrome\.storage\.(?:local|sync)\.get\b"},
        {"name": "localStorage", "pattern": r"\blocalStorage\.(?:getItem|key)\b|\blocalStorage\b"},
        {"name": "sessionStorage", "pattern": r"\bsessionStorage\.(?:getItem|key)\b|\bsessionStorage\b"},
        {"name": "indexedDB", "pattern": r"\bindexedDB\b"},
        {"name": "geolocation", "pattern": r"\bnavigator\.geolocation\.(?:getCurrentPosition|watchPosition)\b"},
        {"name": "dom_form_fields", "pattern": r"\b(?:document\.querySelector|getElementById|getElementsByName)\s*\([^)]*(?:input|password|email|form|textarea)"}
    ]

    SINKS = [
        {"name": "fetch", "pattern": r"\bfetch\s*\("},
        {"name": "xhr", "pattern": r"\bnew\s+XMLHttpRequest\b"},
        {"name": "websocket", "pattern": r"\bnew\s+WebSocket\b"},
        {"name": "sendBeacon", "pattern": r"\bnavigator\.sendBeacon\b"},
        {"name": "form_submission", "pattern": r"\b(?:HTMLFormElement\.prototype\.submit|\.submit\s*\()"},
        {"name": "external_messaging", "pattern": r"\b(?:chrome|browser)\.runtime\.(?:sendMessage|connect)\b|\bpostMessage\s*\("}
    ]

    @classmethod
    def normalize_code(cls, js_code: str) -> str:
        """Strip comments and collapse whitespace to prevent formatting-only diff false positives."""
        clean = JavaScriptParser.strip_comments(js_code)
        # Collapse multiple whitespace characters into single space
        return re.sub(r'\s+', ' ', clean).strip()

    @classmethod
    def extract_function_signatures(cls, js_code: str) -> List[str]:
        """Extract function names and arrow function assignments."""
        clean_code = JavaScriptParser.strip_comments(js_code)
        fn_pattern = re.compile(r'\bfunction\s+([a-zA-Z0-9_$]+)\s*\(|\bconst\s+([a-zA-Z0-9_$]+)\s*=\s*(?:function|\([^)]*\)\s*=>)')
        
        funcs = []
        for match in fn_pattern.finditer(clean_code):
            name = match.group(1) or match.group(2)
            if name:
                funcs.append(name)
        return funcs

    @classmethod
    def extract_event_listeners(cls, js_code: str) -> List[str]:
        """Extract event listener registrations."""
        clean_code = JavaScriptParser.strip_comments(js_code)
        listener_pattern = re.compile(r'(?:addEventListener|chrome\.[a-zA-Z0-9\.]+\.addListener)\s*\(\s*[\'"`]?([a-zA-Z0-9_\-]+)[\'"`]?')
        
        listeners = []
        for match in listener_pattern.finditer(clean_code):
            listeners.append(match.group(0)[:60])
        return listeners

    @classmethod
    def detect_source_sink_flows(cls, js_code: str, file_name: str) -> List[Dict[str, Any]]:
        """Identify files containing both a sensitive data source and an external network sink."""
        parsed_lines = JavaScriptParser.parse_code_lines(js_code)

        detected_sources = []
        detected_sinks = []

        for line_item in parsed_lines:
            code_only = JavaScriptParser.mask_string_literals(line_item["clean"])
            if not code_only.strip():
                continue

            for src in cls.SOURCES:
                if re.search(src["pattern"], code_only):
                    detected_sources.append({
                        "name": src["name"],
                        "line": line_item["line"],
                        "snippet": line_item["clean"].strip()[:120]
                    })

            for sink in cls.SINKS:
                if re.search(sink["pattern"], code_only):
                    detected_sinks.append({
                        "name": sink["name"],
                        "line": line_item["line"],
                        "snippet": line_item["clean"].strip()[:120]
                    })

        flows = []
        if detected_sources and detected_sinks:
            source_names = sorted({item["name"] for item in detected_sources})
            sink_names = sorted({item["name"] for item in detected_sinks})
            flows.append({
                "file": file_name,
                "sources": source_names,
                "sinks": sink_names,
                "source_evidence": detected_sources,
                "sink_evidence": detected_sinks,
                "pattern": f"Heuristic source ({', '.join(source_names)}) near sink ({', '.join(sink_names)})",
                "severity": "Critical" if {"cookies", "history", "clipboard", "dom_form_fields"} & set(source_names) else "High",
                "confidence": 0.75,
                "claim": "Heuristic indicator only; not confirmed exfiltration."
            })
        return flows

    @classmethod
    def compare_structural_drift(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        # Collect functions and event listeners from v1 and v2
        v1_funcs = set()
        v2_funcs = set()
        v1_listeners = set()
        v2_listeners = set()
        v2_source_sink_flows = []

        for root, _, files in os.walk(v1_dir):
            for file in files:
                if file.endswith(".js"):
                    path = os.path.join(root, file)
                    rel = os.path.relpath(path, v1_dir).replace("\\", "/")
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    for fn in cls.extract_function_signatures(code):
                        v1_funcs.add((rel, fn))
                    for listener in cls.extract_event_listeners(code):
                        v1_listeners.add((rel, listener))

        for root, _, files in os.walk(v2_dir):
            for file in files:
                if file.endswith(".js"):
                    path = os.path.join(root, file)
                    rel = os.path.relpath(path, v2_dir).replace("\\", "/")
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    for fn in cls.extract_function_signatures(code):
                        v2_funcs.add((rel, fn))
                    for listener in cls.extract_event_listeners(code):
                        v2_listeners.add((rel, listener))

                    flows = cls.detect_source_sink_flows(code, rel)
                    v2_source_sink_flows.extend(flows)

        added_funcs = sorted([f"{rel}:{fn}" for rel, fn in (v2_funcs - v1_funcs)])
        added_listeners = sorted([f"{rel}:{lst}" for rel, lst in (v2_listeners - v1_listeners)])

        return {
            "v1_function_count": len(v1_funcs),
            "v2_function_count": len(v2_funcs),
            "added_functions": added_funcs,
            "added_event_listeners": added_listeners,
            "source_sink_flows": v2_source_sink_flows,
            "is_structural_drift": len(added_funcs) > 0 or len(added_listeners) > 0 or len(v2_source_sink_flows) > 0
        }
