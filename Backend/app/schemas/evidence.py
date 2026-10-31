from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class EvidenceCreate(BaseModel):
    case_id: UUID
    filename: str
    storage_key: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    description: Optional[str] = None
    acquisition_source: Optional[str] = None

class EvidenceResponse(EvidenceCreate):
    id: UUID
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True