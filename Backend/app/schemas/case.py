from pydantic import BaseModel
from typing import Optional

class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str