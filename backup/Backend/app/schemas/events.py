from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Any

class EventCreate(BaseModel):
    case_id: UUID
    source_evidence_id: UUID | None = None
    event_type: str
    description: str | None = None
    occurred_at: datetime
    source_timezone: str = "UTC"
    attributes: dict[str, Any] | None = None

class EventResponse(EventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime

class TimelineEventCreate(BaseModel):
    case_id: UUID
    event_id: UUID
    timestamp: datetime
    source_timezone: str = "UTC"
    label: str
    notes: str | None = None

class TimelineEventResponse(TimelineEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
