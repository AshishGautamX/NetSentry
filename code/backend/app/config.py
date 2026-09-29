import os
from pathlib import Path
from pydantic_settings import SettingsConfigDict
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DATA_DIR = Path(__file__).resolve().parent / "data"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

    PROJECT_NAME: str = "AI-Driven Multi-Vendor Network Security Compliance Auditor"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/network_auditor.db")
    
    # AI Provider Settings
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "deterministic")  # "deterministic" or "gemini"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # GitOps Webhook Settings (Milestone 2)
    # Set GITHUB_WEBHOOK_SECRET to the secret configured in your GitHub repo webhook settings.
    # Leave empty to disable HMAC signature validation (not recommended for production).
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    GITLAB_WEBHOOK_SECRET: str = os.getenv("GITLAB_WEBHOOK_SECRET", "")
    # Optional GitHub/GitLab PAT for fetching files from private repositories
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITLAB_TOKEN: str = os.getenv("GITLAB_TOKEN", "")

    # Risk weights
    RISK_WEIGHT_CRITICAL: float = 10.0
    RISK_WEIGHT_HIGH: float = 7.0
    RISK_WEIGHT_MEDIUM: float = 4.0
    RISK_WEIGHT_LOW: float = 2.0
    RISK_WEIGHT_INFO: float = 0.0

settings = Settings()
