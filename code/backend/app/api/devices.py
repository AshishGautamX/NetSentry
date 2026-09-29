from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import Device, AuditRun
from backend.app.schemas.schemas import DeviceResponse

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.get("", response_model=List[DeviceResponse])
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    results = []
    for d in devices:
        last_audit = db.query(AuditRun).filter(AuditRun.device_id == d.id).order_by(AuditRun.timestamp.desc()).first()
        results.append(DeviceResponse(
            id=d.id,
            hostname=d.hostname,
            vendor=d.vendor,
            model=d.model,
            os_version=d.os_version,
            serial_number=d.serial_number,
            created_at=d.created_at,
            last_compliance_score=last_audit.compliance_percentage if last_audit else None,
            last_risk_score=last_audit.risk_score if last_audit else None
        ))
    return results

@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(device_id: int, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    last_audit = db.query(AuditRun).filter(AuditRun.device_id == d.id).order_by(AuditRun.timestamp.desc()).first()
    return DeviceResponse(
        id=d.id,
        hostname=d.hostname,
        vendor=d.vendor,
        model=d.model,
        os_version=d.os_version,
        serial_number=d.serial_number,
        created_at=d.created_at,
        last_compliance_score=last_audit.compliance_percentage if last_audit else None,
        last_risk_score=last_audit.risk_score if last_audit else None
    )
