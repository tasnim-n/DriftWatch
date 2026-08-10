from analyzers.permission_analyzer import PermissionAnalyzer

def test_permission_creep_detection():
    v1_perms = ["storage"]
    v2_perms = ["storage", "cookies", "history"]

    res = PermissionAnalyzer.analyze_permission_drift(v1_perms, v2_perms)

    assert res["is_permission_creep"] is True
    assert res["added_permissions"] == ["cookies", "history"]
    assert res["max_added_severity"] == "Critical"
    assert res["added_permission_risk_score"] == 50 # 25 for cookies + 25 for history
