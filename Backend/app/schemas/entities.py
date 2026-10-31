from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class EntityCreate(BaseModel):
    case_id: UUID
    entity_type: str  # e.g., IP, Domain, Person
    name: str
    normalized_name: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class EntityResponse(EntityCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class RelationshipCreate(BaseModel):
    case_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    description: Optional[str] = None
    confidence: Optional[float] = 1.0

class RelationshipResponse(RelationshipCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True