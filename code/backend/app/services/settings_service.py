import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models.models import SystemSetting

# Cached resolution state to avoid hitting the database on every low-level AI operation
_cached_state = {
    "valid": False,
    "gemini_api_key": None,
    "ai_provider": "deterministic",
    "key_source": "none"
}

def invalidate_cache() -> None:
    """Invalidates the in-memory settings resolution cache."""
    _cached_state["valid"] = False
    _cached_state["gemini_api_key"] = None
    _cached_state["ai_provider"] = "deterministic"
    _cached_state["key_source"] = "none"

def get_setting(key: str, db: Optional[Session] = None) -> Optional[str]:
    """Retrieves a setting value from the database."""
    if db is not None:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        return setting.value if setting else None
    
    session = SessionLocal()
    try:
        setting = session.query(SystemSetting).filter(SystemSetting.key == key).first()
        return setting.value if setting else None
    finally:
        session.close()

def set_setting(key: str, value: Optional[str], db: Optional[Session] = None) -> None:
    """Sets or updates a setting in the database and invalidates the resolution cache."""
    def _do_set(sess: Session):
        setting = sess.query(SystemSetting).filter(SystemSetting.key == key).first()
        if value is None or not value.strip():
            if setting:
                sess.delete(setting)
                sess.commit()
        else:
            if not setting:
                setting = SystemSetting(key=key, value=value.strip())
                sess.add(setting)
            else:
                setting.value = value.strip()
            sess.commit()

    if db is not None:
        _do_set(db)
    else:
        session = SessionLocal()
        try:
            _do_set(session)
        finally:
            session.close()

    invalidate_cache()

def delete_setting(key: str, db: Optional[Session] = None) -> None:
    """Deletes a setting from the database and invalidates the resolution cache."""
    def _do_del(sess: Session):
        setting = sess.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            sess.delete(setting)
            sess.commit()

    if db is not None:
        _do_del(db)
    else:
        session = SessionLocal()
        try:
            _do_del(session)
        finally:
            session.close()

    invalidate_cache()

def resolve_gemini_api_key(db: Optional[Session] = None, use_cache: bool = True) -> Optional[str]:
    """
    Answers: Which Gemini API key should be used?
    Precedence:
    1. Saved Settings DB key (if non-empty)
    2. .env / environment variable GEMINI_API_KEY (if non-empty)
    3. None
    Empty strings or whitespace-only strings are treated as not configured.
    """
    global _cached_state
    if use_cache and _cached_state["valid"] and db is None:
        return _cached_state["gemini_api_key"]

    # 1. Check Settings DB
    db_val = get_setting("gemini_api_key", db)
    if db_val and db_val.strip():
        resolved = db_val.strip()
        source = "settings"
    else:
        # 2. Check .env / environment variable
        env_val = os.getenv("GEMINI_API_KEY", "").strip() or getattr(settings, "GEMINI_API_KEY", "").strip()
        if env_val:
            resolved = env_val
            source = "env"
        else:
            resolved = None
            source = "none"

    if db is None:
        _cached_state["gemini_api_key"] = resolved
        _cached_state["key_source"] = source

    return resolved

def resolve_ai_provider(db: Optional[Session] = None, use_cache: bool = True) -> str:
    """
    Answers: Should the application use Gemini or deterministic mode?
    Precedence & Logic:
    1. Check explicitly saved Settings DB 'ai_provider':
       - 'deterministic' -> 'deterministic'
       - 'gemini' -> 'gemini' if a Gemini key resolves, else 'deterministic'
    2. Fallback to deployment-level environment:
       - If AI_PROVIDER == 'gemini' in env or GEMINI_API_KEY is configured (and provider not forced deterministic),
         select 'gemini' if a key resolves.
       - Otherwise 'deterministic'.
    """
    global _cached_state
    if use_cache and _cached_state["valid"] and db is None:
        return _cached_state["ai_provider"]

    resolved_key = resolve_gemini_api_key(db, use_cache=False)

    # 1. Check DB setting
    db_provider = get_setting("ai_provider", db)
    if db_provider and db_provider.strip():
        prov = db_provider.strip().lower()
        if prov == "deterministic":
            chosen = "deterministic"
        elif prov == "gemini":
            chosen = "gemini" if resolved_key else "deterministic"
        else:
            chosen = "deterministic"
    else:
        # 2. Check env
        env_provider = os.getenv("AI_PROVIDER", getattr(settings, "AI_PROVIDER", "deterministic")).strip().lower()
        if env_provider == "gemini":
            chosen = "gemini" if resolved_key else "deterministic"
        elif resolved_key:
            chosen = "gemini"
        else:
            chosen = "deterministic"

    if db is None:
        _cached_state["ai_provider"] = chosen
        _cached_state["valid"] = True

    return chosen

def mask_api_key(key: Optional[str]) -> str:
    """Masks an API key for safe public representation without exposing secrets."""
    if not key or not key.strip():
        return ""
    k = key.strip()
    if len(k) <= 8:
        return "********"
    return f"{k[:6]}********{k[-4:]}"

def get_system_settings_summary(db: Optional[Session] = None) -> Dict[str, Any]:
    """Generates a summary of the current settings without leaking any raw secret."""
    resolved_key = resolve_gemini_api_key(db, use_cache=False)
    resolved_provider = resolve_ai_provider(db, use_cache=False)

    # Determine key source
    db_val = get_setting("gemini_api_key", db)
    if db_val and db_val.strip():
        key_source = "settings"
    else:
        env_val = os.getenv("GEMINI_API_KEY", "").strip() or getattr(settings, "GEMINI_API_KEY", "").strip()
        if env_val:
            key_source = "env"
        else:
            key_source = "none"

    db_provider = get_setting("ai_provider", db)
    display_provider = db_provider.strip().lower() if db_provider and db_provider.strip() else resolved_provider

    return {
        "ai_provider": display_provider,
        "gemini_api_key_configured": resolved_key is not None,
        "gemini_api_key_masked": mask_api_key(resolved_key),
        "gemini_api_key_source": key_source,
    }
