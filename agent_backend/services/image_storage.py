"""
Durable storage and security validation for image attachments.
Enforces magic-byte verification, dimension boundaries, EXIF normalization,
and path traversal prevention.
"""
import io
import base64
import asyncio
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from PIL import Image, ImageOps

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_DIMENSION = 64
MAX_DIMENSION = 4096
Image.MAX_IMAGE_PIXELS = 20_000_000  # Decompression bomb prevention

ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png"}
MIME_MAP = {"image/jpeg": ".jpg", "image/png": ".png", "image/jpg": ".jpg"}

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "storage" / "uploads"

def _process_and_save_image(contents: bytes, upload_dir: Path) -> dict[str, str | int]:
    """Synchronous CPU-bound image processing offloaded to thread."""
    raw_stream = io.BytesIO(contents)
    with Image.open(raw_stream) as img:
        img_format = img.format
        if img_format not in ALLOWED_FORMATS:
            raise ValueError(
                f"Unsupported image format '{img_format}'. Only genuine JPEG and PNG images are accepted."
            )
        
        # Dimension constraints
        width, height = img.size
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            raise ValueError(
                f"Image resolution ({width}x{height}) is too small. Minimum required is {MIN_DIMENSION}x{MIN_DIMENSION} pixels."
            )
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise ValueError(
                f"Image resolution ({width}x{height}) exceeds maximum permitted size of {MAX_DIMENSION}x{MAX_DIMENSION} pixels."
            )

        # EXIF orientation correction
        transposed_img = ImageOps.exif_transpose(img)
        
        # Save normalized RGB image
        upload_dir.mkdir(parents=True, exist_ok=True)
        suffix = ALLOWED_FORMATS[img_format]
        unique_name = f"{uuid4().hex}{suffix}"
        dest_path = upload_dir / unique_name

        # Enforce path containment
        if not str(dest_path.resolve()).startswith(str(upload_dir.resolve())):
            raise ValueError("Path traversal attempt detected.")

        if transposed_img.mode != "RGB":
            transposed_img = transposed_img.convert("RGB")
            
        transposed_img.save(dest_path, format=img_format, quality=95)

    content_type = "image/jpeg" if img_format == "JPEG" else "image/png"
    return {
        "path": str(dest_path),
        "filename": dest_path.name,
        "image_key": f"img_{dest_path.stem}",
        "content_type": content_type,
        "size": dest_path.stat().st_size,
    }

async def save_uploaded_image(file: UploadFile) -> dict[str, str | int]:
    """
    Validate, sanitize, and save an uploaded image file securely.
    Ensures magic-byte validation, dimension checking, and EXIF transposition.
    Offloads synchronous CPU-bound operations to a worker thread.
    """
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if not contents:
        raise ValueError("Uploaded file is empty (0 bytes).")
    if len(contents) > MAX_IMAGE_BYTES:
        raise ValueError(f"The image exceeds the maximum permitted size of {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")

    try:
        return await asyncio.to_thread(_process_and_save_image, contents, UPLOAD_DIR)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Corrupted or invalid image file: {e}") from e

def remove_stored_image(image_path: str | None) -> None:
    """Safely delete a stored image strictly within the UPLOAD_DIR."""
    if not image_path:
        return
    try:
        path = Path(image_path).resolve()
        upload_resolved = UPLOAD_DIR.resolve()
        if path.is_file() and str(path).startswith(str(upload_resolved)):
            path.unlink(missing_ok=True)
    except Exception:
        pass

def image_as_data_url(image_path: str, content_type: str) -> str | None:
    """Read a stored image and return as a Base64 data URL."""
    try:
        path = Path(image_path).resolve()
        upload_resolved = UPLOAD_DIR.resolve()
        if not path.is_file() or not str(path).startswith(str(upload_resolved)):
            return None
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
    except Exception:
        return None
