from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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
    description="Backend API services for Jagspire AI Product Development Team",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)

# Include All Feature Routers mapped to the ER Diagram
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(entities.router)
app.include_router(reports.router)
app.include_router(events.router)

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Jagspire AI Investigation Backend API is running with full 10-table PostgreSQL architecture."}