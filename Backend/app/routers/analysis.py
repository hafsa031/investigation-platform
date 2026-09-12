from fastapi import APIRouter

router = APIRouter(prefix="/analysis", tags=["Analysis Status"])

@router.get("/status/{evidence_id}")
async def get_analysis_status(evidence_id: str):
    return {
        "evidence_id": evidence_id,
        "hashing_status": "Completed",
        "metadata_status": "Completed",
        "ai_analysis_status": "In Progress"
    }