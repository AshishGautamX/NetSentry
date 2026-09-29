import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import AuditRun, AuditFinding, Device, Configuration
from backend.app.engine.reporting import PDFReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/{audit_id}/pdf")
def download_pdf_report(audit_id: int, db: Session = Depends(get_db)):
    """
    Generates and streams a professional compliance audit PDF report for an audited device.
    """
    audit = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit run not found")

    device = db.query(Device).filter(Device.id == audit.device_id).first()
    cfg = db.query(Configuration).filter(Configuration.id == audit.config_id).first()
    findings = db.query(AuditFinding).filter(AuditFinding.audit_id == audit.id).all()

    device_info = {
        "hostname": device.hostname if device else "UNKNOWN",
        "vendor": device.vendor if device else "UNKNOWN",
        "model": device.model if device else "N/A",
        "os_version": device.os_version if device else "N/A"
    }

    audit_info = {
        "id": audit.id,
        "filename": cfg.filename if cfg else "N/A",
        "compliance_percentage": audit.compliance_percentage,
        "risk_score": audit.risk_score,
        "risk_level": audit.risk_level,
        "total_controls": audit.total_controls,
        "passed_count": audit.passed_count,
        "failed_count": audit.failed_count,
        "not_evaluable_count": audit.not_evaluable_count,
        "unknown_count": audit.unknown_count
    }

    findings_list = [
        {
            "rule_id": f.rule_id,
            "framework": f.framework,
            "control_id": f.control_id,
            "title": f.title,
            "status": f.status,
            "severity": f.severity,
            "normalized_param": f.normalized_param,
            "detected_value": f.detected_value,
            "expected_value": f.expected_value,
            "evidence_line_no": f.evidence_line_no,
            "evidence_text": f.evidence_text,
            "remediation_text": f.remediation_text,
            "is_learned_mapping_applied": f.is_learned_mapping_applied
        }
        for f in findings
    ]

    pdf_buffer = io.BytesIO()
    PDFReportGenerator.generate_report(device_info, audit_info, findings_list, pdf_buffer)
    pdf_buffer.seek(0)

    filename = f"Compliance_Audit_{device_info['hostname']}_Audit_{audit.id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
