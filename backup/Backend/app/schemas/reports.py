from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ReportCreate(BaseModel):
    case_id: UUID
    title: str = Field(min_length=2, max_length=200)
    report_type: str = "investigation_summary"
    summary: str | None = None
    storage_key: str | None = None

class ReportResponse(ReportCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by: UUID
    status: str
    created_at: datetime
