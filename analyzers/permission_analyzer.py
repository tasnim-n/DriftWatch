from typing import Dict, Any, List, Set

class PermissionAnalyzer:
    """
    Categorizes permissions into risk levels and identifies permission creep.
    """

    PERMISSION_RISK_MAP = {
        # Critical permissions: high abuse potential for exfiltration, interception, session theft
        "cookies": {"level": "Critical", "score": 25, "desc": "Access to HTTP cookies across domains. Can steal authentication tokens."},
        "history": {"level": "Critical", "score": 25, "desc": "Access to complete browsing history and search activity."},
        "webRequest": {"level": "Critical", "score": 25, "desc": "Interception and inspection of live HTTP requests."},
        "webRequestBlocking": {"level": "Critical", "score": 30, "desc": "Ability to block, modify, or inject headers into live HTTP requests."},
        "debugger": {"level": "Critical", "score": 30, "desc": "Attaches DevTools debugger; full control over JS execution and memory."},
        "scripting": {"level": "Critical", "score": 25, "desc": "Executes arbitrary JavaScript in any target tab."},
        "nativeMessaging": {"level": "Critical", "score": 30, "desc": "Communicates with native binary applications installed on host machine."},
        "proxy": {"level": "Critical", "score": 25, "desc": "Reroutes all browser traffic through custom proxy servers."},
        "privacy": {"level": "Critical", "score": 20, "desc": "Modifies browser security and privacy settings."},

        # High risk permissions
        "tabs": {"level": "High", "score": 15, "desc": "Reads open tab URLs, titles, and screenshot frame captures."},
        "downloads": {"level": "High", "score": 15, "desc": "Initiates and manages background file downloads to disk."},
        "browsingData": {"level": "High", "score": 15, "desc": "Clears or modifies browser caches, history, and stored credentials."},
        "management": {"level": "High", "score": 15, "desc": "Manages, enables, or disables other installed browser extensions."},
        "clipboardRead": {"level": "High", "score": 15, "desc": "Reads sensitive plain-text or HTML data copied to clipboard."},
        "clipboardWrite": {"level": "High", "score": 10, "desc": "Writes modified text or links directly to system clipboard."},
        "geolocation": {"level": "High", "score": 15, "desc": "Reads user's precise physical geographic position."},

        # Moderate risk permissions
        "storage": {"level": "Moderate", "score": 5, "desc": "Stores extension settings and offline persistent data."},
        "activeTab": {"level": "Moderate", "score": 5, "desc": "Temporary user-initiated access to current tab upon action click."},
        "notifications": {"level": "Moderate", "score": 5, "desc": "Displays desktop banner notifications to user."},
        "contextMenus": {"level": "Moderate", "score": 5, "desc": "Adds custom options to browser right-click context menu."},
        "unlimitedStorage": {"level": "Moderate", "score": 5, "desc": "Bypasses local client storage quotas."},

        # Informational / Low risk permissions
        "alarms": {"level": "Low", "score": 2, "desc": "Schedules periodic timer events."},
        "idle": {"level": "Low", "score": 2, "desc": "Detects machine idle state."},
        "offscreen": {"level": "Moderate", "score": 10, "desc": "Runs offscreen DOM documents in Manifest V3 background."}
    }

    @classmethod
    def analyze_permission_drift(cls, v1_perms: List[str], v2_perms: List[str]) -> Dict[str, Any]:
        p1_set = set(v1_perms or [])
        p2_set = set(v2_perms or [])

        added = sorted(list(p2_set - p1_set))
        removed = sorted(list(p1_set - p2_set))
        retained = sorted(list(p1_set & p2_set))

        added_details = []
        added_risk_score = 0
        max_added_severity = "Low"

        severity_rank = {"Low": 1, "Moderate": 2, "High": 3, "Critical": 4}

        for perm in added:
            info = cls.PERMISSION_RISK_MAP.get(perm, {"level": "Moderate", "score": 10, "desc": "Custom or unrecognized API permission."})
            added_details.append({
                "permission": perm,
                "level": info["level"],
                "score": info["score"],
                "description": info["desc"]
            })
            added_risk_score += info["score"]
            
            if severity_rank.get(info["level"], 1) > severity_rank.get(max_added_severity, 1):
                max_added_severity = info["level"]

        return {
            "v1_permissions": sorted(list(p1_set)),
            "v2_permissions": sorted(list(p2_set)),
            "added_permissions": added,
            "removed_permissions": removed,
            "retained_permissions": retained,
            "added_permission_details": added_details,
            "added_permission_risk_score": added_risk_score,
            "max_added_severity": max_added_severity if added else "None",
            "is_permission_creep": len(added) > 0
        }
