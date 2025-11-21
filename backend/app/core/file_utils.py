import os
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile
from loguru import logger

from .config import settings

_UPLOAD_WRITE_TEST_FILENAME = ".upload-write-test"


def get_upload_root() -> Path:
    """Get the configured upload root directory path."""
    return settings.upload_storage_directory


def ensure_upload_root_exists() -> Path:
    """Create the configured upload root directory if it is missing."""
    upload_root = get_upload_root()
    if upload_root.is_dir():
        return upload_root
    if upload_root.exists() and not upload_root.is_dir():
        raise RuntimeError(
            f"Upload storage path '{upload_root}' exists but is not a directory"
        )
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root


def verify_upload_root_writable() -> Path:
    """Ensure the upload root is writable by performing a small write test."""
    upload_root = ensure_upload_root_exists()
    test_file = upload_root / _UPLOAD_WRITE_TEST_FILENAME
    try:
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("ok")
        test_file.unlink()
    except OSError as exc:  # pragma: no cover - fails only on misconfigured hosts
        logger.error(
            "Upload storage directory {upload_root} is not writable: {error}",
            upload_root=upload_root,
            error=exc,
        )
        raise RuntimeError(
            f"Upload storage directory '{upload_root}' is not writable"
        ) from exc
    return upload_root


def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file based on size and extension"""
    # Check file extension first
    if file.filename is None:
        raise HTTPException(status_code=400, detail="File has no filename")
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_extension}' not allowed. Allowed: {', '.join(settings.allowed_extensions)}",
        )

    # Check file size - try to get it from the file object
    file_size = getattr(file, "size", None)
    if file_size is None:
        # If size is not available, try to read the file content to get size
        try:
            original_position = file.file.tell() if hasattr(file.file, "tell") else 0
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(original_position)  # Return to original position
        except Exception:
            # If we can't determine size, allow the upload to proceed
            # The size will be determined after saving
            file_size = 0

    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum limit of {settings.max_file_size} bytes",
        )

    return True


def save_upload_file(file: UploadFile, evidence_seeker_id: int) -> str:
    """Save uploaded file to disk and return the file path"""
    # Ensure upload directory exists
    upload_dir = ensure_upload_root_exists() / str(evidence_seeker_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    if file.filename is None:
        raise HTTPException(status_code=400, detail="File has no filename")
    file_extension = Path(file.filename).suffix.lower()
    import uuid

    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save file: {str(e)}"
        ) from e

    return str(file_path)


def delete_file(file_path: str) -> bool:
    """Delete file from disk"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        # Log error but don't raise exception to avoid breaking the API
        print(f"Error deleting file {file_path}: {str(e)}")
        return False


def get_file_info(file_path: str) -> dict | None:
    """Get file information"""
    try:
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            return {
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
            }
        return None
    except Exception as e:
        print(f"Error getting file info for {file_path}: {str(e)}")
        return None
