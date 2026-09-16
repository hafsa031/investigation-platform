# Backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import global_exception_handler
from app.routers import auth, cases, evidence, analysis
from app.ioc.api import router as ioc_router

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

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(analysis.router)
app.include_router(ioc_router)


@app.get("/")
async def root():
    return {
        "message": "Jagspire AI Investigation Backend API is running."
    }