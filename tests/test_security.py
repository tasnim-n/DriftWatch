import os
import zipfile
import pytest
import tempfile
from app.core.security import SecureExtractor, SecurityException

def test_zip_slip_prevention():
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "malicious_zip_slip.zip")
    extract_target = os.path.join(temp_dir, "extract_target")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "malicious payload")

    with pytest.raises(SecurityException) as exc_info:
        SecureExtractor.validate_and_extract_zip(zip_path, extract_target)

    assert "Path traversal attack detected" in str(exc_info.value)
    shutil_rm(temp_dir)

def test_zip_bomb_file_count_limit():
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "file_count_bomb.zip")
    extract_target = os.path.join(temp_dir, "extract_target")

    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(505):
            zf.writestr(f"file_{i}.txt", "dummy content")

    with pytest.raises(SecurityException) as exc_info:
        SecureExtractor.validate_and_extract_zip(zip_path, extract_target)

    assert "Archive exceeds maximum file count limit" in str(exc_info.value)
    shutil_rm(temp_dir)

def test_valid_zip_extraction():
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "valid.zip")
    extract_target = os.path.join(temp_dir, "extract_target")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", '{"name": "test"}')

    result = SecureExtractor.validate_and_extract_zip(zip_path, extract_target)
    assert result["total_files"] == 1
    assert os.path.exists(os.path.join(extract_target, "manifest.json"))
    shutil_rm(temp_dir)

def shutil_rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)
