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