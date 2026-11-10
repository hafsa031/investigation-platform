from uuid import UUID
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuditLogModel, UserModel

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

class AuditLogCreate(BaseModel):
    action: str = Field(min_length=1, max_length=160)
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: UUID | None = None
    details: dict[str, Any] | None = None

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime

@router.post("/", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
def create_audit_log(data: AuditLogCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    entry = AuditLogModel(user_id=user.id, action=data.action, resource_type=data.resource_type,
                          resource_id=data.resource_id, details=data.details)
    db.add(entry); db.commit(); db.refresh(entry)
    return entry

@router.get("/me", response_model=list[AuditLogResponse])
def list_my_audit_logs(limit: int = 100, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500")
    return db.query(AuditLogModel).filter(AuditLogModel.user_id == user.id).order_by(AuditLogModel.created_at.desc()).limit(limit).all()
