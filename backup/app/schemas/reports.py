from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ReportCreate(BaseModel):
    case_id: UUID
    title: str
    report_type: Optional[str] = "investigation_summary"
    summary: Optional[str] = None
    storage_key: Optional[str] = None

class ReportResponse(ReportCreate):
    id: UUID
    created_by: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True