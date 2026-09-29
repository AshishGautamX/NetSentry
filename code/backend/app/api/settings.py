from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.settings_service import (
    get_system_settings_summary,
    set_setting,
    delete_setting,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdateRequest(BaseModel):
    ai_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None


@router.get("", response_model=Dict[str, Any])
def get_settings(db: Session = Depends(get_db)):
    """
    Returns public settings status and masked API key summary.
    Never exposes raw secrets.
    """
    return get_system_settings_summary(db)


@router.post("", response_model=Dict[str, Any])
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    """
    Updates system settings in persistent storage.
    Saved Settings values take runtime precedence over .env fallbacks.
    """
    if payload.ai_provider is not None:
        provider = payload.ai_provider.strip().lower()
        if provider not in ("deterministic", "gemini"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ai_provider must be 'deterministic' or 'gemini'"
            )
        set_setting("ai_provider", provider, db)

    if payload.gemini_api_key is not None:
        key = payload.gemini_api_key.strip()
        if not key:
            # Empty or whitespace: clear the saved DB key
            delete_setting("gemini_api_key", db)
        elif "*" in key:
            # Client sent back the masked representation; preserve existing stored key
            pass
        else:
            set_setting("gemini_api_key", key, db)

    return {
        "status": "success",
        "message": "Settings saved successfully",
        "settings": get_system_settings_summary(db)
    }


@router.delete("/gemini-key", response_model=Dict[str, Any])
def clear_saved_gemini_key(db: Session = Depends(get_db)):
    """
    Clears the saved Gemini API key from the database.
    If a .env GEMINI_API_KEY exists, the system gracefully falls back to it.
    Otherwise, falls back to deterministic offline mode.
    """
    delete_setting("gemini_api_key", db)
    return {
        "status": "success",
        "message": "Saved Gemini API key cleared successfully",
        "settings": get_system_settings_summary(db)
    }
