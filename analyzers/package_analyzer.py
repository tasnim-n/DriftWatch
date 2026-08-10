import os
import hashlib
from typing import Dict, Any, List, Set

class PackageAnalyzer:
    """
    Analyzes physical package changes between two extracted extension versions.
    Generates file diffs, hash modifications, additions, and file count stats.
    """

    @staticmethod
    def _get_relative_file_map(directory: str) -> Dict[str, Dict[str, Any]]:
        """Map relative file paths to metadata (size, SHA-256 hash)."""
        file_map = {}
        for root, _, files in os.walk(directory):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory).replace("\\", "/")
                
                # Calculate sha256 hash
                sha256 = hashlib.sha256()
                with open(full_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        sha256.update(chunk)
                
                file_map[rel_path] = {
                    "size": os.path.getsize(full_path),
                    "hash": sha256.hexdigest(),
                    "extension": os.path.splitext(file)[1].lower()
                }
        return file_map

    @classmethod
    def compare_packages(cls, v1_dir: str, v2_dir: str) -> Dict[str, Any]:
        v1_files = cls._get_relative_file_map(v1_dir)
        v2_files = cls._get_relative_file_map(v2_dir)

        v1_keys: Set[str] = set(v1_files.keys())
        v2_keys: Set[str] = set(v2_files.keys())

        added_files = sorted(list(v2_keys - v1_keys))
        removed_files = sorted(list(v1_keys - v2_keys))
        common_files = sorted(list(v1_keys & v2_keys))

        modified_files = []
        for file in common_files:
            if v1_files[file]["hash"] != v2_files[file]["hash"]:
                modified_files.append({
                    "path": file,
                    "v1_size": v1_files[file]["size"],
                    "v2_size": v2_files[file]["size"],
                    "v1_hash": v1_files[file]["hash"],
                    "v2_hash": v2_files[file]["hash"]
                })

        # Calculate totals
        v1_total_size = sum(f["size"] for f in v1_files.values())
        v2_total_size = sum(f["size"] for f in v2_files.values())

        return {
            "v1_file_count": len(v1_files),
            "v2_file_count": len(v2_files),
            "v1_total_size": v1_total_size,
            "v2_total_size": v2_total_size,
            "added_files": added_files,
            "removed_files": removed_files,
            "modified_files": modified_files,
            "size_delta": v2_total_size - v1_total_size,
            "file_count_delta": len(v2_files) - len(v1_files)
        }
