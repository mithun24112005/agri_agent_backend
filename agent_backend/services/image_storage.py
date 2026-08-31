"""Durable storage for image attachments referenced by chat checkpoints."""

import base64
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

MAX_IMAGE_BYTES = 5 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "storage" / "uploads"


async def save_uploaded_image(file: UploadFile) -> dict[str, str | int]:
    """Save an approved upload outside the temporary-file lifecycle."""
    content_type = (file.content_type or "").lower()
    suffix = SUPPORTED_IMAGE_TYPES.get(content_type)
    if suffix is None:
        raise ValueError("Please upload a JPEG, PNG, WebP, or GIF image.")

    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise ValueError("The image must be 5 MB or smaller.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    path.write_bytes(contents)
    return {
        "path": str(path),
        "filename": file.filename or f"image{suffix}",
        "content_type": content_type,
        "size": len(contents),
    }


def remove_stored_image(image_path: str | None) -> None:
    if image_path:
        path = Path(image_path)
        if path.is_file() and path.parent == UPLOAD_DIR:
            path.unlink()


def image_as_data_url(image_path: str, content_type: str) -> str | None:
    path = Path(image_path)
    if not path.is_file() or path.parent != UPLOAD_DIR:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"
