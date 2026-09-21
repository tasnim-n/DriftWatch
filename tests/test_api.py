import os
import io

def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "DriftWatch" in response.text
    assert "New Differential Audit" in response.text
    assert "Upload previous version (V1)" in response.text
    assert "Upload updated version (V2)" in response.text
    assert "DriftWatch compares their static security behaviour" in response.text
    assert "Extension JavaScript is never executed" in response.text

def test_full_risky_analysis_workflow(client):
    v1_zip = "samples/v1_safe_note.zip"
    v2_zip = "samples/v2_risky_note.zip"

    assert os.path.exists(v1_zip), "v1_safe_note.zip sample missing"
    assert os.path.exists(v2_zip), "v2_risky_note.zip sample missing"

    with open(v1_zip, "rb") as f1, open(v2_zip, "rb") as f2:
        response = client.post(
            "/analyze",
            files={
                "v1_file": ("v1_safe_note.zip", f1, "application/zip"),
                "v2_file": ("v2_risky_note.zip", f2, "application/zip")
            },
            follow_redirects=False
        )

    assert response.status_code == 303
    report_url = response.headers["location"]
    analysis_id = report_url.split("/")[-1]

    # Test HTML report
    report_resp = client.get(report_url)
    assert report_resp.status_code == 200
    assert "Critical Review Priority" in report_resp.text
    assert "Quick Note Safe" in report_resp.text
    assert "HOLD FOR MANUAL SECURITY REVIEW" in report_resp.text
    assert "REJECT / BLOCK UPDATE" not in report_resp.text
    assert "Risk score reflects manual security-review priority, not malware probability." in report_resp.text
    assert "V1 &rarr; V2 Behavioural Change Summary" in report_resp.text
    assert "Evidence Cards" in report_resp.text
    assert "Previous State (V1)" in report_resp.text
    assert "Updated State (V2)" in report_resp.text
    assert "Analyzer Completeness" in report_resp.text
    assert "No research ML prediction contributes to this score." in report_resp.text
    assert "Static endpoint evidence does not prove malicious communication." in report_resp.text
    assert "Heuristic source/sink co-occurrence does not prove exfiltration." in report_resp.text
    assert "Obfuscation/minification indicators do not establish malicious intent." in report_resp.text
    assert "Differential Security Feature Vector: D<sub>t</sub> = F(V<sub>t</sub>) &minus; F(V<sub>t-1</sub>)" in report_resp.text
    assert r"\( D_t = F(V_t)" not in report_resp.text

    # Test JSON API
    api_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["risk_classification"] == "Critical"
    assert data["permission_drift_count"] == 2
    assert data["host_scope_expanded"] == 1
    assert data["score_breakdown"]["permission_contribution"] > 0
    assert data["score_breakdown"]["host_contribution"] > 0
    assert data["recommendation"].startswith("HOLD FOR MANUAL SECURITY REVIEW")

def test_full_benign_analysis_workflow(client):
    v1_zip = "samples/v1_note_benign.zip"
    v2_zip = "samples/v2_note_benign.zip"

    assert os.path.exists(v1_zip), "v1_note_benign.zip sample missing"
    assert os.path.exists(v2_zip), "v2_note_benign.zip sample missing"

    with open(v1_zip, "rb") as f1, open(v2_zip, "rb") as f2:
        response = client.post(
            "/analyze",
            files={
                "v1_file": ("v1_note_benign.zip", f1, "application/zip"),
                "v2_file": ("v2_note_benign.zip", f2, "application/zip")
            },
            follow_redirects=False
        )

    assert response.status_code == 303
    report_url = response.headers["location"]
    analysis_id = report_url.split("/")[-1]
    low_review_priority = (
        "LOW REVIEW PRIORITY: No significant security-sensitive behavioral drift was identified by the current static analysis. "
        "Standard validation is still recommended before deployment."
    )

    # Test HTML report for benign update
    report_resp = client.get(report_url)
    assert report_resp.status_code == 200
    assert "Low Review Priority" in report_resp.text or "Moderate Review Priority" in report_resp.text
    assert "Critical Review Priority" not in report_resp.text
    assert "APPROVED" not in report_resp.text
    assert "safe for deployment" not in report_resp.text
    assert "not a certification that the update is safe" in report_resp.text
    assert "Risk score reflects manual security-review priority, not malware probability." in report_resp.text

    # Test JSON API for benign update
    api_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["risk_classification"] in ["Low", "Moderate"]
    assert data["permission_drift_count"] == 0
    assert data["host_scope_expanded"] == 0
    if data["risk_classification"] == "Low":
        assert data["recommendation"] == low_review_priority

def test_invalid_upload_returns_error_page(client):
    response = client.post(
        "/analyze",
        files={
            "v1_file": ("not-a-zip.zip", io.BytesIO(b"not a zip"), "application/zip"),
            "v2_file": ("not-a-zip.zip", io.BytesIO(b"not a zip"), "application/zip"),
        },
    )

    assert response.status_code == 400
    assert "Security Validation Error" in response.text

def test_missing_manifest_returns_analysis_error_page(client, tmp_path):
    zip_path = tmp_path / "missing_manifest.zip"
    import zipfile

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("popup.js", "console.log('missing manifest');")

    with open("samples/v1_safe_note.zip", "rb") as f1, open(zip_path, "rb") as f2:
        response = client.post(
            "/analyze",
            files={
                "v1_file": ("v1_safe_note.zip", f1, "application/zip"),
                "v2_file": ("missing_manifest.zip", f2, "application/zip"),
            },
        )

    assert response.status_code == 500
    assert "Analysis Execution Error" in response.text
