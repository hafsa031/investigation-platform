from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime

# 1. Restrict case status according to requirements
class CaseStatus(str, Enum):
    OPEN = "Open"
    UNDER_INVESTIGATION = "Under Investigation"
    CLOSED = "Closed"

# 2. Case Schemas
class CaseCreate(BaseModel):
    title: str = Field(..., example="Suspicious Network Intrusion")
    description: Optional[str] = Field(None, example="Investigating abnormal outgoing traffic")

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None

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