import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import (
    Configuration, Device, AuditRun, AuditFinding, LearnedMapping, UnknownCommand
)
from backend.app.schemas.schemas import AuditRunResponse, AuditFindingResponse, GlobalFindingResponse, SecurityImpactResponse
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.normalizer import NormalizationEngine
from backend.app.engine.compliance import ComplianceEngine
from backend.app.engine.risk import RiskEngine
from backend.app.engine.remediation import RemediationEngine
from backend.app.engine.ai import get_ai_provider
from backend.app.services.settings_service import resolve_ai_provider

router = APIRouter(prefix="/audits", tags=["Audits"])

@router.post("/run/{config_id}", response_model=AuditRunResponse)
async def run_audit(config_id: int, db: Session = Depends(get_db)):
    """
    Executes a comprehensive, real-world compliance audit on an uploaded network configuration.
    Parses, normalizes, applies learned knowledge base, checks rules, calculates risk,
    and attaches device-specific remediation.
    """
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    vendor = config.vendor_detected or "unknown"
    parser = get_parser_for_vendor(vendor)
    parsed_lines = parser.parse(config.sanitized_content)

    # Fetch active learned mappings from database
    active_learned = db.query(LearnedMapping).filter(LearnedMapping.is_active == True).all()

    normalizer = NormalizationEngine()
    parsed_lines, canonical_baseline, unknown_candidates = normalizer.normalize(
        parsed_lines, vendor, active_learned
    )

    # Process and record any detected unknown syntax for human-in-the-loop training
    ai_provider = get_ai_provider()
    for uc in unknown_candidates:
        existing = db.query(UnknownCommand).filter(
            UnknownCommand.config_id == config_id,
            UnknownCommand.raw_command == uc["raw_command"]
        ).first()

        if not existing:
            # Consult AI / deterministic NLP provider for semantic hypothesis
            ai_res = await ai_provider.interpret_command(
                vendor, uc["raw_command"], uc.get("section_context", "")
            )
            unknown_entry = UnknownCommand(
                config_id=config_id,
                raw_command=uc["raw_command"],
                line_number=uc["line_number"],
                vendor=vendor,
                ai_suggested_category=ai_res.get("suggested_category", "Uncategorized"),
                ai_suggested_param=ai_res.get("suggested_parameter", ""),
                ai_confidence=ai_res.get("confidence", 0.5),
                status="PENDING"
            )
            db.add(unknown_entry)
    db.commit()

    # Deterministic Compliance Evaluation
    compliance_engine = ComplianceEngine()
    raw_findings = compliance_engine.evaluate(canonical_baseline, vendor)

    # Attach Vendor-Specific Remediation Commands
    remediation_engine = RemediationEngine()
    for f in raw_findings:
        remed_data = remediation_engine.get_remediation(vendor, f["normalized_param"])
        f["remediation_text"] = remed_data["remediation_text"]
        f["verification_cmd"] = remed_data.get("verification_cmd")

    # Quantitative Risk and Compliance Calculation
    scores = RiskEngine.calculate_scores(raw_findings)

    # Find associated device
    device = db.query(Device).filter(Device.vendor == vendor).first()
    if not device:
        device = Device(
            hostname=config.filename.split(".")[0],
            vendor=vendor,
            model=config.device_model_detected,
            os_version=config.os_detected
        )
        db.add(device)
        db.commit()
        db.refresh(device)

    # Persist AuditRun
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
        status="COMPLETED"
    )
    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    # Persist AuditFindings
    for rf in raw_findings:
        finding = AuditFinding(
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
            is_learned_mapping_applied=rf.get("is_learned_mapping_applied", False)
        )
        db.add(finding)

    # Track usage on applied learned mappings
    applied_params = [
        rf["normalized_param"] for rf in raw_findings if rf.get("is_learned_mapping_applied")
    ]
    if applied_params:
        for lm in active_learned:
            if lm.normalized_param in applied_params:
                lm.use_count += 1
                lm.last_used_at = datetime.datetime.utcnow()

    db.commit()

    return get_audit(audit_id=audit_run.id, db=db)

@router.get("", response_model=List[AuditRunResponse])
def list_audits(db: Session = Depends(get_db)):
    audits = db.query(AuditRun).order_by(AuditRun.timestamp.desc()).all()
    results = []
    for a in audits:
        device = db.query(Device).filter(Device.id == a.device_id).first()
        cfg = db.query(Configuration).filter(Configuration.id == a.config_id).first()
        results.append(AuditRunResponse(
            id=a.id,
            device_id=a.device_id,
            config_id=a.config_id,
            timestamp=a.timestamp,
            compliance_percentage=a.compliance_percentage,
            risk_score=a.risk_score,
            risk_level=a.risk_level,
            total_controls=a.total_controls,
            passed_count=a.passed_count,
            failed_count=a.failed_count,
            not_evaluable_count=a.not_evaluable_count,
            unknown_count=a.unknown_count,
            status=a.status,
            device_hostname=device.hostname if device else "UNKNOWN",
            device_vendor=device.vendor if device else "UNKNOWN",
            filename=cfg.filename if cfg else "N/A",
            normalized_baseline=a.normalized_baseline,
            findings=[]
        ))
    return results

@router.get("/findings/all", response_model=List[GlobalFindingResponse])
def list_all_findings(
    framework: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    audit_id: Optional[int] = None,
    vendor: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(AuditFinding).join(AuditRun, AuditFinding.audit_id == AuditRun.id)
    if audit_id:
        query = query.filter(AuditFinding.audit_id == audit_id)
    if framework and framework != "ALL":
        query = query.filter(AuditFinding.framework == framework)
    if status and status != "ALL":
        query = query.filter(AuditFinding.status == status)
    if severity and severity != "ALL":
        query = query.filter(AuditFinding.severity == severity)
    
    findings = query.order_by(AuditFinding.id.desc()).all()
    results = []
    
    # Cache audit metadata to avoid N+1 queries
    audit_cache = {}
    for f in findings:
        if f.audit_id not in audit_cache:
            ar = db.query(AuditRun).filter(AuditRun.id == f.audit_id).first()
            if ar:
                dev = db.query(Device).filter(Device.id == ar.device_id).first() if ar.device_id else None
                cfg = db.query(Configuration).filter(Configuration.id == ar.config_id).first() if ar.config_id else None
                audit_cache[f.audit_id] = {
                    "device_hostname": dev.hostname if dev else "UNKNOWN",
                    "device_vendor": dev.vendor if dev else (cfg.vendor_detected if cfg else "UNKNOWN"),
                    "filename": cfg.filename if cfg else "N/A",
                    "timestamp": ar.timestamp,
                }
            else:
                audit_cache[f.audit_id] = {
                    "device_hostname": "UNKNOWN",
                    "device_vendor": "UNKNOWN",
                    "filename": "N/A",
                    "timestamp": None,
                }
        
        meta = audit_cache[f.audit_id]
        if vendor and vendor != "ALL" and meta["device_vendor"].lower() != vendor.lower():
            continue

        results.append(GlobalFindingResponse(
            id=f.id,
            audit_id=f.audit_id,
            rule_id=f.rule_id,
            framework=f.framework,
            control_id=f.control_id,
            title=f.title,
            status=f.status,
            severity=f.severity,
            normalized_param=f.normalized_param,
            detected_value=f.detected_value,
            expected_value=f.expected_value,
            evidence_line_no=f.evidence_line_no,
            evidence_text=f.evidence_text,
            section_context=f.section_context,
            rationale=f.rationale,
            remediation_text=f.remediation_text,
            verification_cmd=f.verification_cmd,
            is_learned_mapping_applied=f.is_learned_mapping_applied,
            device_hostname=meta["device_hostname"],
            device_vendor=meta["device_vendor"],
            filename=meta["filename"],
            audit_timestamp=meta["timestamp"]
        ))
    return results

@router.get("/config/{config_id}/latest", response_model=AuditRunResponse)
def get_latest_audit_for_config(
    config_id: int,
    db: Session = Depends(get_db),
):
    """Return the most recent audit for a specific configuration."""
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    audit = (
        db.query(AuditRun)
        .filter(AuditRun.config_id == config_id)
        .order_by(AuditRun.timestamp.desc(), AuditRun.id.desc())
        .first()
    )
    if not audit:
        raise HTTPException(status_code=404, detail="No audit found for this configuration")

    return get_audit(audit_id=audit.id, db=db)



@router.post("/{audit_id}/findings/{finding_id}/impact", response_model=SecurityImpactResponse)
async def analyze_finding_security_impact(
    audit_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate an evidence-bound security impact analysis for one failed finding.
    Analysis is on-demand so normal audits remain deterministic and fast.
    """
    audit = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit run not found")

    finding = db.query(AuditFinding).filter(
        AuditFinding.id == finding_id,
        AuditFinding.audit_id == audit_id,
    ).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found in this audit")
    if finding.status != "FAIL":
        raise HTTPException(status_code=400, detail="Security impact analysis is available for failed findings only")

    device = db.query(Device).filter(Device.id == audit.device_id).first()
    config = db.query(Configuration).filter(Configuration.id == audit.config_id).first()

    finding_context = {
        "rule_id": finding.rule_id,
        "framework": finding.framework,
        "control_id": finding.control_id,
        "title": finding.title,
        "status": finding.status,
        "severity": finding.severity,
        "normalized_param": finding.normalized_param,
        "detected_value": finding.detected_value,
        "expected_value": finding.expected_value,
        "evidence_line_no": finding.evidence_line_no,
        "evidence_text": finding.evidence_text,
        "section_context": finding.section_context,
        "rationale": finding.rationale,
        "remediation_text": finding.remediation_text,
        "vendor": device.vendor if device else (config.vendor_detected if config else "UNKNOWN"),
        "hostname": device.hostname if device else (config.filename if config else "UNKNOWN"),
    }

    provider_name = resolve_ai_provider()
    provider = get_ai_provider()
    analysis = await provider.analyze_security_impact(finding_context)
    analysis["analysis_provider"] = provider_name
    return SecurityImpactResponse(**analysis)

@router.get("/{audit_id}", response_model=AuditRunResponse)
def get_audit(
    audit_id: int,
    framework: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    audit = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit run not found")

    device = db.query(Device).filter(Device.id == audit.device_id).first()
    cfg = db.query(Configuration).filter(Configuration.id == audit.config_id).first()

    query = db.query(AuditFinding).filter(AuditFinding.audit_id == audit.id)
    if framework:
        query = query.filter(AuditFinding.framework == framework)
    if status:
        query = query.filter(AuditFinding.status == status)
    if severity:
        query = query.filter(AuditFinding.severity == severity)

    findings = query.all()

    return AuditRunResponse(
        id=audit.id,
        device_id=audit.device_id,
        config_id=audit.config_id,
        timestamp=audit.timestamp,
        compliance_percentage=audit.compliance_percentage,
        risk_score=audit.risk_score,
        risk_level=audit.risk_level,
        total_controls=audit.total_controls,
        passed_count=audit.passed_count,
        failed_count=audit.failed_count,
        not_evaluable_count=audit.not_evaluable_count,
        unknown_count=audit.unknown_count,
        status=audit.status,
        device_hostname=device.hostname if device else "UNKNOWN",
        device_vendor=device.vendor if device else "UNKNOWN",
        filename=cfg.filename if cfg else "N/A",
        normalized_baseline=audit.normalized_baseline,
        findings=[AuditFindingResponse.from_orm(f) for f in findings]
    )
