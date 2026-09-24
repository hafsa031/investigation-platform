import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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

# 1. Auth Router
app.include_router(auth.router)

# 2. Cases, Evidence & Investigation Router
app.include_router(cases.router)

# 3. Integrated IOC Threat Analysis Router
app.include_router(ioc_router, prefix="/ioc", tags=["Cybersecurity Module"])


@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Jagspire AI Investigation Backend API is running."}