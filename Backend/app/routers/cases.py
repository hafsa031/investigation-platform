<<<<<<< Updated upstream
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from typing import List
from datetime import datetime
import uuid
import hashlib
import sys
from pathlib import Path

FORENSIC_DIR = Path(__file__).resolve().parents[3] / "Forensic"
sys.path.insert(0, str(FORENSIC_DIR))
=======
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (CaseModel, EvidenceModel, UserModel, ForensicAnalysisModel, EvidenceHashModel,
                        EventModel, TimelineEventModel, EntityModel, RelationshipModel, ReportModel)
from app.config import settings
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse
from app.dependencies import get_current_user
>>>>>>> Stashed changes

from forensic_engine import process_evidence

<<<<<<< Updated upstream
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseStatus,
    EvidenceMetadata,
    FindingCreate,
    FindingResponse
)

router = APIRouter(prefix="/cases")

# In-memory storage structures
cases_db = {}
evidence_db = {}
findings_db = {}

EVIDENCE_STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "evidence"
EVIDENCE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 1. CASE MANAGEMENT APIs
# ==========================================

@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Case Management APIs"],
    summary="Create case"
)
async def create_case(case: CaseCreate):
    case_id = f"CASE-{(len(cases_db) + 1):03d}"
    now = datetime.utcnow()
    
    new_case = {
        "id": case_id,
        "title": case.title,
        "description": case.description,
        "status": CaseStatus.OPEN,
        "created_at": now,
        "updated_at": now
    }
    cases_db[case_id] = new_case
    return new_case


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    tags=["Case Management APIs"],
    summary="View case"
)
async def view_case(case_id: str):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return cases_db[case_id]


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    tags=["Case Management APIs"],
    summary="Update case (Status: Open / Under Investigation / Closed)"
)
async def update_case(case_id: str, payload: CaseUpdate):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    
    current_case = cases_db[case_id]
    if payload.title is not None:
        current_case["title"] = payload.title
    if payload.description is not None:
        current_case["description"] = payload.description
    if payload.status is not None:
        current_case["status"] = payload.status
        
    current_case["updated_at"] = datetime.utcnow()
    return current_case


# ==========================================
# 2. EVIDENCE MANAGEMENT APIs
# ==========================================

@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceMetadata,
    status_code=status.HTTP_201_CREATED,
    tags=["Evidence Management APIs"],
    summary="Upload evidence (Auto-generates SHA-256 hash)"
)
async def upload_evidence(case_id: str, file: UploadFile = File(...)):
    if case_id not in cases_db:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{case_id}' not found."
        )

    # Read uploaded file
    content = await file.read()

    # Generate evidence ID
    evidence_id = str(uuid.uuid4())

    # Preserve the original filename safely
    original_name = Path(file.filename or "evidence").name

    # Store using evidence ID to avoid filename collisions
    stored_filename = f"{evidence_id}_{original_name}"
    stored_path = EVIDENCE_STORAGE_DIR / stored_filename

    # Save evidence to disk
    stored_path.write_bytes(content)

    # Calculate hashes
    sha256_hash = hashlib.sha256(content).hexdigest()
    md5_hash = hashlib.md5(content).hexdigest()

    metadata = {
        "id": evidence_id,
        "evidence_id": evidence_id,
        "case_id": case_id,
        "filename": original_name,
        "file_type": file.content_type or "application/octet-stream",
        "sha256": sha256_hash,
        "md5": md5_hash,
        "file_size_bytes": len(content),
        "size": len(content),
        "uploaded_at": datetime.utcnow(),
        "status": "uploaded",
        "stored_path": str(stored_path),
    }

    if case_id not in evidence_db:
        evidence_db[case_id] = []

    evidence_db[case_id].append(metadata)

    return metadata

# ==========================================
# 3. INVESTIGATION ENDPOINTS
# ==========================================

@router.get(
    "",
    response_model=List[CaseResponse],
    tags=["Investigation Endpoints"],
    summary="Get all cases"
)
async def list_cases():
    return list(cases_db.values())


@router.get(
    "/{case_id}/evidence",
    response_model=List[EvidenceMetadata],
    tags=["Investigation Endpoints"],
    summary="Get all case evidence"
)
async def list_case_evidence(case_id: str):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return evidence_db.get(case_id, [])

@router.post(
    "/{case_id}/evidence/{evidence_id}/forensic",
    tags=["Forensic Analysis"],
    summary="Run forensic analysis on evidence"
)
async def analyze_evidence_forensic(
    case_id: str,
    evidence_id: str
):
    if case_id not in cases_db:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{case_id}' not found."
        )

    evidence_list = evidence_db.get(case_id, [])

    evidence = next(
        (
            item
            for item in evidence_list
            if item.get("id") == evidence_id
            or item.get("evidence_id") == evidence_id
        ),
        None,
    )

    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence '{evidence_id}' not found."
        )

    stored_path = evidence.get("stored_path")

    if not stored_path or not Path(stored_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Stored evidence file not found."
        )

    try:
        result = process_evidence(
            file_path=stored_path,
            case_id=case_id,
            evidence_id=evidence_id,
            send_to_backend=False,
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Forensic analysis failed: {exc}"
        )

@router.post(
    "/{case_id}/findings",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Investigation Endpoints"],
    summary="Add finding to case"
)
async def add_finding(case_id: str, finding: FindingCreate):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    
    finding_data = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "summary": finding.summary,
        "severity": finding.severity,
        "details": finding.details,
        "created_at": datetime.utcnow()
    }
    
    if case_id not in findings_db:
        findings_db[case_id] = []
    findings_db[case_id].append(finding_data)
    
    return finding_data


@router.get(
    "/{case_id}/findings",
    response_model=List[FindingResponse],
    tags=["Investigation Endpoints"],
    summary="Get all case findings"
)
async def list_case_findings(case_id: str):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return findings_db.get(case_id, [])


@router.get(
    "/{case_id}/iocs",
    tags=["Investigation Endpoints"],
    summary="Get linked cybersecurity IOCs"
)
async def list_case_iocs(case_id: str):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return {
        "case_id": case_id,
        "status": "active",
        "associated_iocs": []
    }
=======
def owned_case(case_id: UUID, user: UserModel, db: Session) -> CaseModel:
    case = db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(data: CaseCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = CaseModel(title=data.title, description=data.description, created_by=user.id, status="open")
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

@router.delete("/{case_id}")
def delete_case(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    case = owned_case(case_id, user, db)
    evidence_rows = db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).all()
    evidence_ids = [item.id for item in evidence_rows]
    # Remove dependent rows explicitly so this also works with existing PostgreSQL constraints.
    db.query(TimelineEventModel).filter(TimelineEventModel.case_id == case_id).delete(synchronize_session=False)
    db.query(EventModel).filter(EventModel.case_id == case_id).delete(synchronize_session=False)
    db.query(RelationshipModel).filter(RelationshipModel.case_id == case_id).delete(synchronize_session=False)
    db.query(EntityModel).filter(EntityModel.case_id == case_id).delete(synchronize_session=False)
    db.query(ForensicAnalysisModel).filter(ForensicAnalysisModel.case_id == case_id).delete(synchronize_session=False)
    if evidence_ids:
        db.query(EvidenceHashModel).filter(EvidenceHashModel.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
        db.query(EvidenceModel).filter(EvidenceModel.id.in_(evidence_ids)).delete(synchronize_session=False)
    db.query(ReportModel).filter(ReportModel.case_id == case_id).delete(synchronize_session=False)
    db.delete(case); db.commit()
    # Stored evidence is kept outside the database; remove this case's storage folder after commit.
    storage_path = (settings.STORAGE_DIR / str(case_id)).resolve()
    if settings.STORAGE_DIR == storage_path.parent and storage_path.is_dir():
        import shutil
        shutil.rmtree(storage_path, ignore_errors=True)
    return {"message": "Case and related records successfully deleted"}

@router.get("/{case_id}/stats")
def case_stats(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    return {"case_id": str(case_id), "evidence_count": db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).count()}

@router.get("/{case_id}/findings")
def list_case_findings(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    owned_case(case_id, user, db)
    analyses = db.query(ForensicAnalysisModel).filter(ForensicAnalysisModel.case_id == case_id).order_by(ForensicAnalysisModel.created_at.desc()).all()
    findings = []
    for analysis in analyses:
        finding = (analysis.result or {}).get("forensic_finding") or {}
        if finding:
            findings.append({"id": str(analysis.id), **finding, "classification": analysis.classification,
                             "created_at": analysis.created_at.isoformat() if analysis.created_at else None})
    return findings
>>>>>>> Stashed changes
