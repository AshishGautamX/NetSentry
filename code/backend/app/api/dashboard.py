from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.models import Device, AuditRun, AuditFinding, Configuration, UnknownCommand
from backend.app.schemas.schemas import AuditRunResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Returns real-time computed statistics from actual database records.
    """
    total_devices = db.query(Device).count()
    total_audits = db.query(AuditRun).count()
    
    # Average compliance percentage across completed audits
    avg_comp = db.query(func.avg(AuditRun.compliance_percentage)).scalar() or 0.0
    
    # Severity breakdown across all findings of latest audits
    findings = db.query(AuditFinding).filter(AuditFinding.status == "FAIL").all()
    critical_count = sum(1 for f in findings if f.severity.upper() == "CRITICAL")
    high_count = sum(1 for f in findings if f.severity.upper() == "HIGH")
    medium_count = sum(1 for f in findings if f.severity.upper() == "MEDIUM")
    low_count = sum(1 for f in findings if f.severity.upper() == "LOW")

    # Framework distribution
    all_findings = db.query(AuditFinding).all()
    fw_map: Dict[str, Dict[str, int]] = {}
    for f in all_findings:
        fw = f.framework
        if fw not in fw_map:
            fw_map[fw] = {"pass": 0, "fail": 0, "not_evaluable": 0}
        if f.status == "PASS":
            fw_map[fw]["pass"] += 1
        elif f.status == "FAIL":
            fw_map[fw]["fail"] += 1
        else:
            fw_map[fw]["not_evaluable"] += 1

    # Vendor distribution
    vendors = db.query(Device.vendor, func.count(Device.id)).group_by(Device.vendor).all()
    vendor_dist = {v[0]: v[1] for v in vendors}

    # Unknown commands pending
    unknown_count = db.query(UnknownCommand).filter(UnknownCommand.status == "PENDING").count()

    # Recent audits
    recent_runs = db.query(AuditRun).order_by(AuditRun.timestamp.desc()).limit(5).all()
    recent_audits = []
    for a in recent_runs:
        dev = db.query(Device).filter(Device.id == a.device_id).first()
        cfg = db.query(Configuration).filter(Configuration.id == a.config_id).first()
        recent_audits.append({
            "id": a.id,
            "device_hostname": dev.hostname if dev else "UNKNOWN",
            "device_vendor": dev.vendor if dev else "UNKNOWN",
            "filename": cfg.filename if cfg else "N/A",
            "timestamp": a.timestamp,
            "compliance_percentage": a.compliance_percentage,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "passed_count": a.passed_count,
            "failed_count": a.failed_count,
            "not_evaluable_count": a.not_evaluable_count,
            "total_controls": a.total_controls,
            "status": a.status
        })

    return {
        "total_devices": total_devices,
        "total_audits": total_audits,
        "average_compliance_pct": round(float(avg_comp), 1),
        "critical_findings_count": critical_count,
        "high_findings_count": high_count,
        "medium_findings_count": medium_count,
        "low_findings_count": low_count,
        "framework_distribution": fw_map,
        "vendor_distribution": vendor_dist,
        "unknown_commands_count": unknown_count,
        "recent_audits": recent_audits
    }
