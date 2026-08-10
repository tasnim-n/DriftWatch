from __future__ import annotations

import csv
import datetime as dt
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from analyzers.api_analyzer import APIAnalyzer
from analyzers.drift_engine import DriftEngine
from analyzers.host_scope_analyzer import HostScopeAnalyzer
from analyzers.manifest_analyzer import ManifestAnalyzer
from analyzers.network_analyzer import NetworkAnalyzer
from analyzers.obfuscation_analyzer import ObfuscationAnalyzer
from analyzers.permission_analyzer import PermissionAnalyzer
from app.core.security import SecureExtractor
from driftbench.schema import DatasetPairRecord
from driftbench.validator import DatasetValidator


FEATURE_SCHEMA_VERSION = "1.0"

BASELINE_PERMISSION_ONLY = "permission_only"
BASELINE_MANIFEST_PERMISSION = "manifest_permission"
BASELINE_LATEST_STATIC = "latest_version_static"
BASELINE_SIMPLE_DIFFERENTIAL = "simple_differential"
BASELINE_FULL_DRIFTWATCH = "full_driftwatch"

BASELINES = [
    BASELINE_PERMISSION_ONLY,
    BASELINE_MANIFEST_PERMISSION,
    BASELINE_LATEST_STATIC,
    BASELINE_SIMPLE_DIFFERENTIAL,
    BASELINE_FULL_DRIFTWATCH,
]

OPTIONAL_ANALYZERS = [
    "api_analyzer",
    "network_analyzer",
    "obfuscation_analyzer",
    "structure_analyzer",
]

METADATA_FIELDS = [
    "record_id",
    "provenance_id",
    "extension_id",
    "extension_name",
    "old_version",
    "new_version",
    "old_timestamp",
    "new_timestamp",
    "label",
    "label_source",
    "label_review_status",
    "label_quality_tier",
    "eligible_for_supervised_training",
    "source",
    "source_type",
    "is_controlled",
    "controlled_mutation_type",
    "functional_category",
    "split",
]

LEAKAGE_FORBIDDEN_FEATURE_TERMS = [
    "label",
    "rationale",
    "risk_score",
    "risk_classification",
    "severity",
    "recommendation",
    "split",
    "path",
    "filename",
    "benign",
    "risky",
    "malicious",
]


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    description: str
    family: str
    data_type: str
    source: str
    representation: str
    baselines: List[str]
    missing_value: str = "0 when available; paired analyzer availability flags distinguish unavailable analysis."
    allowed_range: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "family": self.family,
            "data_type": self.data_type,
            "source": self.source,
            "representation": self.representation,
            "baselines": list(self.baselines),
            "missing_value": self.missing_value,
            "allowed_range": self.allowed_range,
        }


@dataclass
class FeatureRow:
    metadata: Dict[str, Any]
    features: Dict[str, Any]

    def for_baseline(self, baseline: str, schema: Sequence[FeatureDefinition]) -> Dict[str, Any]:
        names = [definition.name for definition in schema if baseline in definition.baselines]
        row = dict(self.metadata)
        for name in names:
            row[name] = self.features[name]
        return row


@dataclass
class ExtractionResult:
    feature_rows: List[FeatureRow]
    schema: List[FeatureDefinition]
    validation_errors: List[str] = field(default_factory=list)
    extraction_warnings: List[str] = field(default_factory=list)
    failed_records: List[Dict[str, str]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.validation_errors and not self.failed_records


def build_feature_schema() -> List[FeatureDefinition]:
    add = _definition
    schema = [
        add("added_permission_count", "Number of permissions added in V2.", "permission_drift", "integer", "permission_analyzer", "count", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("removed_permission_count", "Number of permissions removed in V2.", "permission_drift", "integer", "permission_analyzer", "count", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("added_sensitive_permission_count", "Added permissions with High or Critical sensitivity.", "permission_drift", "integer", "permission_analyzer", "count", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("removed_sensitive_permission_count", "Removed permissions with High or Critical sensitivity.", "permission_drift", "integer", "permission_analyzer", "count", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("permission_risk_delta", "Aggregate sensitivity score of added permissions.", "permission_drift", "number", "permission_analyzer", "continuous", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("critical_permission_added", "Whether any Critical permission was introduced.", "permission_drift", "integer", "permission_analyzer", "binary", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("high_permission_added", "Whether any High permission was introduced.", "permission_drift", "integer", "permission_analyzer", "binary", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("optional_permission_change_count", "Count of optional permission list changes.", "manifest_permission", "integer", "manifest_analyzer", "count", [BASELINE_PERMISSION_ONLY, BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("host_count_delta", "V2 host permission count minus V1 host permission count.", "host_drift", "integer", "host_scope_analyzer", "count", [BASELINE_MANIFEST_PERMISSION, BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("added_host_count", "Count of new host permission patterns.", "host_drift", "integer", "host_scope_analyzer", "count", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("host_scope_score_delta", "Change in max host-scope score.", "host_drift", "number", "host_scope_analyzer", "continuous", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("wildcard_host_introduced", "Whether a wildcard host was introduced.", "host_drift", "integer", "host_scope_analyzer", "binary", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("all_urls_introduced", "Whether all-URLs access was introduced.", "host_drift", "integer", "host_scope_analyzer", "binary", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("content_script_changed", "Whether content scripts changed.", "manifest_permission", "integer", "manifest_analyzer", "binary", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("service_worker_introduced", "Whether a background service worker/script was introduced.", "manifest_permission", "integer", "manifest_analyzer", "binary", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("externally_connectable_changed", "Whether externally_connectable manifest config changed.", "manifest_permission", "integer", "manifest_analyzer", "binary", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("web_accessible_resource_change_count", "Absolute change in web accessible resource count.", "manifest_permission", "integer", "manifest_analyzer", "count", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH]),
        add("csp_changed", "Whether content security policy changed.", "manifest_permission", "integer", "manifest_analyzer", "binary", [BASELINE_MANIFEST_PERMISSION, BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("v2_total_permission_count", "Total V2 permissions.", "latest_static", "integer", "manifest_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_sensitive_permission_count", "Total V2 High/Critical permissions.", "latest_static", "integer", "permission_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_total_host_count", "Total V2 host permissions.", "latest_static", "integer", "manifest_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_wildcard_host_count", "V2 wildcard/global host count.", "latest_static", "integer", "host_scope_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_all_urls_present", "Whether V2 has all-URLs access.", "latest_static", "integer", "host_scope_analyzer", "binary", [BASELINE_LATEST_STATIC], "0/1"),
        add("v2_service_worker_present", "Whether V2 declares a background service worker/script.", "latest_static", "integer", "manifest_analyzer", "binary", [BASELINE_LATEST_STATIC], "0/1"),
        add("v2_sensitive_api_count", "Total sensitive API calls detected in V2.", "latest_static", "integer", "api_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_external_domain_count", "V2 non-local network endpoint count.", "latest_static", "integer", "network_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_http_endpoint_count", "V2 plain HTTP non-local endpoint count.", "latest_static", "integer", "network_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_hardcoded_ip_count", "V2 hardcoded IPv4 count.", "latest_static", "integer", "network_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_obfuscation_indicator_count", "Total V2 obfuscation indicators.", "latest_static", "integer", "obfuscation_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_dynamic_execution_count", "V2 dynamic execution indicator count.", "latest_static", "integer", "obfuscation_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_function_count", "V2 detected function count.", "latest_static", "integer", "structure_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("v2_source_sink_indicator_count", "V2 same-file source-to-sink heuristic count.", "latest_static", "integer", "structure_analyzer", "count", [BASELINE_LATEST_STATIC]),
        add("permission_count_delta", "V2 permission count minus V1 permission count.", "simple_differential", "integer", "manifest_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("file_count_delta", "V2 file count minus V1 file count.", "simple_differential", "integer", "package_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("package_size_delta_bytes", "V2 package size minus V1 package size.", "simple_differential", "integer", "package_analyzer", "continuous", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("js_file_count_delta", "V2 JavaScript file count minus V1 JavaScript file count.", "simple_differential", "integer", "package_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("api_count_delta", "V2 API count minus V1 API count.", "simple_differential", "integer", "api_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("network_destination_count_delta", "V2 network indicator count minus V1 network indicator count.", "simple_differential", "integer", "network_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("obfuscation_count_delta", "V2 obfuscation count minus V1 obfuscation count.", "simple_differential", "integer", "obfuscation_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("function_count_delta", "V2 function count minus V1 function count.", "simple_differential", "integer", "structure_analyzer", "count", [BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH]),
        add("added_api_count", "Unique newly introduced API capabilities.", "api_drift", "integer", "api_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("critical_api_added", "Whether any newly introduced API has Critical severity.", "api_drift", "integer", "api_analyzer", "binary", [BASELINE_FULL_DRIFTWATCH], "0/1"),
        add("new_external_network_count", "New non-local endpoint count.", "network_drift", "integer", "network_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("new_local_network_count", "New local/test endpoint count.", "network_drift", "integer", "network_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("plain_http_addition_count", "New non-local plain HTTP endpoint count.", "network_drift", "integer", "network_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("decoded_endpoint_addition_count", "New bounded decoded static endpoint indicators.", "network_drift", "integer", "network_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("hardcoded_ip_addition_count", "New hardcoded IPv4 indicators.", "network_drift", "integer", "network_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("added_obfuscation_score", "Aggregate score of newly introduced obfuscation indicators.", "obfuscation_drift", "number", "obfuscation_analyzer", "continuous", [BASELINE_FULL_DRIFTWATCH]),
        add("dynamic_execution_added_count", "New dynamic execution indicator count.", "obfuscation_drift", "integer", "obfuscation_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("added_function_count", "New detected functions.", "structural_drift", "integer", "structure_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("added_event_listener_count", "New detected event listeners.", "structural_drift", "integer", "structure_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("source_sink_flow_count", "New same-file source-to-sink heuristic count.", "structural_drift", "integer", "structure_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
        add("modified_file_count", "Modified file count.", "package_drift", "integer", "package_analyzer", "count", [BASELINE_FULL_DRIFTWATCH]),
    ]

    for analyzer in OPTIONAL_ANALYZERS:
        schema.append(add(f"{analyzer}_available", f"Availability flag for {analyzer}.", "analyzer_health", "integer", analyzer, "binary", [BASELINE_LATEST_STATIC, BASELINE_SIMPLE_DIFFERENTIAL, BASELINE_FULL_DRIFTWATCH], "0/1"))

    return schema


def _definition(
    name: str,
    description: str,
    family: str,
    data_type: str,
    source: str,
    representation: str,
    baselines: List[str],
    allowed_range: str | None = None,
) -> FeatureDefinition:
    return FeatureDefinition(
        name=name,
        description=description,
        family=family,
        data_type=data_type,
        source=source,
        representation=representation,
        baselines=baselines,
        allowed_range=allowed_range,
    )


class LeakageError(ValueError):
    pass


class DriftBenchFeatureExtractor:
    def __init__(self, *, base_dir: str | Path = ".", schema: Sequence[FeatureDefinition] | None = None):
        self.base_dir = Path(base_dir).resolve()
        self.schema = list(schema or build_feature_schema())
        self.feature_order = [definition.name for definition in self.schema]
        self._assert_schema_has_no_leakage()

    def extract(self, records: Sequence[DatasetPairRecord]) -> ExtractionResult:
        validation = DatasetValidator.validate_records(records, base_dir=self.base_dir, validate_paths=True)
        if not validation.is_valid:
            return ExtractionResult(
                feature_rows=[],
                schema=self.schema,
                validation_errors=list(validation.errors),
                extraction_warnings=list(validation.warnings),
            )

        rows: List[FeatureRow] = []
        failed_records: List[Dict[str, str]] = []
        warnings = list(validation.warnings)

        for record in records:
            try:
                rows.append(self._extract_one(record))
            except Exception as exc:
                failed_records.append({"record_id": record.pair_id, "error": str(exc)})

        return ExtractionResult(
            feature_rows=rows,
            schema=self.schema,
            validation_errors=[],
            extraction_warnings=warnings,
            failed_records=failed_records,
        )

    def _extract_one(self, record: DatasetPairRecord) -> FeatureRow:
        old_archive = self._resolve_archive_path(record.old_archive_path)
        new_archive = self._resolve_archive_path(record.new_archive_path)

        with tempfile.TemporaryDirectory(prefix="driftbench_features_") as workspace:
            old_dir = os.path.join(workspace, "old")
            new_dir = os.path.join(workspace, "new")
            SecureExtractor.validate_and_extract_zip(str(old_archive), old_dir)
            SecureExtractor.validate_and_extract_zip(str(new_archive), new_dir)
            drift = DriftEngine.compute_behavioral_drift(old_dir, new_dir)
            features = self._build_features(old_dir, new_dir, drift)

        ordered_features = {name: features.get(name, 0) for name in self.feature_order}
        self._assert_row_has_no_leakage(ordered_features)
        return FeatureRow(metadata=self._metadata(record), features=ordered_features)

    def _resolve_archive_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        resolved = path.resolve() if path.is_absolute() else (self.base_dir / path).resolve()
        try:
            resolved.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError(f"archive path escapes DriftBench base directory: {raw_path}") from exc
        if not resolved.exists():
            raise FileNotFoundError(f"archive path does not exist: {raw_path}")
        return resolved

    @staticmethod
    def _metadata(record: DatasetPairRecord) -> Dict[str, Any]:
        return {
            "record_id": record.pair_id,
            "provenance_id": f"{record.provenance.source_type}:{record.pair_id}",
            "extension_id": record.extension_id,
            "extension_name": record.extension_name,
            "old_version": record.old_version,
            "new_version": record.new_version,
            "old_timestamp": record.old_timestamp,
            "new_timestamp": record.new_timestamp,
            "label": record.label,
            "label_source": record.label_source,
            "label_review_status": record.label_review_status,
            "label_quality_tier": record.label_quality_tier,
            "eligible_for_supervised_training": record.eligible_for_supervised_training,
            "source": record.source,
            "source_type": record.provenance.source_type,
            "is_controlled": bool(record.controlled_mutation_type or record.provenance.source_type == "controlled"),
            "controlled_mutation_type": record.controlled_mutation_type,
            "functional_category": record.functional_category,
            "split": record.split,
        }

    def _build_features(self, old_dir: str, new_dir: str, drift: Dict[str, Any]) -> Dict[str, Any]:
        manifest = drift["manifest_diff"]
        perm = drift["perm_diff"]
        host = drift["host_diff"]
        pkg = drift["pkg_diff"]
        api = drift.get("api_diff", {})
        network = drift.get("network_diff", {})
        obfuscation = drift.get("obfuscation_diff", {})
        structure = drift.get("structure_diff", {})
        errors = drift.get("analyzer_errors", {})

        v2_network = [] if "network_analyzer" in errors else network.get("v2_indicators", [])
        v2_obfuscation = [] if "obfuscation_analyzer" in errors else obfuscation.get("v2_indicators", [])
        v2_api = [] if "api_analyzer" in errors else api.get("v2_apis", [])

        added_details = perm.get("added_permission_details", [])
        removed_sensitive = self._sensitive_permissions(perm.get("removed_permissions", []))
        added_sensitive = [item for item in added_details if item.get("level") in {"High", "Critical"}]
        added_hosts = host.get("added_hosts", [])
        v2_hosts = manifest.get("v2_hosts", [])
        v2_permissions = manifest.get("v2_permissions", [])
        v2_raw = manifest.get("v2_raw", {})
        v1_raw = manifest.get("v1_raw", {})
        v2_bg = v2_raw.get("background", {})

        features = {
            "added_permission_count": len(perm.get("added_permissions", [])),
            "removed_permission_count": len(perm.get("removed_permissions", [])),
            "added_sensitive_permission_count": len(added_sensitive),
            "removed_sensitive_permission_count": len(removed_sensitive),
            "permission_risk_delta": perm.get("added_permission_risk_score", 0),
            "critical_permission_added": int(any(item.get("level") == "Critical" for item in added_details)),
            "high_permission_added": int(any(item.get("level") == "High" for item in added_details)),
            "optional_permission_change_count": self._optional_permission_change_count(v1_raw, v2_raw),
            "host_count_delta": len(manifest.get("v2_hosts", [])) - len(manifest.get("v1_hosts", [])),
            "added_host_count": len(added_hosts),
            "host_scope_score_delta": host.get("scope_score_delta", 0),
            "wildcard_host_introduced": int(any("*" in value for value in added_hosts)),
            "all_urls_introduced": int(host.get("global_expansion", False)),
            "content_script_changed": int(manifest.get("content_scripts_changed", False)),
            "service_worker_introduced": int(manifest.get("background_added", False)),
            "externally_connectable_changed": int(v1_raw.get("externally_connectable") != v2_raw.get("externally_connectable")),
            "web_accessible_resource_change_count": abs(self._war_count(v2_raw) - self._war_count(v1_raw)),
            "csp_changed": int(manifest.get("csp_changed", False)),
            "v2_total_permission_count": len(v2_permissions),
            "v2_sensitive_permission_count": len(self._sensitive_permissions(v2_permissions)),
            "v2_total_host_count": len(v2_hosts),
            "v2_wildcard_host_count": sum(1 for value in v2_hosts if "*" in value or value in HostScopeAnalyzer.GLOBAL_WILDCARDS),
            "v2_all_urls_present": int(any(value in HostScopeAnalyzer.GLOBAL_WILDCARDS for value in v2_hosts)),
            "v2_service_worker_present": int(bool(v2_bg)),
            "v2_sensitive_api_count": len(v2_api),
            "v2_external_domain_count": sum(1 for item in v2_network if not item.get("is_local")),
            "v2_http_endpoint_count": sum(1 for item in v2_network if item.get("is_plain_http")),
            "v2_hardcoded_ip_count": sum(1 for item in v2_network if item.get("type") in {"IPv4", "Hardcoded_IP"}),
            "v2_obfuscation_indicator_count": len(v2_obfuscation),
            "v2_dynamic_execution_count": self._dynamic_execution_count(v2_obfuscation),
            "v2_function_count": structure.get("v2_function_count", 0),
            "v2_source_sink_indicator_count": len(structure.get("source_sink_flows", [])),
            "permission_count_delta": len(manifest.get("v2_permissions", [])) - len(manifest.get("v1_permissions", [])),
            "file_count_delta": pkg.get("file_count_delta", 0),
            "package_size_delta_bytes": pkg.get("size_delta", 0),
            "js_file_count_delta": self._js_file_count(new_dir) - self._js_file_count(old_dir),
            "api_count_delta": api.get("v2_api_count", 0) - api.get("v1_api_count", 0),
            "network_destination_count_delta": network.get("v2_network_count", 0) - network.get("v1_network_count", 0),
            "obfuscation_count_delta": obfuscation.get("v2_indicator_count", 0) - obfuscation.get("v1_indicator_count", 0),
            "function_count_delta": structure.get("v2_function_count", 0) - structure.get("v1_function_count", 0),
            "added_api_count": len(api.get("added_apis", [])),
            "critical_api_added": int(api.get("max_added_api_severity") == "Critical"),
            "new_external_network_count": network.get("new_external_count", 0),
            "new_local_network_count": network.get("new_local_count", 0),
            "plain_http_addition_count": len(network.get("plain_http_additions", [])),
            "decoded_endpoint_addition_count": len(network.get("decoded_static_endpoints", [])),
            "hardcoded_ip_addition_count": sum(1 for item in network.get("added_indicators", []) if item.get("type") in {"IPv4", "Hardcoded_IP"}),
            "added_obfuscation_score": obfuscation.get("added_obfuscation_score", 0),
            "dynamic_execution_added_count": self._dynamic_execution_count(obfuscation.get("added_indicators", [])),
            "added_function_count": len(structure.get("added_functions", [])),
            "added_event_listener_count": len(structure.get("added_event_listeners", [])),
            "source_sink_flow_count": len(structure.get("source_sink_flows", [])),
            "modified_file_count": len(pkg.get("modified_files", [])),
        }

        for analyzer in OPTIONAL_ANALYZERS:
            features[f"{analyzer}_available"] = int(analyzer not in errors)

        return features

    @staticmethod
    def _optional_permission_change_count(v1_raw: Dict[str, Any], v2_raw: Dict[str, Any]) -> int:
        v1 = set(v1_raw.get("optional_permissions", []) or [])
        v2 = set(v2_raw.get("optional_permissions", []) or [])
        return len(v2 - v1) + len(v1 - v2)

    @staticmethod
    def _war_count(manifest: Dict[str, Any]) -> int:
        resources = manifest.get("web_accessible_resources", []) or []
        if not isinstance(resources, list):
            return 0
        count = 0
        for item in resources:
            if isinstance(item, dict):
                count += len(item.get("resources", []) or [])
            else:
                count += 1
        return count

    @staticmethod
    def _dynamic_execution_count(indicators: Sequence[Dict[str, Any]]) -> int:
        dynamic_types = {"eval_call", "new_function", "string_timer", "dynamic_script_creation", "dynamic_import", "wasm_usage", "wasm_file"}
        return sum(1 for item in indicators if item.get("type") in dynamic_types)

    @staticmethod
    def _js_file_count(directory: str) -> int:
        total = 0
        for _, _, files in os.walk(directory):
            total += sum(1 for file in files if file.endswith(".js"))
        return total

    @staticmethod
    def _sensitive_permissions(permissions: Sequence[str]) -> List[str]:
        sensitive = []
        for permission in permissions:
            info = PermissionAnalyzer.PERMISSION_RISK_MAP.get(permission, {"level": "Moderate"})
            if info.get("level") in {"High", "Critical"}:
                sensitive.append(permission)
        return sorted(sensitive)

    def _assert_schema_has_no_leakage(self) -> None:
        seen = set()
        for definition in self.schema:
            if definition.name in seen:
                raise LeakageError(f"duplicate feature name: {definition.name}")
            seen.add(definition.name)
            lowered = definition.name.lower()
            for term in LEAKAGE_FORBIDDEN_FEATURE_TERMS:
                if term in lowered:
                    raise LeakageError(f"feature name may leak target or path information: {definition.name}")

    @staticmethod
    def _assert_row_has_no_leakage(features: Dict[str, Any]) -> None:
        for name, value in features.items():
            if isinstance(value, str):
                lowered = value.lower()
                if any(term in lowered for term in ("benign", "risky", "malicious", "samples", "risk_score")):
                    raise LeakageError(f"feature {name} contains path/label-like text")


def write_feature_artifacts(
    result: ExtractionResult,
    output_dir: str | Path,
    *,
    dataset_id: str,
    dataset_version: str,
    generation_timestamp: str | None = None,
    code_version: str | None = None,
    seed: int | None = None,
) -> Dict[str, str]:
    if result.validation_errors or result.failed_records:
        raise ValueError("cannot write artifacts for invalid or failed extraction result")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = generation_timestamp or dt.datetime.now(dt.timezone.utc).isoformat()
    paths: Dict[str, str] = {}

    schema_payload = {
        "driftbench_feature_schema_version": FEATURE_SCHEMA_VERSION,
        "normalization_policy": "Raw interpretable values only. Fit scaling later inside training pipelines using training data only.",
        "features": [definition.to_dict() for definition in result.schema],
    }
    schema_path = output / "feature_schema.json"
    schema_path.write_text(json.dumps(schema_payload, indent=2, sort_keys=True), encoding="utf-8")
    paths["feature_schema"] = str(schema_path)

    for baseline in BASELINES:
        rows = [row.for_baseline(baseline, result.schema) for row in result.feature_rows]
        csv_path = output / f"{baseline}.csv"
        jsonl_path = output / f"{baseline}.jsonl"
        _write_csv(csv_path, rows)
        _write_jsonl(jsonl_path, rows)
        paths[f"{baseline}_csv"] = str(csv_path)
        paths[f"{baseline}_jsonl"] = str(jsonl_path)

    summary = _dataset_summary(result)
    summary_path = output / "dataset_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    paths["dataset_summary"] = str(summary_path)

    manifest = {
        "generation_timestamp": timestamp,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "record_count": len(result.feature_rows),
        "feature_families": sorted({definition.family for definition in result.schema}),
        "baselines": list(BASELINES),
        "source_dataset_identifier": dataset_id,
        "source_dataset_version": dataset_version,
        "code_version": code_version,
        "split_counts": summary["split_counts"],
        "label_counts": summary["label_counts"],
        "extraction_warnings": result.extraction_warnings,
        "failed_records": result.failed_records,
        "deterministic_seed": seed,
    }
    manifest_path = output / "extraction_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    paths["extraction_manifest"] = str(manifest_path)

    return paths


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = list(METADATA_FIELDS)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _dataset_summary(result: ExtractionResult) -> Dict[str, Any]:
    label_counts: Dict[str, int] = {}
    split_counts: Dict[str, int] = {}
    missingness_counts: Dict[str, int] = {}

    for row in result.feature_rows:
        label = row.metadata.get("label") or "unknown"
        split = row.metadata.get("split") or "unsplit"
        label_counts[label] = label_counts.get(label, 0) + 1
        split_counts[split] = split_counts.get(split, 0) + 1
        for analyzer in OPTIONAL_ANALYZERS:
            feature = f"{analyzer}_available"
            if row.features.get(feature) == 0:
                missingness_counts[feature] = missingness_counts.get(feature, 0) + 1

    return {
        "record_count": len(result.feature_rows),
        "label_counts": dict(sorted(label_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "feature_count": len(result.schema),
        "missingness_counts": dict(sorted(missingness_counts.items())),
    }
