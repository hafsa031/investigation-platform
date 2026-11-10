from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class CaseStatus(str, Enum):
    OPEN = "Open"
    UNDER_INVESTIGATION = "Under Investigation"
    CLOSED = "Closed"

class CaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None

class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    status: CaseStatus | None = None

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime

# 3. Evidence Metadata Schema (Includes SHA-256, type, size, timestamp)
class EvidenceMetadata(BaseModel):
    id: str
    case_id: str
    filename: str
    file_type: str
    sha256: str
    file_size_bytes: int
    uploaded_at: datetime

# 4. Finding Schemas
class FindingCreate(BaseModel):
    summary: str = Field(..., example="Unauthorized administrative login detected")
    severity: str = Field("medium", example="high")
    details: Optional[str] = Field(None, example="Login originated from untrusted IP block")

class FindingResponse(FindingCreate):
    id: str
    case_id: str
    created_at: datetime
