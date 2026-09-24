"""Case Management API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["cases"])

# In-memory storage (replace with database in production)
_CASES: dict[str, dict] = {}


# Pydantic models
class CaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    analyst: Optional[str] = None


class CaseCreate(CaseBase):
    tenant_id: uuid.UUID


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    analyst: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(open|in_progress|closed|archived)$")


class CaseResponse(CaseBase):
    id: str
    tenant_id: str
    case_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0
    finding_count: int = 0
    ioc_count: int = 0


class CaseListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Dependency
def _get_tenant_id(authorization: Optional[str] = Header(default=None)) -> uuid.UUID:
    """Extract tenant ID from auth header (simplified for demo)."""
    # In production, validate JWT and extract tenant_id
    # For demo, generate a consistent ID based on auth or use default
    if authorization and authorization.startswith("Bearer "):
        # Simple hash of token for demo consistency
        import hashlib
        token_hash = hashlib.md5(authorization.encode()).hexdigest()
        return uuid.UUID(token_hash[:32])
    # Default tenant for demo
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


# Endpoints
@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    tenant_id: uuid.UUID = Depends(_get_tenant_id)
):
    """Create a new investigation case."""
    case_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    case_record = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "case_id": case_id,
        "title": case_data.title,
        "description": case_data.description,
        "priority": case_data.priority,
        "analyst": case_data.analyst or "System",
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "evidence_count": 0,
        "finding_count": 0,
        "ioc_count": 0
    }
    
    _CASES[case_id] = case_record
    return CaseResponse(**case_record)


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(_get_tenant_id)
):
    """List cases with pagination."""
    # Filter by tenant
    tenant_cases = [
        case for case in _CASES.values() 
        if case["tenant_id"] == str(tenant_id)
    ]
    
    total = len(tenant_cases)
    start = (page - 1) * page_size
    end = start + page_size
    pages = (total + page_size - 1) // page_size
    
    cases = [
        CaseResponse(**case) 
        for case in tenant_cases[start:end]
    ]
    
    return CaseListResponse(
        cases=cases,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    tenant_id: uuid.UUID = Depends(_get_tenant_id)
):
    """Get a specific case by ID."""
    if case_id not in _CASES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    case = _CASES[case_id]
    if case["tenant_id"] != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    
    return CaseResponse(**case)


@router.put("/cases/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    tenant_id: uuid.UUID = Depends(_get_tenant_id)
):
    """Update a case."""
    if case_id not in _CASES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    case = _CASES[case_id]
    if case["tenant_id"] != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    
    # Update fields
    update_data = case_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            case[field] = value
    
    case["updated_at"] = datetime.utcnow()
    _CASES[case_id] = case
    
    return CaseResponse(**case)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    tenant_id: uuid.UUID = Depends(_get_tenant_id)
):
    """Delete a case."""
    if case_id not in _CASES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    case = _CASES[case_id]
    if case["tenant_id"] != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )
    
    del _CASES[case_id]
    return None
