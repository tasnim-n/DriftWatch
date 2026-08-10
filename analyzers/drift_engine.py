from typing import Dict, Any
from analyzers.package_analyzer import PackageAnalyzer
from analyzers.manifest_analyzer import ManifestAnalyzer
from analyzers.permission_analyzer import PermissionAnalyzer
from analyzers.host_scope_analyzer import HostScopeAnalyzer
from analyzers.api_analyzer import APIAnalyzer
from analyzers.network_analyzer import NetworkAnalyzer
from analyzers.obfuscation_analyzer import ObfuscationAnalyzer
from analyzers.structure_analyzer import StructureAnalyzer

class DriftEngine:
    """
    Computes absolute security feature vectors for V1 and V2,
    and calculates the comprehensive behavioral drift vector D_t = F(V_t) - F(V_{t-1}).
    Integrates Manifest, Permission, Host Scope, API, Network, Obfuscation, and Structural Code Analyzers.
    """

    @staticmethod
    def _safe_analyzer(name: str, default: Dict[str, Any], errors: Dict[str, str], func):
        try:
            return func()
        except Exception as exc:
            errors[name] = str(exc)
            return default

    @classmethod
    def compute_behavioral_drift(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        pkg_diff = PackageAnalyzer.compare_packages(v1_dir, v2_dir)
        manifest_diff = ManifestAnalyzer.compare_manifests(v1_dir, v2_dir)
        analyzer_errors: Dict[str, str] = {}
        
        perm_diff = PermissionAnalyzer.analyze_permission_drift(
            manifest_diff["v1_permissions"],
            manifest_diff["v2_permissions"]
        )

        host_diff = HostScopeAnalyzer.analyze_host_scope_expansion(
            manifest_diff["v1_hosts"],
            manifest_diff["v2_hosts"]
        )

        api_diff = cls._safe_analyzer("api_analyzer", {
            "v1_api_count": 0,
            "v2_api_count": 0,
            "added_apis": [],
            "retained_apis": [],
            "unique_added_api_names": [],
            "max_added_api_severity": "None",
            "is_api_drift": False,
        }, analyzer_errors, lambda: APIAnalyzer.compare_api_drift(v1_dir, v2_dir))

        network_diff = cls._safe_analyzer("network_analyzer", {
            "v1_network_count": 0,
            "v2_network_count": 0,
            "added_indicators": [],
            "new_external_destinations": [],
            "new_local_destinations": [],
            "plain_http_additions": [],
            "decoded_static_endpoints": [],
            "new_external_count": 0,
            "new_local_count": 0,
            "is_network_drift": False,
        }, analyzer_errors, lambda: NetworkAnalyzer.compare_network_drift(v1_dir, v2_dir))

        obfuscation_diff = cls._safe_analyzer("obfuscation_analyzer", {
            "v1_indicator_count": 0,
            "v2_indicator_count": 0,
            "added_indicators": [],
            "added_obfuscation_score": 0,
            "is_obfuscation_drift": False,
        }, analyzer_errors, lambda: ObfuscationAnalyzer.compare_obfuscation_drift(v1_dir, v2_dir))

        structure_diff = cls._safe_analyzer("structure_analyzer", {
            "v1_function_count": 0,
            "v2_function_count": 0,
            "added_functions": [],
            "added_event_listeners": [],
            "source_sink_flows": [],
            "is_structural_drift": False,
        }, analyzer_errors, lambda: StructureAnalyzer.compare_structural_drift(v1_dir, v2_dir))

        # Feature Vector F(V1)
        f_v1 = {
            "permission_count": len(manifest_diff["v1_permissions"]),
            "host_count": len(manifest_diff["v1_hosts"]),
            "file_count": pkg_diff["v1_file_count"],
            "total_size_bytes": pkg_diff["v1_total_size"],
            "has_global_host": host_diff["v1_has_global"],
            "max_host_scope_score": host_diff["v1_max_scope_score"],
            "api_count": api_diff["v1_api_count"],
            "network_count": network_diff["v1_network_count"],
            "obfuscation_count": obfuscation_diff["v1_indicator_count"],
            "function_count": structure_diff["v1_function_count"]
        }

        # Feature Vector F(V2)
        f_v2 = {
            "permission_count": len(manifest_diff["v2_permissions"]),
            "host_count": len(manifest_diff["v2_hosts"]),
            "file_count": pkg_diff["v2_file_count"],
            "total_size_bytes": pkg_diff["v2_total_size"],
            "has_global_host": host_diff["v2_has_global"],
            "max_host_scope_score": host_diff["v2_max_scope_score"],
            "api_count": api_diff["v2_api_count"],
            "network_count": network_diff["v2_network_count"],
            "obfuscation_count": obfuscation_diff["v2_indicator_count"],
            "function_count": structure_diff["v2_function_count"]
        }

        # Differential Vector D_t
        drift_vector = {
            "added_permission_count": len(perm_diff["added_permissions"]),
            "removed_permission_count": len(perm_diff["removed_permissions"]),
            "added_permission_risk_score": perm_diff["added_permission_risk_score"],
            "added_host_count": len(host_diff["added_hosts"]),
            "global_host_expansion": 1 if host_diff["global_expansion"] else 0,
            "host_scope_score_delta": host_diff["scope_score_delta"],
            "added_file_count": len(pkg_diff["added_files"]),
            "modified_file_count": len(pkg_diff["modified_files"]),
            "size_delta_bytes": pkg_diff["size_delta"],
            "background_script_added": 1 if manifest_diff["background_added"] else 0,
            "background_script_changed": 1 if manifest_diff["background_changed"] else 0,
            "content_scripts_changed": 1 if manifest_diff["content_scripts_changed"] else 0,
            "added_api_count": len(api_diff["added_apis"]),
            "new_external_network_count": network_diff["new_external_count"],
            "plain_http_addition_count": len(network_diff["plain_http_additions"]),
            "added_obfuscation_score": obfuscation_diff["added_obfuscation_score"],
            "added_function_count": len(structure_diff["added_functions"]),
            "source_sink_flow_count": len(structure_diff["source_sink_flows"])
        }

        return {
            "extension_name": manifest_diff["v2_name"],
            "v1_version": manifest_diff["v1_version"],
            "v2_version": manifest_diff["v2_version"],
            "f_v1": f_v1,
            "f_v2": f_v2,
            "drift_vector": drift_vector,
            "pkg_diff": pkg_diff,
            "manifest_diff": manifest_diff,
            "perm_diff": perm_diff,
            "host_diff": host_diff,
            "api_diff": api_diff,
            "network_diff": network_diff,
            "obfuscation_diff": obfuscation_diff,
            "structure_diff": structure_diff,
            "analyzer_errors": analyzer_errors
        }
