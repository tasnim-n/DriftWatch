from typing import Dict, Any, List

class ExplanationGenerator:
    """
    Generates human-readable finding descriptions, evidence chains, line-level attributions,
    and analyst recommendations across all analysis modules.
    """

    @classmethod
    def generate_findings(cls, drift_data: Dict[str, Any], risk_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []

        perm_diff = drift_data["perm_diff"]
        host_diff = drift_data["host_diff"]
        manifest_diff = drift_data["manifest_diff"]
        pkg_diff = drift_data["pkg_diff"]
        api_diff = drift_data.get("api_diff", {})
        network_diff = drift_data.get("network_diff", {})
        obfuscation_diff = drift_data.get("obfuscation_diff", {})
        structure_diff = drift_data.get("structure_diff", {})
        analyzer_errors = drift_data.get("analyzer_errors", {})

        # Finding 1: Source-to-Sink Exfiltration Flows
        flows = structure_diff.get("source_sink_flows", [])
        for flow in flows:
            findings.append({
                "title": f"Sensitive Source-to-Sink Heuristic ({flow['file']})",
                "category": "code_structure",
                "severity": flow["severity"],
                "impact": "Code in this file contains sensitive data sources and outbound sinks. This is a heuristic indicator, not proof of exfiltration.",
                "old_value": "No data flow detected",
                "new_value": flow["pattern"],
                "evidence": f"File '{flow['file']}' contains sources ({', '.join(flow['sources'])}) and sinks ({', '.join(flow['sinks'])}).",
                "recommendation": "Perform manual code audit to determine whether sensitive data can reach outbound communication.",
                "confidence": flow.get("confidence", 0.75)
            })

        # Finding 2: Host Scope Expansion
        if host_diff["is_expanded"]:
            findings.append({
                "title": "Host Access Scope Expansion Detected",
                "category": "host_access",
                "severity": "Critical" if host_diff["global_expansion"] else "High",
                "impact": "The updated version expanded webpage access permissions to read/modify DOM content across additional sites.",
                "old_value": ", ".join(host_diff["v1_hosts"]) if host_diff["v1_hosts"] else "None",
                "new_value": ", ".join(host_diff["v2_hosts"]),
                "evidence": f"Host patterns expanded by {len(host_diff['added_hosts'])} new match patterns. Global wildcard expansion: {host_diff['global_expansion']}.",
                "recommendation": "Verify whether the extension genuinely requires access to all webpage content.",
                "confidence": 0.95
            })

        # Finding 3: Permission Creep
        if perm_diff["is_permission_creep"]:
            findings.append({
                "title": "Permission Creep Detected (New Browser Privileges)",
                "category": "permissions",
                "severity": perm_diff["max_added_severity"],
                "impact": "New permissions grant access to sensitive browser subsystems.",
                "old_value": ", ".join(perm_diff["v1_permissions"]) if perm_diff["v1_permissions"] else "None",
                "new_value": ", ".join(perm_diff["v2_permissions"]),
                "evidence": f"Added permissions: {', '.join(perm_diff['added_permissions'])}.",
                "recommendation": "Review each added permission against developer update release notes.",
                "confidence": 0.95
            })

        # Finding 4: Sensitive API Introductions
        if api_diff.get("added_apis"):
            added = api_diff["added_apis"]
            unique_names = api_diff["unique_added_api_names"]
            sample_api = added[0]
            findings.append({
                "title": f"Newly Introduced Sensitive Browser APIs ({', '.join(unique_names[:3])})",
                "category": "browser_apis",
                "severity": api_diff["max_added_api_severity"],
                "impact": "The updated JavaScript code calls browser APIs that were not used in the previous version.",
                "old_value": f"{api_diff['v1_api_count']} API calls",
                "new_value": f"{api_diff['v2_api_count']} API calls (Added: {', '.join(unique_names)})",
                "evidence": f"First call detected in {sample_api['file']} at line {sample_api['line']}: '{sample_api['snippet']}'.",
                "recommendation": "Inspect source code lines calling newly added browser APIs.",
                "confidence": 0.95
            })

        # Finding 5: New External Network Destinations
        new_ext = network_diff.get("new_external_destinations", [])
        if new_ext:
            sample_net = new_ext[0]
            findings.append({
                "title": f"New External Network Destinations Detected ({len(new_ext)} added)",
                "category": "network",
                "severity": "High",
                "impact": "Extension code connects to external web servers not referenced in the previous version.",
                "old_value": f"{network_diff['v1_network_count']} network endpoints",
                "new_value": ", ".join([i["value"] for i in new_ext[:3]]),
                "evidence": f"Destination extracted in {sample_net['file']} at line {sample_net['line']}: '{sample_net['value']}'.",
                "recommendation": "Audit external endpoints for telemetry, tracking, or exfiltration.",
                "confidence": 0.90
            })

        decoded_endpoints = network_diff.get("decoded_static_endpoints", [])
        if decoded_endpoints:
            sample_decoded = decoded_endpoints[0]
            findings.append({
                "title": f"Decoded Static Endpoint Indicator ({len(decoded_endpoints)} found)",
                "category": "network",
                "severity": "Moderate" if sample_decoded.get("is_local") else "High",
                "impact": "A statically decoded encoded string contains a URL, domain, or IP indicator.",
                "old_value": "No decoded endpoint indicator",
                "new_value": sample_decoded["decoded_indicator"],
                "evidence": f"{sample_decoded.get('encoding_type', 'encoded')} string in {sample_decoded['file']} near line {sample_decoded['line']} decoded to '{sample_decoded['decoded_indicator']}'.",
                "recommendation": "Review why the endpoint is encoded and verify whether it is expected telemetry or test infrastructure.",
                "confidence": sample_decoded.get("confidence", 0.85)
            })

        # Finding 6: Obfuscation / Entropy Drift
        if obfuscation_diff.get("added_indicators"):
            added_obf = obfuscation_diff["added_indicators"]
            sample_obf = added_obf[0]
            findings.append({
                "title": f"Dynamic Code Evaluation / Obfuscation Introduced ({len(added_obf)} indicators)",
                "category": "obfuscation",
                "severity": "High",
                "impact": "The update introduced dynamic execution or string obfuscation techniques.",
                "old_value": f"{obfuscation_diff['v1_indicator_count']} indicators",
                "new_value": f"{obfuscation_diff['v2_indicator_count']} indicators",
                "evidence": f"Indicator '{sample_obf['type']}' in {sample_obf['file']} at line {sample_obf['line']}: {sample_obf['description']}.",
                "recommendation": "Request unminified source code to verify dynamic execution behavior.",
                "confidence": 0.90
            })

        # Finding 7: Background Worker Addition
        if manifest_diff["background_added"]:
            findings.append({
                "title": "New Background Service Worker Introduced",
                "category": "background",
                "severity": "Moderate",
                "impact": "A background service worker was introduced to handle background events and extension tasks.",
                "old_value": "No background script",
                "new_value": str(manifest_diff["v2_raw"].get("background", {})),
                "evidence": "Background service worker field added to manifest.json.",
                "recommendation": "Inspect background JavaScript files for automated network requests or data collection.",
                "confidence": 0.90
            })

        for analyzer_name, error in analyzer_errors.items():
            findings.append({
                "title": f"Partial Analysis: {analyzer_name} failed",
                "category": "analysis_error",
                "severity": "Moderate",
                "impact": "One analyzer failed, so the report may be incomplete for that signal category.",
                "old_value": None,
                "new_value": analyzer_name,
                "evidence": error,
                "recommendation": "Review analyzer logs and rerun analysis after fixing the analyzer-specific issue.",
                "confidence": 1.0
            })

        return findings

    @classmethod
    def generate_overall_recommendation(cls, classification: str, findings: List[Dict[str, Any]]) -> str:
        if classification == "Critical":
            return "HOLD FOR MANUAL SECURITY REVIEW: Important security-sensitive behavioral drift was detected, including permission creep, host expansion, sensitive API introductions, or source-to-sink heuristic indicators."
        elif classification == "High":
            return "HOLD FOR MANUAL SECURITY REVIEW: Significant behavioral expansion or new network endpoints detected. Conduct code audit before deployment."
        elif classification == "Moderate":
            return "PROCEED WITH CAUTION: Moderate permission or structural changes detected. Review update release notes."
        else:
            return "LOW REVIEW PRIORITY: No significant security-sensitive behavioral drift was identified by the current static analysis. Standard validation is still recommended before deployment."
