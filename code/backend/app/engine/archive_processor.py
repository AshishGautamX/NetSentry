"""
Archive Processor Engine
========================
Extracts network configuration files from .zip and .tar.gz archives
and runs each member through the standard ingestion pipeline.

Supports: .zip, .tar.gz, .tgz, .tar.bz2
Config extension filter: .cfg, .conf, .txt, .json, .set, no-extension
Max archive size: configurable via MAX_ARCHIVE_SIZE_BYTES (default 50 MB).
"""
import io
import zipfile
import tarfile
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

from backend.app.engine.ingestion import process_file_content

# Extensions that are likely network configuration files
ALLOWED_EXTENSIONS = {".cfg", ".conf", ".txt", ".json", ".set", ""}

# 50 MB default archive cap (uncompressed total across all members)
MAX_ARCHIVE_SIZE_BYTES: int = 50 * 1024 * 1024

# Max individual member file size (10 MB)
MAX_MEMBER_SIZE_BYTES: int = 10 * 1024 * 1024

# Skip hidden files and OS metadata
SKIP_PREFIXES = {".", "__MACOSX", "._"}


@dataclass
class ExtractedMember:
    """Represents a single config file extracted from an archive."""
    filename: str           # member filename inside archive
    content_bytes: bytes    # raw file bytes
    size: int               # byte size


@dataclass
class ArchiveProcessResult:
    """Result of processing all members in an archive."""
    archive_filename: str
    total_found: int        # total entries in archive
    processed: List[ExtractedMember] = field(default_factory=list)
    skipped: List[Tuple[str, str]] = field(default_factory=list)  # (name, reason)
    errors: List[Tuple[str, str]] = field(default_factory=list)   # (name, error_msg)


def _is_allowed_member(name: str) -> bool:
    """
    Returns True if the archive member should be processed as a config file.
    Filters out directories, hidden files, OS metadata, and unsupported extensions.
    """
    # Normalise path separators
    basename = os.path.basename(name.replace("\\", "/"))

    # Skip blank basenames (directory entries)
    if not basename:
        return False

    # Skip hidden / OS metadata files
    for prefix in SKIP_PREFIXES:
        if basename.startswith(prefix):
            return False

    # Skip if the entry looks like a directory
    if name.endswith("/") or name.endswith("\\"):
        return False

    # Check extension
    _, ext = os.path.splitext(basename)
    return ext.lower() in ALLOWED_EXTENSIONS


def extract_zip(file_bytes: bytes, archive_filename: str) -> ArchiveProcessResult:
    """Extract member files from a .zip archive."""
    result = ArchiveProcessResult(
        archive_filename=archive_filename,
        total_found=0,
    )

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            members = zf.infolist()
            result.total_found = len(members)

            for info in members:
                name = info.filename
                if not _is_allowed_member(name):
                    result.skipped.append((name, "filtered (directory, hidden, or unsupported extension)"))
                    continue

                if info.file_size > MAX_MEMBER_SIZE_BYTES:
                    result.skipped.append((name, f"member too large ({info.file_size} bytes > {MAX_MEMBER_SIZE_BYTES})"))
                    continue

                try:
                    content = zf.read(name)
                    result.processed.append(ExtractedMember(
                        filename=os.path.basename(name),
                        content_bytes=content,
                        size=len(content),
                    ))
                except Exception as exc:
                    result.errors.append((name, str(exc)))

    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid or corrupted ZIP archive: {exc}") from exc

    return result


def extract_tar(file_bytes: bytes, archive_filename: str) -> ArchiveProcessResult:
    """Extract member files from a .tar.gz / .tgz / .tar.bz2 archive."""
    result = ArchiveProcessResult(
        archive_filename=archive_filename,
        total_found=0,
    )

    # Detect compression mode
    if archive_filename.endswith(".tar.bz2") or archive_filename.endswith(".tbz2"):
        mode = "r:bz2"
    else:
        mode = "r:gz"

    try:
        with tarfile.open(fileobj=io.BytesIO(file_bytes), mode=mode) as tf:
            members = tf.getmembers()
            result.total_found = len(members)

            for info in members:
                name = info.name
                if not _is_allowed_member(name):
                    result.skipped.append((name, "filtered (directory, hidden, or unsupported extension)"))
                    continue

                if info.size > MAX_MEMBER_SIZE_BYTES:
                    result.skipped.append((name, f"member too large ({info.size} bytes > {MAX_MEMBER_SIZE_BYTES})"))
                    continue

                try:
                    fobj = tf.extractfile(info)
                    if fobj is None:
                        result.skipped.append((name, "not a regular file (symlink or hardlink)"))
                        continue
                    content = fobj.read()
                    result.processed.append(ExtractedMember(
                        filename=os.path.basename(name),
                        content_bytes=content,
                        size=len(content),
                    ))
                except Exception as exc:
                    result.errors.append((name, str(exc)))

    except tarfile.TarError as exc:
        raise ValueError(f"Invalid or corrupted TAR archive: {exc}") from exc

    return result


def extract_archive(file_bytes: bytes, archive_filename: str) -> ArchiveProcessResult:
    """
    Main entry point. Detects archive type and delegates to zip or tar extractor.
    Enforces total uncompressed size cap.

    Args:
        file_bytes: Raw archive bytes.
        archive_filename: Original filename (used to detect archive type).

    Returns:
        ArchiveProcessResult with processed members ready for ingestion.

    Raises:
        ValueError: If archive is too large, unsupported format, or corrupted.
    """
    name_lower = archive_filename.lower()

    if len(file_bytes) > MAX_ARCHIVE_SIZE_BYTES:
        raise ValueError(
            f"Archive too large: {len(file_bytes):,} bytes "
            f"(max {MAX_ARCHIVE_SIZE_BYTES:,} bytes / 50 MB)."
        )

    if name_lower.endswith(".zip"):
        result = extract_zip(file_bytes, archive_filename)
    elif (
        name_lower.endswith(".tar.gz")
        or name_lower.endswith(".tgz")
        or name_lower.endswith(".tar.bz2")
        or name_lower.endswith(".tbz2")
    ):
        result = extract_tar(file_bytes, archive_filename)
    else:
        raise ValueError(
            f"Unsupported archive format: '{archive_filename}'. "
            "Accepted formats: .zip, .tar.gz, .tgz, .tar.bz2"
        )

    return result


def process_archive_members(
    result: ArchiveProcessResult,
) -> List[Tuple[str, str, str, str, int]]:
    """
    Runs each extracted member through the ingestion pipeline.

    Returns list of (filename, raw_content, sanitized_content, file_hash, file_size)
    for each successfully processed member. Deduplicates by SHA-256 hash.
    """
    seen_hashes: set = set()
    ingested: List[Tuple[str, str, str, str, int]] = []

    for member in result.processed:
        try:
            raw_text, sanitized_text, file_hash, file_size = process_file_content(
                member.content_bytes, member.filename
            )
            if file_hash in seen_hashes:
                result.skipped.append((member.filename, "duplicate (same SHA-256 already in this archive)"))
                continue
            seen_hashes.add(file_hash)
            ingested.append((member.filename, raw_text, sanitized_text, file_hash, file_size))
        except Exception as exc:
            result.errors.append((member.filename, f"ingestion error: {exc}"))

    return ingested
