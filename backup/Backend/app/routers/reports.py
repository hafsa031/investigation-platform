from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import ReportModel, CaseModel, UserModel
from app.schemas.reports import ReportCreate, ReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(data: ReportCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = db.query(CaseModel).filter(CaseModel.id == data.case_id, CaseModel.created_by == user.id).first()
    if not case: raise HTTPException(status_code=404, detail="Case not found")
    obj = ReportModel(case_id=data.case_id, created_by=user.id, title=data.title,
                      report_type=data.report_type, summary=data.summary,
                      storage_key=data.storage_key, status="draft")
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/case/{case_id}", response_model=list[ReportResponse])
def list_reports(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    if not db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first():
        raise HTTPException(status_code=404, detail="Case not found")
    return db.query(ReportModel).filter(ReportModel.case_id == case_id).order_by(ReportModel.created_at.desc()).all()
