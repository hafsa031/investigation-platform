from fastapi import APIRouter, UploadFile, File, Form
from app.schemas.evidence import EvidenceUploadResponse
import uuid

router = APIRouter(prefix="/evidence", tags=["Evidence APIs"])

@router.post("/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(case_id: str = Form(...), file: UploadFile = File(...)):
    evidence_id = str(uuid.uuid4())[:8]
    return {
        "evidence_id": f"EVD-{evidence_id}",
        "filename": file.filename,
        "case_id": case_id,
        "status": "Uploaded"
    }