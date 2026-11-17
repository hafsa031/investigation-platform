from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import CaseModel, EvidenceModel, UserModel, ForensicAnalysisModel
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/cases", tags=["Cases"])

def owned_case(case_id: UUID, user: UserModel, db: Session) -> CaseModel:
    case = db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.get("/", response_model=List[CaseResponse])
def get_cases(db: Session = Depends(get_db)):
    return db.query(CaseModel).all()

@router.delete("/{case_id}", status_code=status.HTTP_200_OK)
def delete_case(case_id: UUID, db: Session = Depends(get_db)):
    # Query the database for the case by its unique UUID
    case = db.query(CaseModel).filter(CaseModel.id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found."
        )
    
    # Delete the record from PostgreSQL and commit
    db.delete(case)
    db.commit()
    
    return {"message": f"Case {case_id} successfully deleted."}
@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(data: CaseCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = CaseModel(title=data.title, description=data.description, created_by=user.id, status="Open")
    db.add(case); db.commit(); db.refresh(case)
    return case

@router.get("/", response_model=list[CaseResponse])
def list_cases(db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    return db.query(CaseModel).filter(CaseModel.created_by == user.id).order_by(CaseModel.created_at.desc()).all()

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    return owned_case(case_id, user, db)

@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(case_id: UUID, data: CaseUpdate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = owned_case(case_id, user, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(case, key, value.value if hasattr(value, "value") else value)
    db.commit(); db.refresh(case)
    return case

@router.get("/{case_id}/stats")
def case_stats(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    evidence_count = db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).count()
    return {"case_id": str(case_id), "evidence_count": evidence_count}


@router.get("/{case_id}/findings")
def list_case_findings(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    analyses = db.query(ForensicAnalysisModel).filter(
        ForensicAnalysisModel.case_id == case_id
    ).order_by(ForensicAnalysisModel.created_at.desc()).all()
    findings = []
    for analysis in analyses:
        result = analysis.result or {}
        finding = result.get("forensic_finding") or {}
        if finding:
            findings.append({
                "id": str(analysis.id),
                **finding,
                "classification": analysis.classification,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            })
    return findings
