from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import ComplianceRule
from backend.app.schemas.schemas import ComplianceRuleResponse

router = APIRouter(prefix="/compliance", tags=["Compliance Frameworks & Rules"])

@router.get("/rules", response_model=List[ComplianceRuleResponse])
def list_rules(
    framework: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    parameter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ComplianceRule)
    if framework:
        query = query.filter(ComplianceRule.framework == framework)
    if severity:
        query = query.filter(ComplianceRule.severity == severity)
    if parameter:
        query = query.filter(ComplianceRule.parameter == parameter)
    return query.all()

@router.get("/frameworks")
def list_frameworks(db: Session = Depends(get_db)):
    """
    Returns supported compliance frameworks and their control counts.
    """
    rules = db.query(ComplianceRule).all()
    framework_map = {}
    for r in rules:
        if r.framework not in framework_map:
            framework_map[r.framework] = {
                "name": r.framework,
                "version": r.framework_version,
                "total_controls": 0,
                "severities": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            }
        framework_map[r.framework]["total_controls"] += 1
        sev = r.severity.upper()
        if sev in framework_map[r.framework]["severities"]:
            framework_map[r.framework]["severities"][sev] += 1

    return list(framework_map.values())
