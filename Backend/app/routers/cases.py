from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from datetime import datetime
import uuid
import hashlib
import sys
from pathlib import Path
import shutil

FORENSIC_DIR = Path(__file__).resolve().parents[3] / "Forensic"
sys.path.insert(0, str(FORENSIC_DIR))

from uuid import UUID
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CaseModel, EvidenceModel, UserModel, ForensicAnalysisModel, 
    EvidenceHashModel, EventModel, TimelineEventModel, EntityModel, 
    RelationshipModel, ReportModel
)
from app.config import settings
from app.dependencies import get_current_user
from forensic_engine import process_evidence

from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    EvidenceMetadata,
    FindingCreate,
    FindingResponse
)

router = APIRouter(prefix="/cases", tags=["Case Management & Investigation"])


def owned_case(case_id: UUID, user: UserModel, db: Session) -> CaseModel:
    """Helper to ensure a case exists and belongs to the authenticated user."""
    case = db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return case


# ==========================================
# 1. CASE MANAGEMENT APIs (PostgreSQL)
# ==========================================

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED, summary="Create case")
def create_case(data: CaseCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = CaseModel(
        title=data.title, 
        description=data.description, 
        created_by=user.id, 
        status="Open"
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    return {
        "id": str(case.id),
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "created_at": case.created_at,
        "updated_at": getattr(case, "updated_at", case.created_at)
    }
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import CaseModel
from app.schemas.case import CaseCreate, CaseResponse  # Adjust import path if schemas are in app/schemas.py

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    # Create the case instance with data matching the database model
    new_case = CaseModel(
        title=case_data.title,
        description=case_data.description,
        created_by=case_data.created_by,
        status="Open"  # Defaults to Open based on your enum
    )
    
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    return new_case

@router.get("/", response_model=List[CaseResponse])
def get_cases(db: Session = Depends(get_db)):
    return db.query(CaseModel).all()

@router.get("", response_model=List[CaseResponse], summary="Get all cases for current user")
def list_cases(db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    cases = db.query(CaseModel).filter(CaseModel.created_by == user.id).order_by(CaseModel.created_at.desc()).all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "description": c.description,
            "status": c.status.capitalize() if c.status else "Open",
            "created_at": c.created_at,
            "updated_at": getattr(c, "updated_at", c.created_at)
        }
        for c in cases
    ]


@router.get("/{case_id}", response_model=CaseResponse, summary="View specific case")
def get_case(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    c = owned_case(case_id, user, db)
    return {
        "id": str(c.id),
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "created_at": c.created_at,
        "updated_at": getattr(c, "updated_at", c.created_at)
    }


@router.patch("/{case_id}", response_model=CaseResponse, summary="Update case details or status")
def update_case(case_id: UUID, data: CaseUpdate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = owned_case(case_id, user, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        if key != "updated_at":
            setattr(case, key, value.value if hasattr(value, "value") else value)
    
    if hasattr(case, "updated_at"):
        case.updated_at = datetime.utcnow()
        
    db.commit()
    db.refresh(case)
    
    return {
        "id": str(case.id),
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "created_at": case.created_at,
        "updated_at": getattr(case, "updated_at", case.created_at)
    }


@router.delete("/{case_id}", summary="Delete case and all related records")
def delete_case(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    
    evidence_rows = db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).all()
    evidence_ids = [item.id for item in evidence_rows]
    
    db.query(TimelineEventModel).filter(TimelineEventModel.case_id == case_id).delete(synchronize_session=False)
    db.query(EventModel).filter(EventModel.case_id == case_id).delete(synchronize_session=False)
    db.query(RelationshipModel).filter(RelationshipModel.case_id == case_id).delete(synchronize_session=False)
    db.query(EntityModel).filter(EntityModel.case_id == case_id).delete(synchronize_session=False)
    db.query(ForensicAnalysisModel).filter(ForensicAnalysisModel.case_id == case_id).delete(synchronize_session=False)
    
    if evidence_ids:
        db.query(EvidenceHashModel).filter(EvidenceHashModel.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
        db.query(EvidenceModel).filter(EvidenceModel.id.in_(evidence_ids)).delete(synchronize_session=False)
        
    db.query(ReportModel).filter(ReportModel.case_id == case_id).delete(synchronize_session=False)
    
    case_obj = db.query(CaseModel).filter(CaseModel.id == case_id).first()
    db.delete(case_obj)
    db.commit()

    storage_path = (settings.STORAGE_DIR / str(case_id)).resolve()
    if settings.STORAGE_DIR == storage_path.parent and storage_path.is_dir():
        shutil.rmtree(storage_path, ignore_errors=True)
        
    return {"message": "Case and related records successfully deleted"}


@router.get("/{case_id}/stats", summary="Get case statistics")
def case_stats(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    evidence_count = db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).count()
    return {"case_id": str(case_id), "evidence_count": evidence_count}


# ==========================================
# 2. EVIDENCE MANAGEMENT APIs
# ==========================================

@router.post("/{case_id}/evidence", status_code=status.HTTP_201_CREATED, summary="Upload evidence file")
async def upload_evidence(
    case_id: UUID, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    user: UserModel = Depends(get_current_user)
):
    owned_case(case_id, user, db)

    content = await file.read()
    evidence_id = uuid.uuid4()
    original_name = Path(file.filename or "evidence").name

    case_storage_dir = settings.STORAGE_DIR / str(case_id)
    case_storage_dir.mkdir(parents=True, exist_ok=True)
    
    stored_filename = f"{evidence_id}_{original_name}"
    stored_path = case_storage_dir / stored_filename
    stored_path.write_bytes(content)

    sha256_hash = hashlib.sha256(content).hexdigest()
    md5_hash = hashlib.md5(content).hexdigest()

    db_evidence = EvidenceModel(
        id=evidence_id,
        case_id=case_id,
        filename=original_name,
        file_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        stored_path=str(stored_path),
        status="uploaded"
    )
    db.add(db_evidence)
    
    db_hash = EvidenceHashModel(
        evidence_id=evidence_id,
        sha256=sha256_hash,
        md5=md5_hash
    )
    db.add(db_hash)
    db.commit()
    db.refresh(db_evidence)

    return {
        "id": str(evidence_id),
        "evidence_id": str(evidence_id),
        "case_id": str(case_id),
        "filename": original_name,
        "sha256": sha256_hash,
        "md5": md5_hash,
        "size": len(content),
        "status": "uploaded"
    }


@router.get("/{case_id}/evidence", summary="List all case evidence")
def list_case_evidence(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    evidence_rows = db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).all()
    return evidence_rows


@router.post("/{case_id}/evidence/{evidence_id}/forensic", summary="Run forensic analysis")
async def analyze_evidence_forensic(
    case_id: UUID,
    evidence_id: UUID,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    owned_case(case_id, user, db)

    evidence = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id, EvidenceModel.case_id == case_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found.")

    if not evidence.stored_path or not Path(evidence.stored_path).exists():
        raise HTTPException(status_code=404, detail="Stored evidence file on disk not found.")

    try:
        result = process_evidence(
            file_path=evidence.stored_path,
            case_id=str(case_id),
            evidence_id=str(evidence_id),
            send_to_backend=False,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Forensic analysis failed: {exc}")


# ==========================================
# 3. FINDINGS & IOCs ENDPOINTS
# ==========================================

@router.get("/{case_id}/findings", summary="Get case findings from analysis")
def list_case_findings(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    analyses = db.query(ForensicAnalysisModel).filter(ForensicAnalysisModel.case_id == case_id).order_by(ForensicAnalysisModel.created_at.desc()).all()
    
    findings = []
    for analysis in analyses:
        finding = (analysis.result or {}).get("forensic_finding") or {}
        if finding:
            findings.append({
                "id": str(analysis.id), 
                **finding, 
                "classification": analysis.classification,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            })
    return findings


@router.get("/{case_id}/iocs", summary="Get linked cybersecurity IOCs")
def list_case_iocs(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    return {
        "case_id": str(case_id),
        "status": "active",
        "associated_iocs": []
    }
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
