from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class CaseStatus(str, Enum):
    OPEN = "Open"
    UNDER_INVESTIGATION = "Under Investigation"
    CLOSED = "Closed"

class CaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    title: str = Field(..., example="Suspicious Network Intrusion")
    description: Optional[str] = Field(None, example="Investigating abnormal outgoing traffic")
    created_by: UUID  # Required to link the case to the user in PostgreSQL

class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    status: CaseStatus | None = None

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
    id: str
    case_id: str
    created_at: datetime
    id: UUID
    case_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
