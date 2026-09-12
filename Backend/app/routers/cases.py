from fastapi import APIRouter
from typing import List
from app.schemas.case import CaseCreate, CaseResponse

router = APIRouter(prefix="/cases", tags=["Case Management"])

cases_db = []

@router.post("/", response_model=CaseResponse)
async def create_case(case: CaseCreate):
    new_case = {
        "id": f"CASE-{len(cases_db) + 1:03d}",
        "title": case.title,
        "description": case.description,
        "status": "Active"
    }
    cases_db.append(new_case)
    return new_case

@router.get("/", response_model=List[CaseResponse])
async def list_cases():
    return cases_db