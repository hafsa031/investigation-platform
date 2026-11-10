import sys
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine, get_db
from app.dependencies import get_current_user
from app import models
from app.routers import auth, cases, evidence, entities, reports, events, audit

# Path resolution:
# ROOT_DIR is "Investigation Platform"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Point sys.path to "Security/CyberSecurity" so Python can resolve "backend.app.ioc..."
CYBERSECURITY_DIR = ROOT_DIR / "Security" / "CyberSecurity"
sys.path.append(str(CYBERSECURITY_DIR))
from app.core.exceptions import global_exception_handler
from app.routers import auth, cases, evidence, entities, reports, events
from app.database import engine
from app import models

# Explicitly import all 10 models so SQLAlchemy registers and creates them in PostgreSQL
from app.models import (
    UserModel,
    CaseModel,
    EvidenceModel,
    EvidenceHashModel,
    EventModel,
    TimelineEventModel,
    EntityModel,
    RelationshipModel,
    ReportModel,
    AuditLogModel
)

# Initialize database tables for all 10 models in PostgreSQL
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Investigation, evidence management and forensic analysis API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def initialize_database():
    # Creates missing tables only. Existing schema changes require migrations.
    models.Base.metadata.create_all(bind=engine)
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Do not expose SQL, filesystem paths, credentials or stack traces to clients.
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# 1. Auth Router
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 2. Cases, Evidence & Investigation Routers
# Include All Feature Routers mapped to the ER Diagram
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(entities.router)
app.include_router(reports.router)
app.include_router(events.router)
app.include_router(audit.router)

# 3. Direct Global Findings Endpoint for Frontend UI Compatibility
@app.get("/cases/{case_id}/findings", tags=["Findings"])
def get_global_case_findings(case_id: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    case = db.query(models.CaseModel).filter(models.CaseModel.id == case_id, models.CaseModel.created_by == user.id).first()
    if not case:
        return []
    
    findings = db.query(models.EventModel).filter(
        models.EventModel.case_id == case_id,
        models.EventModel.event_type.in_(["forensic_finding", "file_system", "forensic"])
    ).order_by(models.EventModel.occurred_at.desc()).all()
    
    return [
        {
            "id": str(f.id),
            "title": f.description[:50] if f.description else "Forensic Finding",
            "description": f.description,
            "severity": "Info",
            "timestamp": f.occurred_at
        }
        for f in findings
    ]

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": "2.0.0"}

@app.get("/health/db", tags=["Health"])
def database_health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Jagspire AI Investigation Backend API is running with full 10-table PostgreSQL architecture."}
