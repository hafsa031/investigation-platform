from pydantic import BaseModel

class EvidenceUploadResponse(BaseModel):
    evidence_id: str
    filename: str
    case_id: str
    status: str