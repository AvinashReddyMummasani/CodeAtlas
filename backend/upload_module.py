"""
upload_module.py — Safe ZIP upload + extraction for CodeAtlas.

Public API
----------
save_upload(file, session_id, max_mb) -> dict
"""

from __future__ import annotations

import io
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SESSIONS_ROOT = Path("sessions")
ZIP_MAGIC = b"PK\x03\x04"           # Local file header signature
MAX_TOTAL_UNCOMPRESSED_MB = 500
MAX_TOTAL_UNCOMPRESSED_BYTES = MAX_TOTAL_UNCOMPRESSED_MB * 1024 * 1024
MAX_FILE_COUNT = 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_real_zip(header: bytes) -> bool:
    """Return True if the first bytes match the ZIP local-file-header magic."""
    return header[:4] == ZIP_MAGIC


def _is_safe_member(member_name: str) -> bool:
    """
    Reject any archive member whose name contains path-traversal components
    or is an absolute path.
    """
    # Absolute paths
    if os.path.isabs(member_name):
        return False
    # Path traversal
    normalized = os.path.normpath(member_name)
    if normalized.startswith(".."):
        return False
    parts = Path(member_name).parts
    if ".." in parts:
        return False
    return True


def _mb(n_bytes: int) -> float:
    return n_bytes / (1024 * 1024)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

async def save_upload(
    file: UploadFile,
    session_id: Optional[str] = None,
    max_mb: int = 50,
) -> dict:
    """
    Validate, extract, and catalogue a ZIP upload for one analysis session.

    Parameters
    ----------
    file       : FastAPI UploadFile (must be a .zip)
    session_id : Existing session ID, or None to generate a new UUID4.
    max_mb     : Maximum raw (compressed) upload size in megabytes.

    Returns
    -------
    dict with keys:
        session_id  – str
        py_files    – list of str (relative paths inside session_dir)
        other_files – list of str
        session_dir – str (absolute path)
        error       – None | str
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    result: dict = {
        "session_id": session_id,
        "py_files": [],
        "other_files": [],
        "session_dir": "",
        "error": None,
    }

    # ------------------------------------------------------------------
    # 1. Read the entire upload into memory so we can inspect it safely.
    # ------------------------------------------------------------------
    try:
        raw_bytes: bytes = await file.read()
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"Failed to read uploaded file: {exc}"
        return result

    # ------------------------------------------------------------------
    # 2. Size guard (compressed / raw upload size).
    # ------------------------------------------------------------------
    max_bytes = max_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        result["error"] = (
            f"Upload exceeds the {max_mb} MB limit "
            f"(received {_mb(len(raw_bytes)):.2f} MB)."
        )
        return result

    # ------------------------------------------------------------------
    # 3. Magic-byte validation — must be a real ZIP file.
    # ------------------------------------------------------------------
    if len(raw_bytes) < 4 or not _is_real_zip(raw_bytes):
        result["error"] = (
            "Uploaded file is not a valid ZIP archive (magic bytes mismatch)."
        )
        return result

    # ------------------------------------------------------------------
    # 4. Open as ZIP and validate members before touching the filesystem.
    # ------------------------------------------------------------------
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile as exc:
        result["error"] = f"ZIP file is corrupt or invalid: {exc}"
        return result

    with zf:
        members = zf.infolist()

        # 4a. File-count bomb guard
        if len(members) > MAX_FILE_COUNT:
            result["error"] = (
                f"ZIP bomb rejected: archive contains {len(members):,} members "
                f"(limit {MAX_FILE_COUNT:,})."
            )
            return result

        # 4b. Total uncompressed size bomb guard + path-traversal guard
        total_uncompressed = 0
        for info in members:
            if not _is_safe_member(info.filename):
                result["error"] = (
                    f"Unsafe archive member rejected: '{info.filename}'. "
                    "Path traversal or absolute paths are not allowed."
                )
                return result
            total_uncompressed += info.file_size

        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            result["error"] = (
                f"ZIP bomb rejected: total uncompressed size "
                f"{_mb(total_uncompressed):.1f} MB exceeds "
                f"{MAX_TOTAL_UNCOMPRESSED_MB} MB limit."
            )
            return result

        # ------------------------------------------------------------------
        # 5. Prepare session directory (clean slate if it already exists).
        # ------------------------------------------------------------------
        session_dir = SESSIONS_ROOT / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
        session_dir.mkdir(parents=True, exist_ok=True)

        result["session_dir"] = str(session_dir.resolve())

        # ------------------------------------------------------------------
        # 6. Extract — member by member to avoid any library short-circuits.
        # ------------------------------------------------------------------
        py_files: list[str] = []
        other_files: list[str] = []

        for info in members:
            # Skip directory entries
            if info.filename.endswith("/") or info.is_dir():
                target_dir = session_dir / info.filename
                target_dir.mkdir(parents=True, exist_ok=True)
                continue

            target_path = (session_dir / info.filename).resolve()

            # Double-check resolved path is still inside session_dir
            try:
                target_path.relative_to(session_dir.resolve())
            except ValueError:
                result["error"] = (
                    f"Path-traversal attempt detected for member '{info.filename}'. "
                    "Extraction aborted."
                )
                shutil.rmtree(session_dir, ignore_errors=True)
                return result

            # Create intermediate directories
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content — never execute or import
            with zf.open(info) as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            # Categorise
            rel = str(Path(info.filename))
            if info.filename.lower().endswith(".py"):
                py_files.append(rel)
            else:
                other_files.append(rel)

    result["py_files"] = sorted(py_files)
    result["other_files"] = sorted(other_files)
    return result
