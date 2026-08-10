from typing import List, Dict, Any, Set
import re

class HostScopeAnalyzer:
    """
    Evaluates host pattern expansion across versions.
    Models webpage access expansion from single domain/path to wildcards and <all_urls>.
    """

    GLOBAL_WILDCARDS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*"}

    @classmethod
    def classify_host_pattern(cls, pattern: str) -> Dict[str, Any]:
        p = pattern.strip()
        if p in cls.GLOBAL_WILDCARDS:
            return {"pattern": p, "scope": "Global", "score": 100, "description": "Unrestricted access to all websites."}
        
        if p.startswith("*://*") or p.startswith("http://*") or p.startswith("https://*"):
            return {"pattern": p, "scope": "Global Wildcard", "score": 90, "description": "Access to all domains under HTTP/HTTPS."}

        if ".*" in p or "*." in p:
            return {"pattern": p, "scope": "Domain Wildcard", "score": 50, "description": "Access to all subdomains of a domain."}

        return {"pattern": p, "scope": "Specific Host", "score": 10, "description": "Access restricted to specific domain or path."}

    @classmethod
    def analyze_host_scope_expansion(cls, v1_hosts: List[str], v2_hosts: List[str]) -> Dict[str, Any]:
        h1_set = set(v1_hosts or [])
        h2_set = set(v2_hosts or [])

        added = sorted(list(h2_set - h1_set))
        removed = sorted(list(h1_set - h2_set))

        v1_has_global = any(h in cls.GLOBAL_WILDCARDS for h in h1_set)
        v2_has_global = any(h in cls.GLOBAL_WILDCARDS for h in h2_set)

        global_expansion = (not v1_has_global) and v2_has_global

        v1_max_score = max([cls.classify_host_pattern(h)["score"] for h in h1_set], default=0)
        v2_max_score = max([cls.classify_host_pattern(h)["score"] for h in h2_set], default=0)

        scope_score_delta = v2_max_score - v1_max_score

        added_classified = [cls.classify_host_pattern(h) for h in added]

        is_expanded = (scope_score_delta > 0) or (len(added) > 0 and not v1_has_global)

        return {
            "v1_hosts": sorted(list(h1_set)),
            "v2_hosts": sorted(list(h2_set)),
            "added_hosts": added,
            "removed_hosts": removed,
            "added_classified": added_classified,
            "v1_has_global": v1_has_global,
            "v2_has_global": v2_has_global,
            "global_expansion": global_expansion,
            "v1_max_scope_score": v1_max_score,
            "v2_max_scope_score": v2_max_score,
            "scope_score_delta": scope_score_delta,
            "is_expanded": is_expanded
        }
