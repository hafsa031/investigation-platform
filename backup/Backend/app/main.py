from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app import models
from app.routers import auth, cases, evidence, entities, reports, events

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

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(entities.router)
app.include_router(reports.router)
app.include_router(events.router)

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": "2.0.0"}

@app.get("/health/db", tags=["Health"])
def database_health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
