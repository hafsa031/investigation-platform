from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.models import CaseModel

router = APIRouter(prefix="/cases", tags=["Cases"])

class CaseCreate(BaseModel):
    id: str
    title: str
    description: Optional[str] = None

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    # Check if case ID already exists in PostgreSQL
    existing_case = db.query(CaseModel).filter(CaseModel.id == case_data.id).first()
    if existing_case:
        raise HTTPException(status_code=400, detail="Case ID already exists")
    
    new_case = CaseModel(
        id=case_data.id,
        title=case_data.title,
        description=case_data.description
    )
    
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    return new_case

@router.get("/", response_model=List[CaseResponse])
def get_cases(db: Session = Depends(get_db)):
    return db.query(CaseModel).all()
