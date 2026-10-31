from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

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