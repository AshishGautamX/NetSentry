"""
GitOps Webhook Auditing API
============================
Provides POST /api/webhooks/github and POST /api/webhooks/gitlab endpoints
that receive push event payloads from GitHub / GitLab, automatically identify
network configuration files in the commit diff, fetch their raw content, and
run each through the full compliance audit pipeline.

Security:
  - HMAC-SHA256 signature validation (X-Hub-Signature-256 / X-Gitlab-Token).
  - Webhook secret configured via GITHUB_WEBHOOK_SECRET / GITLAB_WEBHOOK_SECRET env vars.
  - If no secret is configured, signature validation is skipped (dev/demo mode).
  - Config file content is treated as untrusted text per ADR-04 — never executed.

Compliance pipeline:
  Each fetched file goes through: sanitize → vendor-detect → parse → normalize
  → compliance evaluate → risk score → persist AuditRun + AuditFindings.
"""
import hashlib
import hmac
import datetime
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db, SessionLocal
from backend.app.models.models import (
    Configuration, ConfigurationLine, Device,
    AuditRun, AuditFinding, LearnedMapping, UnknownCommand,
)
from backend.app.schemas.schemas import WebhookAuditResponse, WebhookConfigFileResult
from backend.app.engine.ingestion import process_file_content
from backend.app.engine.vendor_detector import VendorDetector
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.normalizer import NormalizationEngine
from backend.app.engine.compliance import ComplianceEngine
from backend.app.engine.risk import RiskEngine
from backend.app.engine.remediation import RemediationEngine
from backend.app.engine.webhook_processor import (
    parse_github_payload,
    parse_gitlab_payload,
    fetch_raw_file,
    WebhookParseResult,
    ChangedConfigFile,
)

router = APIRouter(prefix="/webhooks", tags=["GitOps Webhooks"])

# ── HMAC Signature Helpers ────────────────────────────────────────────────────

def _verify_github_signature(body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Validates GitHub's X-Hub-Signature-256 HMAC-SHA256 header.
    Returns True if valid or if no secret is configured (dev mode).
    """
    if not secret:
        return True  # dev/demo mode: skip validation
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)


def _verify_gitlab_token(token_header: Optional[str], secret: str) -> bool:
    """
    Validates GitLab's X-Gitlab-Token header (simple string comparison).
    Returns True if valid or if no secret is configured (dev mode).
    """
    if not secret:
        return True  # dev/demo mode
    if not token_header:
        return False
    return hmac.compare_digest(token_header, secret)


# ── Core Pipeline: Ingest + Audit a Single Config File ───────────────────────

def _run_pipeline_for_file(
    db: Session,
    filename: str,
    file_bytes: bytes,
    source_url: str,
) -> WebhookConfigFileResult:
    """
    Runs the full ingestion → compliance pipeline for one config file fetched
    from a webhook push event.

    Returns a WebhookConfigFileResult with audit summary.
    """
    # 1. Ingest + sanitize
    raw_text, sanitized_text, file_hash, file_size = process_file_content(
        file_bytes, filename
    )

    # 2. Vendor detection
    detection = VendorDetector.detect(raw_text)
    vendor = detection["vendor"]
    hostname = detection["hostname"]

    # 3. Persist or retrieve existing config (dedup by hash)
    existing_config = db.query(Configuration).filter(
        Configuration.file_hash == file_hash
    ).first()

    if existing_config:
        config = existing_config
    else:
        # Persist device
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
            raw_content=raw_text,
            sanitized_content=sanitized_text,
            vendor_detected=vendor,
            device_model_detected=detection["model"],
            os_detected=detection["os_version"],
            file_size=file_size,
            lines_count=len(raw_text.splitlines()),
        )
        db.add(config)
        db.commit()
        db.refresh(config)

        # 4. Parse and persist config lines
        parser = get_parser_for_vendor(vendor)
        parsed_lines_stored = parser.parse(sanitized_text)
        for pl in parsed_lines_stored:
            db.add(ConfigurationLine(
                config_id=config.id,
                line_number=pl.line_number,
                raw_text=pl.raw_text,
                section_context=pl.section_context,
                is_security_relevant=pl.is_security_relevant,
            ))
        db.commit()

    # 5. Normalize
    active_learned = db.query(LearnedMapping).filter(
        LearnedMapping.is_active == True
    ).all()
    parser = get_parser_for_vendor(vendor)
    parsed_lines = parser.parse(sanitized_text)
    normalizer = NormalizationEngine()
    parsed_lines, canonical_baseline, unknown_candidates = normalizer.normalize(
        parsed_lines, vendor, active_learned
    )

    # 6. Record unknown commands
    for uc in unknown_candidates:
        exists = db.query(UnknownCommand).filter(
            UnknownCommand.config_id == config.id,
            UnknownCommand.raw_command == uc["raw_command"]
        ).first()
        if not exists:
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

    # 7. Compliance evaluation
    compliance_engine = ComplianceEngine()
    raw_findings = compliance_engine.evaluate(canonical_baseline, vendor)

    remediation_engine = RemediationEngine()
    for f in raw_findings:
        remed = remediation_engine.get_remediation(vendor, f["normalized_param"])
        f["remediation_text"] = remed["remediation_text"]
        f["verification_cmd"] = remed.get("verification_cmd")

    # 8. Risk calculation
    scores = RiskEngine.calculate_scores(raw_findings)

    # 9. Find / create device record for this audit run
    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        device = Device(
            hostname=hostname, vendor=vendor,
            model=detection["model"], os_version=detection["os_version"]
        )
        db.add(device)
        db.commit()
        db.refresh(device)

    # 10. Persist AuditRun
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

    # 11. Persist AuditFindings
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

    return WebhookConfigFileResult(
        filename=filename,
        raw_url=source_url,
        status="audited",
        config_id=config.id,
        audit_id=audit_run.id,
        vendor_detected=vendor,
        compliance_percentage=round(scores["compliance_percentage"], 2),
        risk_level=scores["risk_level"],
    )


# ── Shared Webhook Handler ────────────────────────────────────────────────────

async def _handle_webhook(
    parsed: WebhookParseResult,
    db: Session,
    access_token: str = "",
) -> WebhookAuditResponse:
    """
    Fetch and audit all config files identified in a webhook push event.
    """
    file_results: list[WebhookConfigFileResult] = []

    for cf in parsed.config_files:
        try:
            file_bytes = fetch_raw_file(cf.raw_url, token=access_token or None)
        except ValueError as exc:
            file_results.append(WebhookConfigFileResult(
                filename=cf.filename,
                raw_url=cf.raw_url,
                status="error",
                reason=str(exc),
            ))
            continue

        try:
            result = _run_pipeline_for_file(db, cf.filename, file_bytes, cf.raw_url)
            file_results.append(result)
        except Exception as exc:
            file_results.append(WebhookConfigFileResult(
                filename=cf.filename,
                raw_url=cf.raw_url,
                status="error",
                reason=f"Pipeline error: {exc}",
            ))

    # Skipped (non-config) files
    for ignored in parsed.ignored_files:
        file_results.append(WebhookConfigFileResult(
            filename=ignored,
            raw_url="",
            status="skipped",
            reason="Not a recognised network configuration extension",
        ))

    audited_count = sum(1 for f in file_results if f.status == "audited")
    skipped_count = sum(1 for f in file_results if f.status == "skipped")
    error_count = sum(1 for f in file_results if f.status == "error")

    return WebhookAuditResponse(
        platform=parsed.platform,
        repository=parsed.repository,
        branch=parsed.branch,
        commit_sha=parsed.commit_sha,
        pusher=parsed.pusher,
        commit_message=parsed.commit_message,
        total_config_files_found=len(parsed.config_files),
        audited=audited_count,
        skipped=skipped_count,
        errors=error_count,
        files=file_results,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/github", response_model=WebhookAuditResponse, status_code=200)
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header(None, alias="X-Github-Event"),
    db: Session = Depends(get_db),
):
    """
    Receive a GitHub `push` webhook event.

    Configure your GitHub repository webhook to:
      - Payload URL: http://<your-server>:8000/api/webhooks/github
      - Content type: application/json
      - Secret: value of GITHUB_WEBHOOK_SECRET environment variable
      - Events: Just the push event

    On each push, this endpoint:
      1. Validates the HMAC-SHA256 signature (if GITHUB_WEBHOOK_SECRET is set).
      2. Parses the commit diff to find added/modified .cfg/.conf/.json files.
      3. Fetches each file's raw content from GitHub's CDN.
      4. Runs the full ingestion → vendor detection → compliance → risk pipeline.
      5. Returns a fleet-level audit summary.
    """
    body = await request.body()

    # Validate signature
    if not _verify_github_signature(body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature.")

    # Only process push events; acknowledge all others
    if x_github_event and x_github_event != "push":
        return WebhookAuditResponse(
            platform="github",
            repository="",
            branch="",
            commit_sha="",
            pusher="",
            commit_message=f"Event '{x_github_event}' acknowledged but not processed.",
            total_config_files_found=0,
            audited=0,
            skipped=0,
            errors=0,
            files=[],
        )

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    parsed = parse_github_payload(payload)
    return await _handle_webhook(parsed, db, access_token=settings.GITHUB_TOKEN)


@router.post("/gitlab", response_model=WebhookAuditResponse, status_code=200)
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_event: Optional[str] = Header(None, alias="X-Gitlab-Event"),
    db: Session = Depends(get_db),
):
    """
    Receive a GitLab `Push Hook` webhook event.

    Configure your GitLab project webhook to:
      - URL: http://<your-server>:8000/api/webhooks/gitlab
      - Secret token: value of GITLAB_WEBHOOK_SECRET environment variable
      - Trigger: Push events

    Processing is identical to the GitHub endpoint but uses GitLab's
    raw file URL format and X-Gitlab-Token header for authentication.
    """
    body = await request.body()

    # Validate token
    if not _verify_gitlab_token(x_gitlab_token, settings.GITLAB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid GitLab webhook token.")

    if x_gitlab_event and "Push" not in x_gitlab_event:
        return WebhookAuditResponse(
            platform="gitlab",
            repository="",
            branch="",
            commit_sha="",
            pusher="",
            commit_message=f"Event '{x_gitlab_event}' acknowledged but not processed.",
            total_config_files_found=0,
            audited=0,
            skipped=0,
            errors=0,
            files=[],
        )

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    parsed = parse_gitlab_payload(payload)
    return await _handle_webhook(parsed, db, access_token=settings.GITLAB_TOKEN)


@router.get("/status", tags=["GitOps Webhooks"])
def webhook_status():
    """
    Returns configuration status of the webhook integration.
    Useful for verifying that webhook secrets are loaded without exposing their values.
    """
    return {
        "github_webhook_configured": bool(settings.GITHUB_WEBHOOK_SECRET),
        "gitlab_webhook_configured": bool(settings.GITLAB_WEBHOOK_SECRET),
        "github_private_repo_access": bool(settings.GITHUB_TOKEN),
        "gitlab_private_repo_access": bool(settings.GITLAB_TOKEN),
        "github_endpoint": "/api/webhooks/github",
        "gitlab_endpoint": "/api/webhooks/gitlab",
        "supported_extensions": [".cfg", ".conf", ".txt", ".json", ".set"],
        "max_file_size_mb": 5,
    }
