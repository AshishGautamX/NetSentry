"""
test_archive_upload.py
======================
Tests for the Bulk Archive Upload engine (archive_processor.py) and the
POST /api/configurations/upload-archive FastAPI endpoint.

Covers:
  - .zip extraction + full ingestion
  - .tar.gz extraction + full ingestion
  - SHA-256 deduplication within a single archive
  - Unsupported extension filtering
  - Oversized archive rejection (ValueError)
  - Malformed archive rejection (ValueError)
  - API endpoint happy-path via httpx TestClient
"""
import io
import zipfile
import tarfile
import pytest
from fastapi.testclient import TestClient

from backend.app.engine.archive_processor import (
    extract_archive,
    process_archive_members,
    MAX_ARCHIVE_SIZE_BYTES,
    ArchiveProcessResult,
)

# ---------------------------------------------------------------------------
# Minimal authentic-ish config content for tests
# ---------------------------------------------------------------------------
CISCO_SNIPPET = b"""\
hostname TEST-CISCO-ROUTER
!
ip ssh version 2
no ip http server
banner motd ^C Authorized use only ^C
line vty 0 4
 transport input ssh
!
"""

JUNIPER_SNIPPET = b"""\
system {
    host-name TEST-JUNIPER;
    services {
        ssh {
            protocol-version v2;
        }
    }
}
"""


# ---------------------------------------------------------------------------
# Helper: build an in-memory .zip archive
# ---------------------------------------------------------------------------
def _build_zip(members: dict) -> bytes:
    """members: {filename: bytes_content}"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _build_tar_gz(members: dict) -> bytes:
    """members: {filename: bytes_content}"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, content in members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


# ===========================================================================
# Unit tests — archive_processor engine
# ===========================================================================

class TestZipExtraction:
    def test_zip_extracts_cfg_files(self):
        archive_bytes = _build_zip({
            "cisco.cfg": CISCO_SNIPPET,
            "juniper.conf": JUNIPER_SNIPPET,
        })
        result = extract_archive(archive_bytes, "fleet.zip")
        assert result.total_found == 2
        assert len(result.processed) == 2
        assert len(result.skipped) == 0
        assert len(result.errors) == 0

    def test_zip_skips_non_config_extensions(self):
        archive_bytes = _build_zip({
            "cisco.cfg": CISCO_SNIPPET,
            "readme.pdf": b"not a config",
            "image.png": b"\x89PNG",
        })
        result = extract_archive(archive_bytes, "mixed.zip")
        assert result.total_found == 3
        assert len(result.processed) == 1  # only .cfg
        assert len(result.skipped) == 2

    def test_zip_skips_hidden_files(self):
        archive_bytes = _build_zip({
            "cisco.cfg": CISCO_SNIPPET,
            ".DS_Store": b"apple metadata",
            "__MACOSX/._cisco.cfg": b"resource fork",
        })
        result = extract_archive(archive_bytes, "macos_zip.zip")
        assert len(result.processed) == 1

    def test_zip_deduplication_within_archive(self):
        """Same content under two filenames → only one stored after ingestion."""
        archive_bytes = _build_zip({
            "copy1.cfg": CISCO_SNIPPET,
            "copy2.cfg": CISCO_SNIPPET,   # identical bytes → same SHA-256
        })
        result = extract_archive(archive_bytes, "dupes.zip")
        assert len(result.processed) == 2   # both extracted

        ingested = process_archive_members(result)
        # After dedup: only 1 unique hash
        assert len(ingested) == 1
        assert len(result.skipped) == 1  # second copy recorded as duplicate


class TestTarGzExtraction:
    def test_targz_extracts_conf_files(self):
        archive_bytes = _build_tar_gz({
            "cisco.cfg": CISCO_SNIPPET,
            "juniper.conf": JUNIPER_SNIPPET,
        })
        result = extract_archive(archive_bytes, "fleet.tar.gz")
        assert result.total_found == 2
        assert len(result.processed) == 2

    def test_tgz_extension_accepted(self):
        archive_bytes = _build_tar_gz({"router.cfg": CISCO_SNIPPET})
        result = extract_archive(archive_bytes, "configs.tgz")
        assert len(result.processed) == 1


class TestArchiveGuards:
    def test_oversized_archive_raises_value_error(self):
        # Simulate a file that reports as too large (padding to exceed cap)
        oversized = b"X" * (MAX_ARCHIVE_SIZE_BYTES + 1)
        with pytest.raises(ValueError, match="too large"):
            extract_archive(oversized, "huge.zip")

    def test_unsupported_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported archive format"):
            extract_archive(b"data", "configs.7z")

    def test_malformed_zip_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid or corrupted ZIP"):
            extract_archive(b"this is not a zip", "bad.zip")

    def test_malformed_targz_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid or corrupted TAR"):
            extract_archive(b"this is not a tar", "bad.tar.gz")

    def test_empty_archive_returns_zero_members(self):
        archive_bytes = _build_zip({})
        result = extract_archive(archive_bytes, "empty.zip")
        assert result.total_found == 0
        assert len(result.processed) == 0


# ===========================================================================
# Integration tests — FastAPI endpoint via TestClient
# ===========================================================================

@pytest.fixture(scope="module")
def client():
    """In-process FastAPI TestClient with a fresh SQLite DB."""
    import gc
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_archive.db")
    os.environ.setdefault("AI_PROVIDER", "deterministic")

    from backend.app.main import app
    with TestClient(app) as c:
        yield c

    # Cleanup test DB — gc.collect() releases SQLAlchemy's connection pool
    # on Windows before attempting to delete the locked file.
    gc.collect()
    try:
        if os.path.exists("test_archive.db"):
            os.remove("test_archive.db")
    except PermissionError:
        pass  # Windows may still hold the file; it will be cleaned on next run


class TestArchiveEndpoint:
    def test_upload_zip_returns_fleet_summary(self, client: TestClient):
        archive_bytes = _build_zip({
            "cisco.cfg": CISCO_SNIPPET,
            "juniper.conf": JUNIPER_SNIPPET,
        })
        response = client.post(
            "/api/configurations/upload-archive",
            files={"file": ("fleet.zip", io.BytesIO(archive_bytes), "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["archive_filename"] == "fleet.zip"
        assert data["successfully_processed"] == 2
        assert data["skipped"] == 0
        assert data["errors"] == 0
        # Every processed member should have a valid config_id
        for member in data["members"]:
            if member["status"] == "processed":
                assert member["config_id"] is not None
                assert member["vendor_detected"] is not None

    def test_upload_targz_returns_fleet_summary(self, client: TestClient):
        archive_bytes = _build_tar_gz({"cisco_device.cfg": CISCO_SNIPPET})
        response = client.post(
            "/api/configurations/upload-archive",
            files={"file": ("routers.tar.gz", io.BytesIO(archive_bytes), "application/gzip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["successfully_processed"] == 1

    def test_upload_invalid_format_returns_400(self, client: TestClient):
        response = client.post(
            "/api/configurations/upload-archive",
            files={"file": ("configs.7z", io.BytesIO(b"7z data"), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Unsupported archive format" in response.json()["detail"]

    def test_upload_empty_file_returns_400(self, client: TestClient):
        response = client.post(
            "/api/configurations/upload-archive",
            files={"file": ("empty.zip", io.BytesIO(b""), "application/zip")},
        )
        assert response.status_code == 400

    def test_upload_skips_non_config_files(self, client: TestClient):
        archive_bytes = _build_zip({
            "cisco.cfg": CISCO_SNIPPET,
            "notes.pdf": b"%PDF data",
        })
        response = client.post(
            "/api/configurations/upload-archive",
            files={"file": ("mixed.zip", io.BytesIO(archive_bytes), "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["successfully_processed"] == 1
        assert data["skipped"] == 1
