"""Main FastAPI application for Jagspire AI Investigation Platform."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.openapi.utils import get_openapi

# Import all routers
from backend.app.ioc.api import router as ioc_router
from backend.app.case_management import router as case_router
from backend.app.evidence_management import router as evidence_router
from backend.app.investigation import router as investigation_router

app = FastAPI(
    title="Jagspire AI Investigation Platform",
    description="""
    ## Jagspire AI Evidence Correlation & Digital Investigation Platform
    
    A comprehensive platform for digital investigation workflows including:
    - Case Management
    - Evidence Upload and Processing  
    - Forensic Analysis
    - IOC Extraction and Correlation
    - Investigation Dashboard
    
    ## Features
    
    * **Case Management**: Create, read, update, delete investigations
    * **Evidence Handling**: Upload, process, and analyze digital evidence
    * **Forensic Analysis**: Extract metadata, hashes, timeline events
    * **IOC Extraction**: Defang-aware regex extraction with scoring
    * **Threat Intelligence**: MITRE ATT&CK mapping and threat correlation
    * **AI Enhancement**: Opt-in Groq LLM reranking (fail-open to heuristic)
    
    ## Authentication
    
    Currently uses fail-open authentication for development. In production,
    integrate with proper JWT/OAuth2 validation.
    
    ## Data Handling
    
    All sample data is synthetic (RFC5737 IPs, example.* domains, computed hashes)
    as per platform requirements.
    """,
    version="1.0.0",
    contact={
        "name": "Jagspire AI Platform Team",
        "url": "https://jagspire.ai/platform",
        "email": "platform@jagspire.ai",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://jagspire.ai/licensing",
    },
    # Disable default docs to customize
    docs_url=None,
    redoc_url=None,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Jagspire AI Investigation Platform API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Apply security globally
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Custom docs endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": "jagspire-ai-platform",
        "version": "1.0.0",
        "timestamp": "2026-09-18T12:59:28Z"
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Jagspire AI Investigation Platform",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api_v1_prefix": "/api/v1"
    }


# Include all routers with API version prefix
app.include_router(case_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(investigation_router, prefix="/api/v1")
app.include_router(ioc_router, prefix="/api/v1")
