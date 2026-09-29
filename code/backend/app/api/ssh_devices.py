"""
SSH Device Puller API
=====================
REST endpoints that allow users to pull running configurations directly from
live network devices over SSH, then immediately run them through the full
ingestion → vendor-detection → compliance → risk pipeline.

Credential security (enforced by the engine layer, ADR-04/ADR-07):
  ─ Credentials in the POST body are NEVER written to the database.
  ─ After the SSH session closes, credential references are deleted.
  ─ The raw config text is sanitized before storage (passwords, keys removed).
  ─ Only read-only show commands are sent to devices.

Endpoints:
  GET  /api/ssh/probe?hostname=&port=   — TCP reachability check, no credentials
  POST /api/ssh/pull                    — Pull config + full audit pipeline
  GET  /api/ssh/commands?vendor=        — List show commands for a vendor
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.models import (
    Configuration, ConfigurationLine, Device,
    AuditRun, AuditFinding, LearnedMapping, UnknownCommand,
)
from backend.app.schemas.schemas import (
    SSHPullRequestSchema, SSHPullResponse, SSHConnectivityResponse,
)
from backend.app.engine.ssh_puller import (
    SSHPullRequest, pull_device_config, test_ssh_connectivity,
    VENDOR_SHOW_COMMANDS, PARAMIKO_AVAILABLE,
)
from backend.app.engine.ingestion import process_file_content
from backend.app.engine.vendor_detector import VendorDetector
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.normalizer import NormalizationEngine
from backend.app.engine.compliance import ComplianceEngine
from backend.app.engine.risk import RiskEngine
from backend.app.engine.remediation import RemediationEngine

router = APIRouter(prefix="/ssh", tags=["SSH Device Puller"])


# ── Shared pipeline helper ────────────────────────────────────────────────────

def _ingest_and_audit(
    db: Session,
    raw_text: str,
    source_hostname: str,
) -> tuple[int, int, str, float, str, int]:
    """
    Run the full ingestion → audit pipeline for a pulled config string.

    Returns: (config_id, audit_id, vendor, compliance_pct, risk_level, lines_count)
    """
    file_bytes = raw_text.encode("utf-8")
    filename = f"ssh_pull_{source_hostname}.cfg"

    raw_text_out, sanitized, file_hash, file_size = process_file_content(
        file_bytes, filename
    )

    # Vendor detection
    detection = VendorDetector.detect(raw_text_out)
    vendor = detection["vendor"]
    hostname = detection["hostname"] or source_hostname

    # Dedup by hash
    existing = db.query(Configuration).filter(Configuration.file_hash == file_hash).first()
    if existing:
        config = existing
    else:
        device = db.query(Device).filter(Device.hostname == hostname).first()
        if not device:
            device = Device(
                hostname=hostname,
                vendor=vendor,
                model=detection["model"],
                os_version=detection["os_version"],
            )
            db.add(device)
            db.commit()
            db.refresh(device)

        config = Configuration(
            filename=filename,
            file_hash=file_hash,
            raw_content=raw_text_out,
            sanitized_content=sanitized,
            vendor_detected=vendor,
            device_model_detected=detection["model"],
            os_detected=detection["os_version"],
            file_size=file_size,
            lines_count=len(raw_text_out.splitlines()),
        )
        db.add(config)
        db.commit()
        db.refresh(config)

        parser = get_parser_for_vendor(vendor)
        for pl in parser.parse(sanitized):
            db.add(ConfigurationLine(
                config_id=config.id,
                line_number=pl.line_number,
                raw_text=pl.raw_text,
                section_context=pl.section_context,
                is_security_relevant=pl.is_security_relevant,
            ))
        db.commit()

    # Normalize + compliance
    active_learned = db.query(LearnedMapping).filter(LearnedMapping.is_active == True).all()
    parser = get_parser_for_vendor(vendor)
    parsed_lines, canonical_baseline, unknown_candidates = NormalizationEngine().normalize(
        parser.parse(sanitized), vendor, active_learned
    )

    for uc in unknown_candidates:
        if not db.query(UnknownCommand).filter(
            UnknownCommand.config_id == config.id,
            UnknownCommand.raw_command == uc["raw_command"]
        ).first():
            db.add(UnknownCommand(
                config_id=config.id,
                raw_command=uc["raw_command"],
                line_number=uc["line_number"],
                vendor=vendor,
                ai_suggested_category="Uncategorized",
                ai_suggested_param="",
                ai_confidence=0.5,
                status="PENDING",
            ))
    db.commit()

    raw_findings = ComplianceEngine().evaluate(canonical_baseline, vendor)
    remediation = RemediationEngine()
    for f in raw_findings:
        r = remediation.get_remediation(vendor, f["normalized_param"])
        f["remediation_text"] = r["remediation_text"]
        f["verification_cmd"] = r.get("verification_cmd")

    scores = RiskEngine.calculate_scores(raw_findings)

    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        device = Device(hostname=hostname, vendor=vendor,
                        model=detection["model"], os_version=detection["os_version"])
        db.add(device)
        db.commit()
        db.refresh(device)

    audit_run = AuditRun(
        device_id=device.id,
        config_id=config.id,
        compliance_percentage=scores["compliance_percentage"],
        risk_score=scores["risk_score"],
        risk_level=scores["risk_level"],
        total_controls=len(raw_findings),
        passed_count=scores["passed_count"],
        failed_count=scores["failed_count"],
        not_evaluable_count=scores["not_evaluable_count"],
        unknown_count=scores["unknown_count"],
        normalized_baseline=canonical_baseline.get("parameters", {}),
        status="COMPLETED",
    )
    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    for rf in raw_findings:
        db.add(AuditFinding(
            audit_id=audit_run.id,
            rule_id=rf["rule_id"],
            framework=rf["framework"],
            control_id=rf["control_id"],
            title=rf["title"],
            status=rf["status"],
            severity=rf["severity"],
            normalized_param=rf["normalized_param"],
            detected_value=rf.get("detected_value"),
            expected_value=rf.get("expected_value"),
            evidence_line_no=rf.get("evidence_line_no"),
            evidence_text=rf.get("evidence_text"),
            section_context=rf.get("section_context"),
            rationale=rf.get("rationale"),
            remediation_text=rf.get("remediation_text"),
            verification_cmd=rf.get("verification_cmd"),
            is_learned_mapping_applied=rf.get("is_learned_mapping_applied", False),
        ))
    db.commit()

    return (
        config.id,
        audit_run.id,
        vendor,
        round(scores["compliance_percentage"], 2),
        scores["risk_level"],
        config.lines_count,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/probe", response_model=SSHConnectivityResponse)
def probe_device(
    hostname: str = Query(..., description="IP address or FQDN of the device"),
    port: int = Query(22, description="SSH port (default 22)"),
):
    """
    TCP-level reachability probe — no credentials required.
    Returns instantly if the SSH port is reachable.
    Use this before attempting a full pull to give faster UX feedback.
    """
    reachable = test_ssh_connectivity(hostname, port, timeout=5)
    return SSHConnectivityResponse(
        hostname=hostname,
        port=port,
        reachable=reachable,
        message="SSH port reachable" if reachable else "Host unreachable or port closed",
    )


@router.post("/pull", response_model=SSHPullResponse)
def pull_and_audit(
    req: SSHPullRequestSchema,
    db: Session = Depends(get_db),
):
    """
    Open a read-only SSH session to a live network device, pull its running
    configuration via `show running-config` (or vendor-equivalent), sanitize
    it, run the full compliance audit pipeline, and return results.

    **Security**: The `password` field in the request body is never persisted.
    It is used only for the SSH session and then discarded. All configs are
    sanitized to remove credentials before storage.

    **No config changes are made** — only read-only show commands are sent.

    Returns an SSHPullResponse with the full audit summary (config_id, audit_id,
    compliance_percentage, risk_level) so the user can view detailed findings
    in the Audits tab immediately.
    """
    if not PARAMIKO_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=(
                "SSH Device Puller requires the `paramiko` package. "
                "Run: pip install paramiko  (then restart the backend)."
            ),
        )

    pull_req = SSHPullRequest(
        hostname=req.hostname,
        port=req.port,
        username=req.username,
        password=req.password,
        vendor_hint=req.vendor_hint,
        use_key_auth=req.use_key_auth,
        timeout=req.timeout,
    )

    result = pull_device_config(pull_req)

    if not result.success:
        return SSHPullResponse(
            host=result.host,
            port=result.port,
            success=False,
            error=result.error,
            elapsed_ms=result.elapsed_ms,
            commands_sent=result.commands_sent,
        )

    if not result.raw_config.strip():
        return SSHPullResponse(
            host=result.host,
            port=result.port,
            success=False,
            error="Device connected but returned empty configuration. Check credentials and device state.",
            elapsed_ms=result.elapsed_ms,
            commands_sent=result.commands_sent,
        )

    try:
        config_id, audit_id, vendor, compliance_pct, risk_level, lines = (
            _ingest_and_audit(db, result.raw_config, req.hostname)
        )
        return SSHPullResponse(
            host=result.host,
            port=result.port,
            success=True,
            config_id=config_id,
            audit_id=audit_id,
            vendor_detected=vendor,
            compliance_percentage=compliance_pct,
            risk_level=risk_level,
            lines_pulled=lines,
            elapsed_ms=result.elapsed_ms,
            commands_sent=result.commands_sent,
        )
    except Exception as exc:
        return SSHPullResponse(
            host=result.host,
            port=result.port,
            success=False,
            error=f"Pipeline error after successful SSH pull: {exc}",
            elapsed_ms=result.elapsed_ms,
        )


@router.get("/commands")
def list_show_commands(vendor: str = Query("cisco", description="Vendor name")):
    """
    Returns the list of show commands that will be sent to a device of the
    given vendor type. Useful for verifying expected behavior before pulling.
    """
    from backend.app.engine.ssh_puller import _resolve_commands
    return {
        "vendor": vendor,
        "commands": _resolve_commands(vendor),
        "supported_vendors": [k for k in VENDOR_SHOW_COMMANDS if k != "__default__"],
    }


@router.get("/status")
def ssh_status():
    """Returns whether the paramiko SSH library is installed and ready."""
    return {
        "paramiko_available": PARAMIKO_AVAILABLE,
        "message": (
            "SSH Device Puller is ready."
            if PARAMIKO_AVAILABLE
            else "Install paramiko: pip install paramiko"
        ),
        "supported_vendors": [k for k in VENDOR_SHOW_COMMANDS if k != "__default__"],
        "security_notes": [
            "Credentials are never persisted to the database.",
            "Only read-only show commands are sent to devices.",
            "All pulled configs are sanitized before storage.",
            "SSH session is closed immediately after config pull.",
        ],
    }
