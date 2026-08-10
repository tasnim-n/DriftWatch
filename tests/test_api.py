import os
import io

def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "DriftWatch" in response.text
    assert "New Differential Audit" in response.text

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
    assert "Critical Risk" in report_resp.text
    assert "Quick Note Safe" in report_resp.text

    # Test JSON API
    api_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["risk_classification"] == "Critical"
    assert data["permission_drift_count"] == 2
    assert data["host_scope_expanded"] == 1
    assert data["score_breakdown"]["permission_contribution"] > 0
    assert data["score_breakdown"]["host_contribution"] > 0

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

    # Test HTML report for benign update
    report_resp = client.get(report_url)
    assert report_resp.status_code == 200
    assert "Low Risk" in report_resp.text or "Moderate Risk" in report_resp.text
    assert "Critical Risk" not in report_resp.text

    # Test JSON API for benign update
    api_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["risk_classification"] in ["Low", "Moderate"]
    assert data["permission_drift_count"] == 0
    assert data["host_scope_expanded"] == 0

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
