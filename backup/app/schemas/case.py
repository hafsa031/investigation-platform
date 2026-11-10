from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime
from uuid import UUID

# 1. Restrict case status according to requirements
class CaseStatus(str, Enum):
    OPEN = "Open"
    UNDER_INVESTIGATION = "Under Investigation"
    CLOSED = "Closed"

# 2. Case Schemas
class CaseCreate(BaseModel):
    title: str = Field(..., example="Suspicious Network Intrusion")
    description: Optional[str] = Field(None, example="Investigating abnormal outgoing traffic")
    created_by: UUID  # Required to link the case to the user in PostgreSQL

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None

class CaseResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: CaseStatus
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# 3. Evidence Metadata Schema
class EvidenceMetadata(BaseModel):
    id: UUID
    case_id: UUID
    filename: str
    file_type: str
    sha256: str
    file_size_bytes: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

# 4. Finding Schemas
class FindingCreate(BaseModel):
    summary: str = Field(..., example="Unauthorized administrative login detected")
    severity: str = Field("medium", example="high")
    details: Optional[str] = Field(None, example="Login originated from untrusted IP block")

class FindingResponse(FindingCreate):
    id: UUID
    case_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True