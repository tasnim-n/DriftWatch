from __future__ import annotations

import base64
import json
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List


class MutationType(str, Enum):
    PERMISSION_EXPANSION = "permission_expansion"
    HOST_EXPANSION = "host_expansion"
    SENSITIVE_API_INTRODUCTION = "sensitive_api_introduction"
    NETWORK_ENDPOINT_INTRODUCTION = "network_endpoint_introduction"
    OBFUSCATION_INTRODUCTION = "obfuscation_introduction"
    BACKGROUND_WORKER_INTRODUCTION = "background_worker_introduction"
    REMOTE_CONFIGURATION_PATTERN = "remote_configuration_pattern"
    SOURCE_TO_SINK_HEURISTIC = "source_to_sink_heuristic"
    GRADUAL_CAPABILITY_EXPANSION = "gradual_capability_expansion"


@dataclass
class MutationSpec:
    mutation_type: MutationType
    output_version: str
    permissions: List[str] = field(default_factory=list)
    host_permissions: List[str] = field(default_factory=list)
    endpoint: str = "http://127.0.0.1:8000/driftbench-controlled"
    notes: List[str] = field(default_factory=list)


class ControlledMutationFramework:
    """Create harmless synthetic extension updates for controlled DriftBench records."""

    @classmethod
    def apply_mutation(cls, source_dir: str | Path, output_dir: str | Path, spec: MutationSpec) -> Dict[str, str]:
        source = Path(source_dir)
        output = Path(output_dir)
        if not source.exists():
            raise FileNotFoundError(f"source extension directory does not exist: {source}")
        if output.exists():
            raise FileExistsError(f"output directory already exists: {output}")

        shutil.copytree(source, output)
        manifest_path = output / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)

        manifest["version"] = spec.output_version
        permissions = list(dict.fromkeys(manifest.get("permissions", []) + spec.permissions))
        hosts = list(dict.fromkeys(manifest.get("host_permissions", []) + spec.host_permissions))
        manifest["permissions"] = permissions
        if hosts:
            manifest["host_permissions"] = hosts

        changed_file = "manifest.json"
        if spec.mutation_type == MutationType.PERMISSION_EXPANSION:
            manifest["permissions"] = list(dict.fromkeys(permissions + ["history"]))
        elif spec.mutation_type == MutationType.HOST_EXPANSION:
            manifest["host_permissions"] = list(dict.fromkeys(hosts + ["<all_urls>"]))
        elif spec.mutation_type == MutationType.BACKGROUND_WORKER_INTRODUCTION:
            changed_file = cls._add_background_worker(output, manifest, cls._background_worker(spec.endpoint))
        elif spec.mutation_type == MutationType.SENSITIVE_API_INTRODUCTION:
            changed_file = cls._add_background_worker(output, manifest, cls._sensitive_api_worker())
            manifest["permissions"] = list(dict.fromkeys(manifest.get("permissions", []) + ["cookies"]))
        elif spec.mutation_type == MutationType.NETWORK_ENDPOINT_INTRODUCTION:
            changed_file = cls._add_background_worker(output, manifest, cls._network_worker(spec.endpoint))
        elif spec.mutation_type == MutationType.OBFUSCATION_INTRODUCTION:
            changed_file = cls._add_background_worker(output, manifest, cls._encoded_worker(spec.endpoint))
        elif spec.mutation_type == MutationType.REMOTE_CONFIGURATION_PATTERN:
            changed_file = cls._add_background_worker(output, manifest, cls._remote_config_worker(spec.endpoint))
        elif spec.mutation_type == MutationType.SOURCE_TO_SINK_HEURISTIC:
            changed_file = cls._add_background_worker(output, manifest, cls._source_sink_worker(spec.endpoint))
            manifest["permissions"] = list(dict.fromkeys(manifest.get("permissions", []) + ["cookies"]))
        elif spec.mutation_type == MutationType.GRADUAL_CAPABILITY_EXPANSION:
            manifest["permissions"] = list(dict.fromkeys(manifest.get("permissions", []) + ["history"]))
            manifest["host_permissions"] = list(dict.fromkeys(manifest.get("host_permissions", []) + ["https://*.example.test/*"]))
            changed_file = cls._add_background_worker(output, manifest, cls._network_worker(spec.endpoint))
        else:
            raise ValueError(f"unsupported mutation type: {spec.mutation_type}")

        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

        return {
            "mutation_type": spec.mutation_type.value,
            "output_dir": str(output),
            "changed_file": changed_file,
            "safety_note": "Synthetic controlled mutation; JavaScript is static sample text and is not executed by DriftWatch.",
        }

    @staticmethod
    def _add_background_worker(output: Path, manifest: Dict, content: str) -> str:
        worker_name = "driftbench_worker.js"
        worker_path = output / worker_name
        worker_path.write_text(content, encoding="utf-8")
        manifest["background"] = {"service_worker": worker_name}
        return worker_name

    @staticmethod
    def _background_worker(endpoint: str) -> str:
        return f"""chrome.runtime.onInstalled.addListener(() => {{
  console.log("Controlled DriftBench worker initialized for {endpoint}");
}});
"""

    @staticmethod
    def _sensitive_api_worker() -> str:
        return """chrome.cookies.getAll({}, (cookies) => {
  console.log("Controlled cookie count", cookies.length);
});
"""

    @staticmethod
    def _network_worker(endpoint: str) -> str:
        return f"""fetch("{endpoint}", {{
  method: "POST",
  body: JSON.stringify({{ controlled: true }})
}}).catch(() => {{}});
"""

    @staticmethod
    def _encoded_worker(endpoint: str) -> str:
        encoded = base64.b64encode(endpoint.encode("utf-8")).decode("ascii")
        return f"""const encodedEndpoint = "{encoded}";
const decodedEndpoint = atob(encodedEndpoint);
console.log("Controlled decoded endpoint", decodedEndpoint);
"""

    @staticmethod
    def _remote_config_worker(endpoint: str) -> str:
        return f"""fetch("{endpoint}/config.json")
  .then((response) => response.json())
  .then((config) => console.log("Controlled config keys", Object.keys(config)))
  .catch(() => {{}});
"""

    @staticmethod
    def _source_sink_worker(endpoint: str) -> str:
        return f"""chrome.cookies.getAll({{}}, (cookies) => {{
  fetch("{endpoint}", {{
    method: "POST",
    body: JSON.stringify({{ cookieCount: cookies.length }})
  }}).catch(() => {{}});
}});
"""
