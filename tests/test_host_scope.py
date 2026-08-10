from analyzers.host_scope_analyzer import HostScopeAnalyzer

def test_host_scope_global_expansion():
    v1_hosts = ["https://notes.local/*"]
    v2_hosts = ["<all_urls>"]

    res = HostScopeAnalyzer.analyze_host_scope_expansion(v1_hosts, v2_hosts)

    assert res["is_expanded"] is True
    assert res["global_expansion"] is True
    assert res["v1_max_scope_score"] == 10
    assert res["v2_max_scope_score"] == 100
    assert res["scope_score_delta"] == 90
