<<<<<<< Updated upstream
import sys
from pathlib import Path
from fastapi import FastAPI
=======
from fastapi import FastAPI, Request
>>>>>>> Stashed changes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import settings
<<<<<<< Updated upstream
from app.core.exceptions import global_exception_handler
from app.routers import auth, cases

# Path resolution:
# ROOT_DIR is "Investigation Platform"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Point sys.path to "Security/CyberSecurity" so Python can resolve "backend.app.ioc..."
CYBERSECURITY_DIR = ROOT_DIR / "Security" / "CyberSecurity"
sys.path.append(str(CYBERSECURITY_DIR))

# Import teammate's IOC router
from backend.app.ioc.api import router as ioc_router

=======
from app.database import engine
from app import models
from app.routers import auth, cases, evidence, entities, reports, events, audit
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
# 1. Auth Router
=======
>>>>>>> Stashed changes
app.include_router(auth.router)

# 2. Cases, Evidence & Investigation Router
app.include_router(cases.router)
<<<<<<< Updated upstream

# 3. Integrated IOC Threat Analysis Router
# Clean inclusion (uses the router's existing tag):
app.include_router(ioc_router, prefix="/ioc")


@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Jagspire AI Investigation Backend API is running."}
=======
app.include_router(evidence.router)
app.include_router(entities.router)
app.include_router(reports.router)
app.include_router(events.router)
app.include_router(audit.router)

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": "2.0.0"}

@app.get("/health/db", tags=["Health"])
def database_health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
>>>>>>> Stashed changes
