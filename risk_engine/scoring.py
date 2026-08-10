from typing import Dict, Any, List
from risk_engine.rules import RuleRegistry

class RiskScorer:
    """
    Computes normalized risk score (0-100), risk classification (Low, Moderate, High, Critical),
    and confidence scores based on rule weightings and comprehensive feature drift.
    """

    @classmethod
    def calculate_risk_score(cls, drift_data: Dict[str, Any]) -> Dict[str, Any]:
        triggered_rules = RuleRegistry.evaluate_rules(drift_data)

        perm_risk = drift_data["perm_diff"]["added_permission_risk_score"]
        permission_contribution = min(round(perm_risk * 0.45, 1), 25.0)

        host_diff = drift_data["host_diff"]
        if host_diff["global_expansion"]:
            host_contribution = 25.0
        elif host_diff["is_expanded"]:
            host_contribution = min(round(max(host_diff["scope_score_delta"], 0) * 0.25, 1), 15.0)
        else:
            host_contribution = 0.0

        api_diff = drift_data.get("api_diff", {})
        unique_api_count = len(api_diff.get("unique_added_api_names", []))
        api_contribution = min(unique_api_count * 4.0, 15.0) if api_diff.get("is_api_drift") else 0.0

        network_diff = drift_data.get("network_diff", {})
        external_count = len(network_diff.get("new_external_destinations", []))
        local_count = len(network_diff.get("new_local_destinations", []))
        decoded_count = len(network_diff.get("decoded_static_endpoints", []))
        plain_http_count = len(network_diff.get("plain_http_additions", []))
        network_contribution = min(
            (external_count * 8.0) + min(local_count * 1.0, 2.0) + (decoded_count * 3.0) + (plain_http_count * 2.0),
            20.0,
        )

        obfuscation_diff = drift_data.get("obfuscation_diff", {})
        obfuscation_contribution = min(
            round(obfuscation_diff.get("added_obfuscation_score", 0) * 0.5, 1),
            15.0,
        )

        structure_diff = drift_data.get("structure_diff", {})
        structural_contribution = 0.0
        if structure_diff.get("source_sink_flows"):
            structural_contribution += 22.0
        structural_contribution += min(len(structure_diff.get("added_functions", [])) * 1.0, 5.0)
        structural_contribution += min(len(structure_diff.get("added_event_listeners", [])) * 1.0, 3.0)
        structural_contribution = min(structural_contribution, 25.0)

        combination_rules = []
        combination_contribution = 0.0
        for rule in triggered_rules:
            if rule.get("score_category") == "combination":
                weight = float(rule.get("score_weight", 0))
                combination_contribution += weight
                combination_rules.append({
                    "rule_id": rule["rule_id"],
                    "title": rule["title"],
                    "contribution": weight,
                })

        combination_contribution = min(combination_contribution, 20.0)

        breakdown = {
            "permission_contribution": permission_contribution,
            "host_contribution": host_contribution,
            "api_contribution": api_contribution,
            "network_contribution": network_contribution,
            "obfuscation_contribution": obfuscation_contribution,
            "structural_contribution": structural_contribution,
            "combination_contribution": combination_contribution,
            "combination_rules": combination_rules,
        }

        raw_score = sum(value for key, value in breakdown.items() if key.endswith("_contribution"))

        # Clamp normalized score between 0 and 100
        final_score = min(max(round(raw_score, 1), 0.0), 100.0)

        # Determine Classification
        if final_score >= 65.0:
            classification = "Critical"
        elif final_score >= 40.0:
            classification = "High"
        elif final_score >= 15.0:
            classification = "Moderate"
        else:
            classification = "Low"

        expected_optional_analyzers = [
            "api_analyzer",
            "network_analyzer",
            "obfuscation_analyzer",
            "structure_analyzer",
        ]
        analyzer_errors = drift_data.get("analyzer_errors", {})
        failed_analyzers = [
            name for name in expected_optional_analyzers
            if name in analyzer_errors
        ]
        succeeded_analyzers = [
            name for name in expected_optional_analyzers
            if name not in analyzer_errors
        ]
        confidence_score = round(
            len(succeeded_analyzers) / len(expected_optional_analyzers),
            2,
        )
        confidence_breakdown = {
            "meaning": "Static-analysis completeness score; not a malware probability.",
            "formula": "successful_optional_phase2_analyzers / expected_optional_phase2_analyzers",
            "expected_analyzers": expected_optional_analyzers,
            "succeeded_analyzers": succeeded_analyzers,
            "failed_analyzers": failed_analyzers,
        }

        return {
            "risk_score": final_score,
            "risk_classification": classification,
            "confidence_score": confidence_score,
            "triggered_rules": triggered_rules,
            "score_breakdown": breakdown,
            "confidence_breakdown": confidence_breakdown,
            "raw_score_before_cap": round(raw_score, 1)
        }
