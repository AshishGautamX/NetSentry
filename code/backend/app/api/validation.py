from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import Configuration, LearnedMapping, ComplianceRule
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.normalizer import NormalizationEngine

router = APIRouter(prefix="/validation", tags=["Validation Mode"])

@router.get("/trace/{config_id}")
def get_validation_trace(config_id: int, db: Session = Depends(get_db)):
    """
    Validation Mode: returns full transparent trace through all pipeline layers:
    RAW LINE -> PARSED STRUCTURE -> SEMANTIC INTERPRETATION -> NORMALIZED PARAMETER ->
    EXTRACTED VALUE -> MATCHING RULES -> EVIDENCE TRACE.
    """
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    vendor = config.vendor_detected or "unknown"
    parser = get_parser_for_vendor(vendor)
    parsed_lines = parser.parse(config.sanitized_content)

    active_learned = db.query(LearnedMapping).filter(LearnedMapping.is_active == True).all()
    normalizer = NormalizationEngine()
    parsed_lines, canonical_baseline, unknown_candidates = normalizer.normalize(
        parsed_lines, vendor, active_learned
    )

    rules = db.query(ComplianceRule).all()
    rules_by_param: Dict[str, List[Dict[str, str]]] = {}
    for r in rules:
        if r.parameter not in rules_by_param:
            rules_by_param[r.parameter] = []
        rules_by_param[r.parameter].append({
            "rule_id": r.rule_id,
            "framework": r.framework,
            "expected_value": r.expected_value,
            "severity": r.severity
        })

    trace_steps = []
    for line in parsed_lines:
        if line.is_blank or line.is_comment:
            continue

        matching_rules = rules_by_param.get(line.normalized_param, []) if line.normalized_param else []

        trace_steps.append({
            "line_number": line.line_number,
            "raw_text": line.raw_text,
            "cleaned_text": line.cleaned_text,
            "section_context": line.section_context or "Global",
            "is_security_relevant": line.is_security_relevant,
            "normalized_param": line.normalized_param or "UNMAPPED",
            "extracted_value": str(line.extracted_value) if line.extracted_value is not None else None,
            "confidence": round(line.confidence * 100, 1) if line.confidence else 0.0,
            "mapping_source": line.mapping_source or "NONE",
            "is_learned_mapping": (line.mapping_source == "LEARNED_KNOWLEDGE_BASE"),
            "matching_rules_count": len(matching_rules),
            "matching_rules": matching_rules
        })

    return {
        "config_id": config.id,
        "filename": config.filename,
        "vendor_detected": vendor,
        "total_lines_analyzed": len(parsed_lines),
        "security_relevant_count": sum(1 for t in trace_steps if t["is_security_relevant"]),
        "steps": trace_steps
    }
