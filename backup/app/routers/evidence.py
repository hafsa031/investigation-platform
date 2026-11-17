from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import EvidenceModel, CaseModel
from app.schemas.evidence import EvidenceCreate, EvidenceResponse

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.post("/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_evidence(evidence: EvidenceCreate, db: Session = Depends(get_db)):
    # Verify case exists
    case = db.query(CaseModel).filter(CaseModel.id == evidence.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    db_evidence = EvidenceModel(
        case_id=evidence.case_id,
        uploaded_by=case.created_by, # Fallback to case creator or authenticated user ID
        filename=evidence.filename,
        storage_key=evidence.storage_key,
        mime_type=evidence.mime_type,
        size_bytes=evidence.size_bytes,
        description=evidence.description,
        acquisition_source=evidence.acquisition_source
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence

@router.get("/case/{case_id}", response_model=List[EvidenceResponse])
def get_evidence_by_case(case_id: UUID, db: Session = Depends(get_db)):
    return db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).all()