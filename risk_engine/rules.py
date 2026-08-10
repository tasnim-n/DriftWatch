from typing import Dict, Any, List

class RuleRegistry:
    """
    Evaluates rule combinations on the complete behavioral drift vector.
    Triggers high/critical findings for dangerous compound behaviors.
    """

    @classmethod
    def evaluate_rules(cls, drift_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered_rules = []

        perm_diff = drift_data["perm_diff"]
        host_diff = drift_data["host_diff"]
        manifest_diff = drift_data["manifest_diff"]
        pkg_diff = drift_data["pkg_diff"]
        api_diff = drift_data.get("api_diff", {})
        network_diff = drift_data.get("network_diff", {})
        obfuscation_diff = drift_data.get("obfuscation_diff", {})
        structure_diff = drift_data.get("structure_diff", {})

        added_perms = set(perm_diff["added_permissions"])

        # Rule 1: Sensitive Source-to-Sink Heuristic Pattern
        flows = structure_diff.get("source_sink_flows", [])
        if flows:
            triggered_rules.append({
                "rule_id": "RULE_CRITICAL_SOURCE_SINK_HEURISTIC",
                "title": "Sensitive Source-to-Sink Heuristic Indicator",
                "severity": "Critical",
                "score_weight": 0,
                "score_category": "structural",
                "evidence": f"Code heuristic identified sensitive source APIs ({', '.join(flows[0]['sources'])}) in the same file as outbound sinks ({', '.join(flows[0]['sinks'])}). This is not confirmed exfiltration.",
                "recommendation": "Manually audit the file and verify whether sensitive data can reach outbound communication."
            })

        # Rule 2: Global Host Expansion + Sensitive Permission Creep
        if host_diff["global_expansion"] and ("cookies" in added_perms or "history" in added_perms or "scripting" in added_perms):
            triggered_rules.append({
                "rule_id": "RULE_CRITICAL_GLOBAL_SENSITIVE_CREEP",
                "title": "Global Host Expansion with Critical Permission Creep",
                "severity": "Critical",
                "score_weight": 15,
                "score_category": "combination",
                "evidence": f"The update expanded host access to global wildcard (<all_urls>) while adding critical permissions: {', '.join(added_perms & {'cookies', 'history', 'scripting'})}.",
                "recommendation": "Block update immediately. High risk of authentication session theft or user activity tracking across all sites."
            })

        # Rule 3: Obfuscation / Dynamic Code Introduced
        if obfuscation_diff.get("added_obfuscation_score", 0) > 0:
            score = obfuscation_diff["added_obfuscation_score"]
            triggered_rules.append({
                "rule_id": "RULE_HIGH_OBFUSCATION_INTRODUCED",
                "title": "Dynamic Code Evaluation or String Obfuscation Introduced",
                "severity": "High" if score < 30 else "Critical",
                "score_weight": 0,
                "score_category": "obfuscation",
                "evidence": f"The update introduced {len(obfuscation_diff['added_indicators'])} dynamic code / obfuscation indicators (e.g. eval, new Function, high entropy strings).",
                "recommendation": "Inspect obfuscated code locations or demand non-minified source for manual review."
            })

        # Rule 4: New External Network Endpoint Introduced
        new_ext = network_diff.get("new_external_destinations", [])
        if new_ext:
            urls = [i["value"] for i in new_ext[:3]]
            triggered_rules.append({
                "rule_id": "RULE_HIGH_NEW_EXTERNAL_NETWORK",
                "title": "New External Network Destinations Introduced",
                "severity": "High",
                "score_weight": 0,
                "score_category": "network",
                "evidence": f"The update introduced communication with new external destinations: {', '.join(urls)}.",
                "recommendation": "Audit external host endpoints for reputation and privacy compliance."
            })

        # Rule 5: Critical Permission Added
        critical_added = added_perms & {"cookies", "history", "webRequest", "webRequestBlocking", "debugger", "scripting", "nativeMessaging", "proxy"}
        if critical_added:
            triggered_rules.append({
                "rule_id": "RULE_CRITICAL_PERM_ADDED",
                "title": "Critical Browser Privileges Introduced",
                "severity": "Critical",
                "score_weight": 0,
                "score_category": "permissions",
                "evidence": f"Added dangerous high-risk browser capabilities: {', '.join(critical_added)}.",
                "recommendation": "Conduct deep security review of added background workers and script files."
            })

        # Rule 6: Global Host Expansion Alone
        elif host_diff["global_expansion"]:
            triggered_rules.append({
                "rule_id": "RULE_HIGH_GLOBAL_HOST_EXPANSION",
                "title": "Unrestricted Webpage Access Expansion",
                "severity": "High",
                "score_weight": 0,
                "score_category": "host",
                "evidence": "Host permissions expanded from specific domains to global webpage access (<all_urls>).",
                "recommendation": "Require developer justification for why broad webpage access is required."
            })

        # Rule 7: New Background Service Worker
        if manifest_diff["background_added"]:
            triggered_rules.append({
                "rule_id": "RULE_MODERATE_NEW_BACKGROUND_WORKER",
                "title": "Background Service Worker Introduced",
                "severity": "Moderate",
                "score_weight": 5,
                "score_category": "combination",
                "evidence": "The update introduced a new background service worker script that executes persistently.",
                "recommendation": "Audit background script event listeners and network fetch requests."
            })

        return triggered_rules
