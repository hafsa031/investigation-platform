import json
import re
import shutil
import uuid
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import (EvidenceModel, EvidenceHashModel, CaseModel, UserModel,
                        ForensicAnalysisModel, EventModel, TimelineEventModel)
from app.schemas.evidence import EvidenceResponse, EvidenceAnalysisResponse

router = APIRouter(prefix="/evidence", tags=["Evidence"])
CHUNK = 1024 * 1024

def _owned_case(case_id: UUID, user: UserModel, db: Session):
    case = db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

def _safe_filename(name: str) -> str:
    name = Path(name or "evidence.bin").name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    return name[:180] or "evidence.bin"

@router.post("/upload/{case_id}", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(case_id: UUID, file: UploadFile = File(...),
                          description: str | None = Form(None),
                          acquisition_source: str | None = Form(None),
                          db: Session = Depends(get_db),
                          user: UserModel = Depends(get_current_user)):
    _owned_case(case_id, user, db)
    original_name = _safe_filename(file.filename)
    evidence_id = uuid.uuid4()
    target_dir = settings.STORAGE_DIR / str(case_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{evidence_id}_{original_name}"
    total = 0
    try:
        with target.open("wb") as out:
            while chunk := await file.read(CHUNK):
                total += len(chunk)
                if total > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB limit")
                out.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="Empty files cannot be uploaded")
        record = EvidenceModel(
            id=evidence_id, case_id=case_id, uploaded_by=user.id,
            filename=original_name, storage_key=str(target.relative_to(settings.STORAGE_DIR)),
            mime_type=file.content_type, size_bytes=total,
            description=description, acquisition_source=acquisition_source
        )
        db.add(record); db.commit(); db.refresh(record)
        return record
    except Exception:
        target.unlink(missing_ok=True)
        db.rollback()
        raise
    finally:
        await file.close()

@router.get("/case/{case_id}", response_model=list[EvidenceResponse])
def list_case_evidence(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    _owned_case(case_id, user, db)
    return db.query(EvidenceModel).filter(EvidenceModel.case_id == case_id).order_by(EvidenceModel.created_at.desc()).all()

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    item = db.query(EvidenceModel).join(CaseModel).filter(
        EvidenceModel.id == evidence_id, CaseModel.created_by == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return item

@router.get("/{evidence_id}/download")
def download_evidence(evidence_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    evidence = db.query(EvidenceModel).join(CaseModel).filter(
        EvidenceModel.id == evidence_id, CaseModel.created_by == user.id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    path = (settings.STORAGE_DIR / evidence.storage_key).resolve()
    if settings.STORAGE_DIR not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Stored evidence file is missing")
    return FileResponse(path, filename=evidence.filename, media_type="application/octet-stream")


@router.post("/{evidence_id}/analyze", response_model=EvidenceAnalysisResponse)
def analyze_evidence(evidence_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    evidence = db.query(EvidenceModel).join(CaseModel).filter(
        EvidenceModel.id == evidence_id, CaseModel.created_by == user.id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    path = (settings.STORAGE_DIR / evidence.storage_key).resolve()
    if settings.STORAGE_DIR not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Stored evidence file is missing")

    try:
        # Import the single-source forensic engine from the repository's Forensic folder.
        import sys
        forensic_dir = Path(__file__).resolve().parents[3] / "Forensic"
        if str(forensic_dir) not in sys.path:
            sys.path.insert(0, str(forensic_dir))
        from forensic_engine_final import process_evidence
        result = process_evidence(path, case_id=str(evidence.case_id), evidence_id=str(evidence.id), send_to_backend=False)
        # Store complete JSON-safe output and mark analysis completed.
        payload = json.loads(json.dumps(result, default=str))
        existing = db.query(ForensicAnalysisModel).filter(ForensicAnalysisModel.evidence_id == evidence.id).first()
        if existing:
            existing.result = payload
            existing.classification = (result.get("classification") or {}).get("classification", "Normal")
        else:
            db.add(ForensicAnalysisModel(
                evidence_id=evidence.id, case_id=evidence.case_id,
                classification=(result.get("classification") or {}).get("classification", "Normal"),
                result=payload
            ))
        for h in (result.get("hash") or {}).get("hashes", []):
            row = db.query(EvidenceHashModel).filter(
                EvidenceHashModel.evidence_id == evidence.id,
                EvidenceHashModel.algorithm == h["algorithm"]).first()
            if row:
                row.hash_value = h["hash_value"]
            else:
                db.add(EvidenceHashModel(evidence_id=evidence.id, algorithm=h["algorithm"], hash_value=h["hash_value"]))
        # Persist engine-generated timeline events as case events and timeline rows.
        for event_data in result.get("timeline_events", []):
            occurred = event_data.get("timestamp") or event_data.get("occurred_at")
            if not occurred:
                continue
            from datetime import datetime
            if isinstance(occurred, str):
                occurred = datetime.fromisoformat(occurred.replace("Z", "+00:00")).replace(tzinfo=None)
            event = EventModel(case_id=evidence.case_id, source_evidence_id=evidence.id,
                               event_type=str(event_data.get("event_type") or event_data.get("source") or "forensic"),
                               description=str(event_data.get("description") or event_data.get("label") or "Extracted forensic event"),
                               occurred_at=occurred, source_timezone="UTC",
                               attributes=json.loads(json.dumps(event_data, default=str)))
            db.add(event); db.flush()
            db.add(TimelineEventModel(case_id=evidence.case_id, event_id=event.id,
                timestamp=occurred, source_timezone="UTC",
                label=str(event_data.get("label") or event_data.get("event_type") or "Forensic event"),
                notes=str(event_data.get("description") or "")))
        db.commit()
        return {"evidence_id": evidence.id, "case_id": evidence.case_id, "status": "completed", "result": payload}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Forensic analysis failed: {exc}") from exc

@router.get("/{evidence_id}/analysis", response_model=EvidenceAnalysisResponse)
def get_analysis(evidence_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    evidence = db.query(EvidenceModel).join(CaseModel).filter(
        EvidenceModel.id == evidence_id, CaseModel.created_by == user.id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    analysis = db.query(ForensicAnalysisModel).filter(ForensicAnalysisModel.evidence_id == evidence_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not available. Run analysis first.")
    return {"evidence_id": evidence.id, "case_id": evidence.case_id, "status": "completed", "result": analysis.result}
