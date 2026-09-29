from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import Configuration, ConfigurationLine, Device
from backend.app.schemas.schemas import ConfigurationResponse, ArchiveMemberResult, ArchiveUploadResponse
from backend.app.engine.ingestion import process_file_content
from backend.app.engine.vendor_detector import VendorDetector
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.archive_processor import extract_archive, process_archive_members

router = APIRouter(prefix="/configurations", tags=["Configurations"])

@router.post("/upload", response_model=List[ConfigurationResponse])
async def upload_configurations(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts one or multiple network configuration files, sanitizes sensitive credentials,
    detects vendor and platform, and registers them in the database.
    """
    uploaded_configs = []

    for file in files:
        content_bytes = await file.read()
        if len(content_bytes) == 0:
            continue

        raw_text, sanitized_text, file_hash, file_size = process_file_content(content_bytes, file.filename)
        detection = VendorDetector.detect(raw_text)

        # Register or get device
        hostname = detection["hostname"]
        device = db.query(Device).filter(Device.hostname == hostname).first()
        if not device:
            device = Device(
                hostname=hostname,
                vendor=detection["vendor"],
                model=detection["model"],
                os_version=detection["os_version"]
            )
            db.add(device)
            db.commit()
            db.refresh(device)

        # Check existing config by hash or save new
        config = db.query(Configuration).filter(Configuration.file_hash == file_hash).first()
        if not config:
            config = Configuration(
                filename=file.filename,
                file_hash=file_hash,
                raw_content=raw_text,
                sanitized_content=sanitized_text,
                vendor_detected=detection["vendor"],
                device_model_detected=detection["model"],
                os_detected=detection["os_version"],
                file_size=file_size,
                lines_count=len(raw_text.splitlines())
            )
            db.add(config)
            db.commit()
            db.refresh(config)

            # Parse lines using vendor-specific parser
            parser = get_parser_for_vendor(detection["vendor"])
            parsed_lines = parser.parse(sanitized_text)

            for pl in parsed_lines:
                cline = ConfigurationLine(
                    config_id=config.id,
                    line_number=pl.line_number,
                    raw_text=pl.raw_text,
                    section_context=pl.section_context,
                    is_security_relevant=pl.is_security_relevant
                )
                db.add(cline)
            db.commit()

        uploaded_configs.append(ConfigurationResponse(
            id=config.id,
            filename=config.filename,
            file_hash=config.file_hash,
            vendor_detected=config.vendor_detected,
            device_model_detected=config.device_model_detected,
            os_detected=config.os_detected,
            file_size=config.file_size,
            lines_count=config.lines_count,
            uploaded_at=config.uploaded_at,
            sanitized_preview="\n".join(config.sanitized_content.splitlines()[:20])
        ))

    return uploaded_configs

@router.get("", response_model=List[ConfigurationResponse])
def list_configurations(db: Session = Depends(get_db)):
    configs = db.query(Configuration).order_by(Configuration.uploaded_at.desc()).all()
    return [
        ConfigurationResponse(
            id=c.id,
            filename=c.filename,
            file_hash=c.file_hash,
            vendor_detected=c.vendor_detected,
            device_model_detected=c.device_model_detected,
            os_detected=c.os_detected,
            file_size=c.file_size,
            lines_count=c.lines_count,
            uploaded_at=c.uploaded_at,
            sanitized_preview="\n".join(c.sanitized_content.splitlines()[:20])
        )
        for c in configs
    ]

@router.get("/{config_id}", response_model=ConfigurationResponse)
def get_configuration(config_id: int, db: Session = Depends(get_db)):
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return ConfigurationResponse(
        id=config.id,
        filename=config.filename,
        file_hash=config.file_hash,
        vendor_detected=config.vendor_detected,
        device_model_detected=config.device_model_detected,
        os_detected=config.os_detected,
        file_size=config.file_size,
        lines_count=config.lines_count,
        uploaded_at=config.uploaded_at,
        sanitized_preview=config.sanitized_content
    )


# ── Fleet / Bulk Archive Upload ────────────────────────────────────────────────

def _store_config_from_ingestion(
    db: Session,
    filename: str,
    raw_text: str,
    sanitized_text: str,
    file_hash: str,
    file_size: int,
) -> Configuration:
    """
    Shared helper: detect vendor, persist device + configuration + parsed lines.
    Deduplicates by SHA-256 hash — returns existing record if hash already stored.
    """
    # Check if this config has already been stored (idempotent on hash)
    existing = db.query(Configuration).filter(Configuration.file_hash == file_hash).first()
    if existing:
        return existing

    detection = VendorDetector.detect(raw_text)
    hostname = detection["hostname"]

    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        device = Device(
            hostname=hostname,
            vendor=detection["vendor"],
            model=detection["model"],
            os_version=detection["os_version"],
        )
        db.add(device)
        db.commit()
        db.refresh(device)

    config = Configuration(
        filename=filename,
        file_hash=file_hash,
        raw_content=raw_text,
        sanitized_content=sanitized_text,
        vendor_detected=detection["vendor"],
        device_model_detected=detection["model"],
        os_detected=detection["os_version"],
        file_size=file_size,
        lines_count=len(raw_text.splitlines()),
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    parser = get_parser_for_vendor(detection["vendor"])
    parsed_lines = parser.parse(sanitized_text)
    for pl in parsed_lines:
        cline = ConfigurationLine(
            config_id=config.id,
            line_number=pl.line_number,
            raw_text=pl.raw_text,
            section_context=pl.section_context,
            is_security_relevant=pl.is_security_relevant,
        )
        db.add(cline)
    db.commit()

    return config


@router.post("/upload-archive", response_model=ArchiveUploadResponse)
async def upload_archive(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accept a single .zip, .tar.gz, .tgz, or .tar.bz2 archive containing one or
    more network configuration files.  Every member is individually processed
    through the full ingestion → vendor-detection → parsing pipeline and stored
    in the database.

    Returns a fleet-level summary with per-file status, vendor detection result,
    and configuration IDs ready for auditing.
    """
    archive_filename = file.filename or "upload.zip"
    content_bytes = await file.read()

    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded archive file is empty.")

    # Extract members from archive
    try:
        extraction = extract_archive(content_bytes, archive_filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Run ingestion pipeline on all valid members
    ingested = process_archive_members(extraction)

    member_results: list[ArchiveMemberResult] = []

    # Persist each successfully ingested member
    for (fname, raw_text, sanitized_text, file_hash, file_size) in ingested:
        try:
            config = _store_config_from_ingestion(
                db, fname, raw_text, sanitized_text, file_hash, file_size
            )
            member_results.append(ArchiveMemberResult(
                filename=fname,
                status="processed",
                config_id=config.id,
                vendor_detected=config.vendor_detected,
                lines_count=config.lines_count,
            ))
        except Exception as exc:
            member_results.append(ArchiveMemberResult(
                filename=fname,
                status="error",
                reason=str(exc),
            ))

    # Record skipped entries
    for (fname, reason) in extraction.skipped:
        member_results.append(ArchiveMemberResult(
            filename=fname,
            status="skipped",
            reason=reason,
        ))

    # Record extraction errors
    for (fname, reason) in extraction.errors:
        member_results.append(ArchiveMemberResult(
            filename=fname,
            status="error",
            reason=reason,
        ))

    processed_count = sum(1 for m in member_results if m.status == "processed")
    skipped_count = sum(1 for m in member_results if m.status == "skipped")
    error_count = sum(1 for m in member_results if m.status == "error")

    return ArchiveUploadResponse(
        archive_filename=archive_filename,
        total_members_in_archive=extraction.total_found,
        successfully_processed=processed_count,
        skipped=skipped_count,
        errors=error_count,
        members=member_results,
    )
