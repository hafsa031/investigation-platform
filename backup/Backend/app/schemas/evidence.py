from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: UUID
    uploaded_by: UUID
    filename: str
    storage_key: str
    mime_type: str | None
    size_bytes: int | None
    description: str | None
    acquisition_source: str | None
    created_at: datetime

class EvidenceAnalysisResponse(BaseModel):
    evidence_id: UUID
    case_id: UUID
    status: str
    result: dict
