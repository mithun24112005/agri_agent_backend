"""
Durable Storage Manager & Retention Lifecycle (Phase 5)
Provides durable UUID storage key abstractions (img_UUID) instead of raw absolute disk paths,
and provides automated 30-day retention cleanup.
"""

import time
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_KEY_REGEX = re.compile(r"^img_[0-9a-fA-F]{32}$")


class StorageManager:
    """Manages durable image keys, file path mapping, and retention policies."""

    def __init__(self, base_dir: Path = UPLOAD_DIR):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_image_key(self) -> str:
        """Generate a random unique storage key (e.g. img_7a8b9c...)."""
        return f"img_{uuid4().hex}"

    def get_image_path_from_key(self, image_key: str) -> Optional[Path]:
        """
        Resolve an abstract image_key to its real physical file path.
        Prevents directory traversal and rejects invalid keys.
        """
        if not image_key or not isinstance(image_key, str):
            return None

        # Key must match expected format
        clean_key = image_key.strip()
        if not IMAGE_KEY_REGEX.match(clean_key):
            # Allow fallback for filenames already using UUID format
            hex_part = clean_key.replace("img_", "").split(".")[0]
            if len(hex_part) != 32:
                return None
        else:
            hex_part = clean_key.replace("img_", "")

        # Look for existing files matching hex_part
        for ext in [".jpg", ".png", ".jpeg"]:
            candidate = self.base_dir / f"{hex_part}{ext}"
            if candidate.exists() and str(candidate.resolve()).startswith(str(self.base_dir)):
                return candidate

        return None

    def store_bytes(self, data: bytes, suffix: str = ".jpg") -> str:
        """Store raw bytes securely and return its abstract image_key."""
        key = self.generate_image_key()
        hex_id = key.replace("img_", "")
        dest = self.base_dir / f"{hex_id}{suffix}"

        # Prevent traversal
        if not str(dest.resolve()).startswith(str(self.base_dir)):
            raise ValueError("Path traversal violation")

        with open(dest, "wb") as f:
            f.write(data)

        return key

    def delete_by_key(self, image_key: str) -> bool:
        """Delete an image by its abstract key."""
        path = self.get_image_path_from_key(image_key)
        if path and path.exists():
            try:
                path.unlink()
                return True
            except OSError:
                return False
        return False

    def cleanup_expired_images(self, max_age_days: int = 30) -> int:
        """
        Retention policy: Delete files in upload directory older than max_age_days.
        Returns the number of deleted files.
        """
        deleted_count = 0
        cutoff_seconds = time.time() - (max_age_days * 86400)

        for file_path in self.base_dir.glob("*.*"):
            if file_path.is_file():
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < cutoff_seconds:
                        file_path.unlink()
                        deleted_count += 1
                except (OSError, PermissionError) as e:
                    print(f"[STORAGE RETENTION] Error deleting {file_path.name}: {e}")

        return deleted_count


storage_manager = StorageManager()

