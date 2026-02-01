"""
Supabase Storage service for file uploads and signed URL generation.

Wraps the Supabase Storage SDK to provide a simple interface for
resume uploads and document management.  All file access goes through
signed URLs with configurable expiry.

Usage::

    from app.services.storage_service import upload_file, get_signed_url

    path = await upload_file(user_id="user_123", file_bytes=b"...", filename="resume.pdf")
    url = await get_signed_url(path, expires_in=900)
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Virus scanning: Supabase Storage does not expose a scanning API.
# Enable virus scanning via the Supabase dashboard:
#   Storage → Settings → Enable virus scanning on upload.
# Files flagged as infected will be quarantined automatically.

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ACCEPTED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
ACCEPTED_EXTENSIONS = {".pdf", ".docx"}
DEFAULT_BUCKET = "resumes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_storage():
    """Get the Supabase Storage client (lazy import to avoid circular deps)."""
    from app.db.supabase_client import get_client

    client = get_client()
    return client.storage


def _validate_file(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None,
) -> None:
    """
    Validate file size and type before upload.

    Raises:
        ValueError: If file exceeds size limit or has unsupported type.
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size ({len(file_bytes)} bytes) exceeds maximum "
            f"of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
        )

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ACCEPTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Accepted: {', '.join(sorted(ACCEPTED_EXTENSIONS))}"
        )

    if content_type and content_type not in ACCEPTED_CONTENT_TYPES:
        raise ValueError(
            f"Unsupported content type '{content_type}'. "
            f"Accepted: {', '.join(sorted(ACCEPTED_CONTENT_TYPES.keys()))}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def upload_file(
    user_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None,
    bucket: str = DEFAULT_BUCKET,
) -> str:
    """
    Upload a file to Supabase Storage.

    Files are stored under ``{bucket}/{user_id}/{filename}`` to enforce
    per-user isolation.  Existing files at the same path are overwritten.

    Args:
        user_id: Owner's Clerk user ID (used as folder prefix).
        file_bytes: Raw file content.
        filename: Original filename (used for path and extension validation).
        content_type: MIME type (optional, validated if provided).
        bucket: Storage bucket name (default: "resumes").

    Returns:
        The storage path (e.g. ``user_123/resume.pdf``).

    Raises:
        ValueError: If file validation fails.
        Exception: On Supabase Storage API errors.
    """
    _validate_file(file_bytes, filename, content_type)

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Supabase not configured -- file upload for user %s suppressed",
            user_id,
        )
        return f"{user_id}/{filename}"

    storage = _get_storage()
    path = f"{user_id}/{filename}"

    try:
        file_options = {}
        if content_type:
            file_options["content-type"] = content_type

        storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options=file_options or None,
        )
        logger.info("Uploaded %s to bucket '%s'", path, bucket)
        return path

    except Exception as exc:
        # Supabase returns 409 if file exists; try upsert
        if "Duplicate" in str(exc) or "409" in str(exc):
            storage.from_(bucket).update(
                path=path,
                file=file_bytes,
                file_options=file_options or None,
            )
            logger.info("Updated existing file %s in bucket '%s'", path, bucket)
            return path
        logger.error("Failed to upload %s: %s", path, exc)
        raise


async def get_signed_url(
    path: str,
    bucket: str = DEFAULT_BUCKET,
    expires_in: int = 900,
) -> str:
    """
    Generate a signed URL for a stored file.

    Args:
        path: Storage path returned by ``upload_file()``.
        bucket: Storage bucket name.
        expires_in: URL validity in seconds (default: 900 = 15 minutes).

    Returns:
        A time-limited signed URL string.

    Raises:
        Exception: On Supabase Storage API errors.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("Supabase not configured -- returning placeholder URL")
        return f"https://placeholder.storage/{bucket}/{path}"

    storage = _get_storage()

    try:
        result = storage.from_(bucket).create_signed_url(path, expires_in)
        url = result.get("signedURL", "")
        logger.info("Generated signed URL for %s (expires in %ds)", path, expires_in)
        return url

    except Exception as exc:
        logger.error("Failed to generate signed URL for %s: %s", path, exc)
        raise


async def delete_file(
    path: str,
    bucket: str = DEFAULT_BUCKET,
) -> bool:
    """
    Delete a file from Supabase Storage.

    Args:
        path: Storage path to delete.
        bucket: Storage bucket name.

    Returns:
        True if deletion succeeded, False otherwise.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("Supabase not configured -- delete for %s suppressed", path)
        return True

    storage = _get_storage()

    try:
        storage.from_(bucket).remove([path])
        logger.info("Deleted %s from bucket '%s'", path, bucket)
        return True
    except Exception as exc:
        logger.error("Failed to delete %s: %s", path, exc)
        return False
