import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings, APP_DATA_DIR
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.models import ComplianceRule, LearnedMapping
from backend.app.api import (
    configurations,
    audits,
    devices,
    compliance,
    training,
    knowledge,
    reports,
    validation,
    dashboard,
    webhooks,
    ssh_devices,
    settings as settings_api,
)

def init_db_and_seed():
    """
    Creates tables and seeds default compliance rules and base mappings if table is empty.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed compliance rules from JSON catalogs
        rules_dir = APP_DATA_DIR / "rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*.json"):
                with open(rule_file, "r", encoding="utf-8") as f:
                    rules_list = json.load(f)
                    for r in rules_list:
                        existing = db.query(ComplianceRule).filter(ComplianceRule.rule_id == r["rule_id"]).first()
                        if not existing:
                            rule_entry = ComplianceRule(
                                rule_id=r["rule_id"],
                                framework=r["framework"],
                                framework_version=r.get("framework_version", ""),
                                control_id=r["control_id"],
                                title=r["title"],
                                description=r["description"],
                                parameter=r["parameter"],
                                operator=r["operator"],
                                expected_value=str(r["expected_value"]),
                                severity=r["severity"],
                                category=r.get("category", "General"),
                                rationale=r.get("rationale", "")
                            )
                            db.add(rule_entry)
            db.commit()

        # Seed initial learned mappings
        init_map_file = APP_DATA_DIR / "initial_mappings.json"
        if init_map_file.exists():
            with open(init_map_file, "r", encoding="utf-8") as f:
                map_list = json.load(f)
                for m in map_list:
                    existing = db.query(LearnedMapping).filter(
                        LearnedMapping.vendor == m["vendor"],
                        LearnedMapping.command_pattern == m["command_pattern"]
                    ).first()
                    if not existing:
                        mapping_entry = LearnedMapping(
                            vendor=m["vendor"],
                            command_pattern=m["command_pattern"],
                            normalized_param=m["normalized_param"],
                            semantic_category=m.get("semantic_category", "General"),
                            value_type=m.get("value_type", "string"),
                            description=m.get("description", "Seeded baseline mapping"),
                            source="SEEDED",
                            confidence=0.98,
                            is_active=True
                        )
                        db.add(mapping_entry)
            db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_and_seed()
    yield

# Also initialize immediately on module load
init_db_and_seed()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Real-world multi-vendor network security compliance auditor for SIH 2026 Problem Statement 26155",
    lifespan=lifespan
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: configure specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(configurations.router, prefix=settings.API_V1_STR)
app.include_router(audits.router, prefix=settings.API_V1_STR)
app.include_router(devices.router, prefix=settings.API_V1_STR)
app.include_router(compliance.router, prefix=settings.API_V1_STR)
app.include_router(training.router, prefix=settings.API_V1_STR)
app.include_router(knowledge.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(validation.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)
app.include_router(ssh_devices.router, prefix=settings.API_V1_STR)
app.include_router(settings_api.router, prefix=settings.API_V1_STR)

from fastapi.staticfiles import StaticFiles
from backend.app.config import BASE_DIR
from backend.app.services.settings_service import resolve_ai_provider

sample_dir = BASE_DIR / "sample_configs"
if sample_dir.exists():
    app.mount("/sample_configs", StaticFiles(directory=str(sample_dir)), name="sample_configs")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "ai_provider": resolve_ai_provider()
    }
