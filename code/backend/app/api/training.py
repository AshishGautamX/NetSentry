import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import UnknownCommand, LearnedMapping
from backend.app.schemas.schemas import UnknownCommandResponse, MappingCreateRequest, LearnedMappingResponse

router = APIRouter(prefix="/training", tags=["Training Center"])

@router.get("/unknown", response_model=List[UnknownCommandResponse])
def list_unknown_commands(status: Optional[str] = "PENDING", db: Session = Depends(get_db)):
    """
    Retrieves unmapped network configuration commands flagged for human-in-the-loop review.
    """
    query = db.query(UnknownCommand)
    if status and status != "ALL":
        query = query.filter(UnknownCommand.status == status)
    return query.order_by(UnknownCommand.created_at.desc()).all()

@router.post("/mapping", response_model=LearnedMappingResponse)
def create_mapping_from_training(
    req: MappingCreateRequest,
    unknown_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Allows an administrator to map an unknown command syntax to a normalized security parameter.
    Persists the mapping into the Adaptive Knowledge Base for automatic reuse on future scans.
    """
    # Validate regex pattern
    try:
        re.compile(req.command_pattern)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regular expression pattern: {e}")

    learned_mapping = LearnedMapping(
        vendor=req.vendor,
        command_pattern=req.command_pattern,
        normalized_param=req.normalized_param,
        semantic_category=req.semantic_category,
        value_type=req.value_type,
        extraction_regex=req.extraction_regex,
        description=req.description or "Administrator trained mapping",
        source="HUMAN_TRAINING",
        confidence=1.0,
        is_active=True
    )
    db.add(learned_mapping)

    if unknown_id:
        uc = db.query(UnknownCommand).filter(UnknownCommand.id == unknown_id).first()
        if uc:
            uc.status = "MAPPED"

    db.commit()
    db.refresh(learned_mapping)
    return learned_mapping

@router.post("/ignore/{unknown_id}")
def ignore_unknown_command(unknown_id: int, db: Session = Depends(get_db)):
    uc = db.query(UnknownCommand).filter(UnknownCommand.id == unknown_id).first()
    if not uc:
        raise HTTPException(status_code=404, detail="Unknown command not found")
    uc.status = "IGNORED"
    db.commit()
    return {"status": "success", "message": f"Command {unknown_id} marked as ignored"}
