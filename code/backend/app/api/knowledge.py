from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import LearnedMapping
from backend.app.schemas.schemas import LearnedMappingResponse

router = APIRouter(prefix="/knowledge", tags=["Adaptive Knowledge Base"])

@router.get("", response_model=List[LearnedMappingResponse])
def list_knowledge_base(db: Session = Depends(get_db)):
    """
    Returns all persistent learned mappings in the Adaptive Knowledge Base.
    """
    return db.query(LearnedMapping).order_by(LearnedMapping.created_at.desc()).all()

@router.post("/{mapping_id}/toggle", response_model=LearnedMappingResponse)
def toggle_mapping_active(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(LearnedMapping).filter(LearnedMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    mapping.is_active = not mapping.is_active
    db.commit()
    db.refresh(mapping)
    return mapping

@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(LearnedMapping).filter(LearnedMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    db.delete(mapping)
    db.commit()
    return {"status": "success", "message": f"Mapping {mapping_id} deleted successfully"}
