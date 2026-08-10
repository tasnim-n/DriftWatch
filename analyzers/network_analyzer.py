import os
import re
import base64
import binascii
import urllib.parse
from typing import Dict, Any, List, Set
from analyzers.javascript_parser import JavaScriptParser

class NetworkAnalyzer:
    """
    Extracts network endpoints, URLs, IP addresses, WebSocket endpoints, and fetch/XHR destinations.
    Distinguishes local/test endpoints (localhost, 127.0.0.1) from external infrastructure.
    """

    LOCAL_PATTERNS = [
        re.compile(r"^127\.\d+\.\d+\.\d+$"),
        re.compile(r"^localhost$", re.IGNORECASE),
        re.compile(r"^0\.0\.0\.0$"),
        re.compile(r"^\[?::1\]?$"),
        re.compile(r".*\.local$", re.IGNORECASE),
        re.compile(r".*untrusted-domain\.com$", re.IGNORECASE) # Controlled test domain
    ]

    URL_REGEX = re.compile(
        r'https?://(?:\[[0-9a-fA-F:]+\]|[a-zA-Z0-9.\-]+)(?::\d+)?(?:/[^\s\'"`<>]*)?',
        re.IGNORECASE
    )

    WS_REGEX = re.compile(
        r'wss?://(?:\[[0-9a-fA-F:]+\]|[a-zA-Z0-9.\-]+)(?::\d+)?(?:/[^\s\'"`<>]*)?',
        re.IGNORECASE
    )

    IP_REGEX = re.compile(
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    )

    DOMAIN_REGEX = re.compile(
        r'(?<![@/\w.-])(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s\'"`<>]*)?',
        re.IGNORECASE
    )

    BASE64_CANDIDATE_REGEX = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')
    MAX_ENCODED_LENGTH = 4096
    MAX_DECODED_LENGTH = 8192
    MAX_NON_MANIFEST_JSON_SCAN_BYTES = 2 * 1024 * 1024
    NON_NETWORK_TLDS = {
        "js", "json", "html", "htm", "css", "png", "jpg", "jpeg", "gif",
        "svg", "wasm", "txt", "md", "map"
    }

    @classmethod
    def is_local_endpoint(cls, host_or_url: str) -> bool:
        host = ""
        try:
            if "://" in host_or_url:
                parsed = urllib.parse.urlparse(host_or_url)
                host = parsed.hostname or ""
            else:
                host = host_or_url.split(":")[0].split("/")[0]
        except Exception:
            host = host_or_url

        if not host:
            return False

        for pat in cls.LOCAL_PATTERNS:
            if pat.search(host):
                return True
        return False

    @classmethod
    def _indicator_base(
        cls,
        rel_path: str,
        line: int,
        indicator_type: str,
        value: str,
        source: str,
        confidence: float = 1.0,
        encoding_type: str | None = None,
    ) -> Dict[str, Any]:
        is_local = cls.is_local_endpoint(value)
        is_http = value.lower().startswith("http://")
        has_uncommon_port = bool(re.search(r':(?!80(?:/|$)|443(?:/|$))\d+', value))
        return {
            "file": rel_path,
            "line": line,
            "type": indicator_type,
            "value": value,
            "source": source,
            "is_local": is_local,
            "is_plain_http": is_http and not is_local,
            "has_uncommon_port": has_uncommon_port,
            "confidence": confidence,
            "encoding_type": encoding_type,
        }

    @classmethod
    def _add_indicator(
        cls,
        results: List[Dict[str, Any]],
        seen: Set[tuple],
        rel_path: str,
        line: int,
        indicator_type: str,
        value: str,
        source: str,
        confidence: float = 1.0,
        encoding_type: str | None = None,
    ) -> None:
        value = value.rstrip(").,;")
        key = (rel_path, line, value.lower())
        if key in seen:
            return
        seen.add(key)
        results.append(cls._indicator_base(rel_path, line, indicator_type, value, source, confidence, encoding_type))

    @classmethod
    def _extract_indicators_from_text(
        cls,
        text: str,
        rel_path: str,
        line: int,
        source: str,
        results: List[Dict[str, Any]],
        seen: Set[tuple],
        confidence: float = 1.0,
        encoding_type: str | None = None,
        include_bare_domains: bool = True,
    ) -> None:
        occupied_spans = []

        for regex, indicator_type in ((cls.URL_REGEX, "URL"), (cls.WS_REGEX, "WebSocket")):
            for match in regex.finditer(text):
                occupied_spans.append(match.span())
                cls._add_indicator(
                    results, seen, rel_path, line, indicator_type, match.group(0),
                    source, confidence, encoding_type
                )

        for match in cls.IP_REGEX.finditer(text):
            start, end = match.span()
            if any(start >= span_start and end <= span_end for span_start, span_end in occupied_spans):
                continue
            ip = match.group(0)
            cls._add_indicator(
                results, seen, rel_path, line, "IPv4", ip, source, confidence, encoding_type
            )

        if include_bare_domains:
            for match in cls.DOMAIN_REGEX.finditer(text):
                start, end = match.span()
                if any(start >= span_start and end <= span_end for span_start, span_end in occupied_spans):
                    continue
                domain = match.group(0)
                if "." not in domain:
                    continue
                hostname = domain.split("/", 1)[0].split(":", 1)[0].lower()
                tld = hostname.rsplit(".", 1)[-1]
                if tld in cls.NON_NETWORK_TLDS:
                    continue
                cls._add_indicator(
                    results, seen, rel_path, line, "Domain", domain, source, confidence, encoding_type
                )

    @classmethod
    def _extract_direct_sink_destinations(
        cls,
        clean_text: str,
        rel_path: str,
        line: int,
        results: List[Dict[str, Any]],
        seen: Set[tuple],
    ) -> None:
        sink_patterns = [
            ("Fetch_Destination", r"\bfetch\s*\(\s*(['\"`])(?P<dest>(?:\\.|(?!\1).)*)\1"),
            ("XMLHttpRequest_Destination", r"\.open\s*\(\s*(['\"`])(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\1\s*,\s*(['\"`])(?P<dest>(?:\\.|(?!\2).)*)\2"),
            ("WebSocket_Destination", r"\bnew\s+WebSocket\s*\(\s*(['\"`])(?P<dest>(?:\\.|(?!\1).)*)\1"),
            ("Beacon_Destination", r"\bnavigator\.sendBeacon\s*\(\s*(['\"`])(?P<dest>(?:\\.|(?!\1).)*)\1"),
        ]
        for indicator_type, pattern in sink_patterns:
            for match in re.finditer(pattern, clean_text):
                dest = match.group("dest")
                cls._extract_indicators_from_text(
                    dest, rel_path, line, indicator_type, results, seen
                )

    @classmethod
    def _try_decode_base64(cls, value: str) -> str | None:
        compact = "".join(value.split())
        if len(compact) < 12 or len(compact) > cls.MAX_ENCODED_LENGTH:
            return None
        if not cls.BASE64_CANDIDATE_REGEX.match(compact):
            return None
        padded = compact + ("=" * ((4 - len(compact) % 4) % 4))
        try:
            decoded_bytes = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            return None
        if not decoded_bytes or len(decoded_bytes) > cls.MAX_DECODED_LENGTH:
            return None
        try:
            decoded_text = decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return decoded_text

    @classmethod
    def extract_network_indicators(cls, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        results = []
        seen: Set[tuple] = set()
        parsed_lines = JavaScriptParser.parse_code_lines(code)

        for line_item in parsed_lines:
            line_num = line_item["line"]
            clean_text = line_item["clean"]

            cls._extract_indicators_from_text(
                clean_text, rel_path, line_num, "static_literal", results, seen, include_bare_domains=False
            )
            cls._extract_direct_sink_destinations(
                clean_text, rel_path, line_num, results, seen
            )

        for string_item in JavaScriptParser.extract_string_literals(code):
            cls._extract_indicators_from_text(
                string_item["value"],
                rel_path,
                string_item["line"],
                "string_literal",
                results,
                seen,
                include_bare_domains=True,
            )
            decoded_text = cls._try_decode_base64(string_item["value"])
            if decoded_text is None:
                continue
            before = len(results)
            cls._extract_indicators_from_text(
                decoded_text,
                rel_path,
                string_item["line"],
                "Decoded static endpoint indicator",
                results,
                seen,
                confidence=0.85,
                encoding_type="base64",
            )
            for indicator in results[before:]:
                indicator["decoded_indicator"] = indicator["value"]
                indicator["encoded_value_preview"] = string_item["value"][:80]

        return results

    @classmethod
    def analyze_directory_network(cls, extension_dir: str) -> List[Dict[str, Any]]:
        indicators = []
        for root, _, files in os.walk(extension_dir):
            for file in files:
                if file.endswith((".js", ".html", ".json")):
                    full_path = os.path.join(root, file)
                    if (
                        file.endswith(".json")
                        and file != "manifest.json"
                        and os.path.getsize(full_path) > cls.MAX_NON_MANIFEST_JSON_SCAN_BYTES
                    ):
                        continue
                    rel_path = os.path.relpath(full_path, extension_dir).replace("\\", "/")
                    indicators.extend(cls.extract_network_indicators(full_path, rel_path))
        return indicators

    @classmethod
    def compare_network_drift(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        v1_ind = cls.analyze_directory_network(v1_dir)
        v2_ind = cls.analyze_directory_network(v2_dir)

        v1_values = {i["value"] for i in v1_ind}
        v2_values = {i["value"] for i in v2_ind}

        added_values = v2_values - v1_values
        added_indicators = []
        seen_added = set()
        for indicator in v2_ind:
            value_key = indicator["value"].lower()
            if indicator["value"] in added_values and value_key not in seen_added:
                seen_added.add(value_key)
                added_indicators.append(indicator)

        new_external_destinations = [i for i in added_indicators if not i["is_local"]]
        new_local_destinations = [i for i in added_indicators if i["is_local"]]
        plain_http_additions = [i for i in new_external_destinations if i["is_plain_http"]]
        decoded_static_endpoints = [
            i for i in added_indicators
            if i.get("source") == "Decoded static endpoint indicator"
        ]

        return {
            "v1_network_count": len(v1_ind),
            "v2_network_count": len(v2_ind),
            "v2_indicators": v2_ind,
            "added_indicators": added_indicators,
            "new_external_destinations": new_external_destinations,
            "new_local_destinations": new_local_destinations,
            "plain_http_additions": plain_http_additions,
            "decoded_static_endpoints": decoded_static_endpoints,
            "new_external_count": len(new_external_destinations),
            "new_local_count": len(new_local_destinations),
            "is_network_drift": len(added_indicators) > 0
        }
