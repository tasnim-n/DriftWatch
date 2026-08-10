import json
import os
from typing import Dict, Any, List

class ManifestAnalyzer:
    """
    Parses manifest.json files (V2 and V3) and detects differential metadata/configuration changes.
    """

    @staticmethod
    def load_manifest(extension_dir: str) -> Dict[str, Any]:
        manifest_path = os.path.join(extension_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"manifest.json missing in directory: {extension_dir}")
        
        with open(manifest_path, "r", encoding="utf-8", errors="ignore") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in manifest.json: {str(e)}")

    @classmethod
    def _extract_permissions_and_hosts(cls, manifest: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Extract permissions and host permissions according to Manifest V2/V3 spec."""
        mv = manifest.get("manifest_version", 2)
        raw_perms = manifest.get("permissions", [])
        
        permissions = []
        hosts = []

        for item in raw_perms:
            if isinstance(item, str):
                if "://" in item or item in ["<all_urls>"]:
                    hosts.append(item)
                else:
                    permissions.append(item)

        # Manifest V3 explicitly separates host_permissions
        if mv >= 3:
            raw_host_perms = manifest.get("host_permissions", [])
            for item in raw_host_perms:
                if isinstance(item, str) and item not in hosts:
                    hosts.append(item)

        return permissions, hosts

    @classmethod
    def compare_manifests(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        m1 = cls.load_manifest(v1_dir)
        m2 = cls.load_manifest(v2_dir)

        m1_perms, m1_hosts = cls._extract_permissions_and_hosts(m1)
        m2_perms, m2_hosts = cls._extract_permissions_and_hosts(m2)

        # Background script / service worker check
        m1_bg = m1.get("background", {})
        m2_bg = m2.get("background", {})

        bg_changed = m1_bg != m2_bg
        bg_added = (not m1_bg) and bool(m2_bg)

        # Content scripts
        m1_cs = m1.get("content_scripts", [])
        m2_cs = m2.get("content_scripts", [])
        cs_changed = m1_cs != m2_cs

        # CSP check
        m1_csp = m1.get("content_security_policy", "")
        m2_csp = m2.get("content_security_policy", "")
        csp_changed = m1_csp != m2_csp

        return {
            "v1_name": m1.get("name", "Unknown Extension"),
            "v2_name": m2.get("name", "Unknown Extension"),
            "v1_version": str(m1.get("version", "1.0")),
            "v2_version": str(m2.get("version", "1.0")),
            "v1_manifest_version": m1.get("manifest_version", 2),
            "v2_manifest_version": m2.get("manifest_version", 2),
            "v1_permissions": m1_perms,
            "v2_permissions": m2_perms,
            "v1_hosts": m1_hosts,
            "v2_hosts": m2_hosts,
            "background_changed": bg_changed,
            "background_added": bg_added,
            "content_scripts_changed": cs_changed,
            "csp_changed": csp_changed,
            "v1_raw": m1,
            "v2_raw": m2
        }
