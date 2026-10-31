from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import ReportModel, CaseModel
from app.schemas.reports import ReportCreate, ReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    case = db.query(CaseModel).filter(CaseModel.id == report.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    db_report = ReportModel(
        case_id=report.case_id,
        created_by=case.created_by,
        title=report.title,
        report_type=report.report_type,
        summary=report.summary,
        storage_key=report.storage_key,
        status="draft"
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router.get("/case/{case_id}", response_model=List[ReportResponse])
def get_reports_by_case(case_id: UUID, db: Session = Depends(get_db)):
    return db.query(ReportModel).filter(ReportModel.case_id == case_id).all()