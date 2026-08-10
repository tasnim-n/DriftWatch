import os
import zipfile
import hashlib
import shutil
import uuid
from typing import Dict, Any, List, Tuple
from app.core.config import settings

class SecurityException(Exception):
    """Custom exception raised during security validation failures."""
    pass

class SecureExtractor:
    """
    Secure archive unpacking sandbox.
    Protects against:
    - Zip-Slip (Path Traversal)
    - Zip Bomb (Decompression DoS: file count, total size, compression ratio caps)
    - Symlink exploitation
    - Large single file abuse
    """
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 digest of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def calculate_bytes_hash(data: bytes) -> str:
        """Calculate SHA-256 digest of bytes."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def validate_and_extract_zip(cls, zip_path: str, extract_to: str) -> Dict[str, Any]:
        """
        Safely unpack zip file to extract_to target folder while applying security checks.
        """
        if not os.path.exists(zip_path):
            raise SecurityException(f"Zip file does not exist: {zip_path}")
            
        file_size = os.path.getsize(zip_path)
        max_upload_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_upload_bytes:
            raise SecurityException(f"Uploaded zip exceeds max size limit of {settings.MAX_UPLOAD_SIZE_MB} MB")

        if not zipfile.is_zipfile(zip_path):
            raise SecurityException("Invalid zip archive format.")

        total_uncompressed_size = 0
        total_files = 0
        target_dir_abs = os.path.abspath(extract_to)

        os.makedirs(target_dir_abs, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            infolist = zf.infolist()
            total_files = len(infolist)

            if total_files > settings.MAX_FILE_COUNT:
                raise SecurityException(f"Archive exceeds maximum file count limit ({settings.MAX_FILE_COUNT} files)")

            # Check uncompressed size and compression ratio upfront
            for info in infolist:
                total_uncompressed_size += info.file_size
                
                # Check compression ratio for individual file
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > settings.MAX_COMPRESSION_RATIO:
                        raise SecurityException(f"Zip bomb pattern detected: high compression ratio ({ratio:.1f}x) for file {info.filename}")

            max_extracted_bytes = settings.MAX_EXTRACTED_SIZE_MB * 1024 * 1024
            if total_uncompressed_size > max_extracted_bytes:
                raise SecurityException(f"Archive uncompressed size ({total_uncompressed_size / (1024*1024):.1f} MB) exceeds maximum allowed limit ({settings.MAX_EXTRACTED_SIZE_MB} MB)")

            # Extract with path traversal prevention
            for info in infolist:
                # Disallow symlinks
                # External attributes high 16 bits contain unix file mode
                mode = info.external_attr >> 16
                if mode & 0o120000 == 0o120000:
                    raise SecurityException(f"Symbolic link detected and blocked: {info.filename}")

                # Path traversal check (Zip-Slip)
                dest_path = os.path.abspath(os.path.join(target_dir_abs, info.filename))
                if not dest_path.startswith(target_dir_abs + os.sep) and dest_path != target_dir_abs:
                    raise SecurityException(f"Path traversal attack detected (Zip-Slip): {info.filename}")

                zf.extract(info, target_dir_abs)

        archive_hash = cls.calculate_file_hash(zip_path)

        return {
            "archive_hash": archive_hash,
            "archive_size": file_size,
            "extracted_path": target_dir_abs,
            "total_files": total_files,
            "total_uncompressed_size": total_uncompressed_size
        }

    @staticmethod
    def cleanup_directory(dir_path: str):
        """Remove temporary extraction workspace safely."""
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)
