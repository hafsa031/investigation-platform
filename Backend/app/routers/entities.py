from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import EntityModel, RelationshipModel
from app.schemas.entities import (
    EntityCreate, EntityResponse,
    RelationshipCreate, RelationshipResponse
)

router = APIRouter(prefix="/graph", tags=["Entities & Relationships"])

@router.post("/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity(entity: EntityCreate, db: Session = Depends(get_db)):
    db_entity = EntityModel(**entity.dict())
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity

@router.get("/entities/{case_id}", response_model=List[EntityResponse])
def get_case_entities(case_id: UUID, db: Session = Depends(get_db)):
    return db.query(EntityModel).filter(EntityModel.case_id == case_id).all()

@router.post("/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(rel: RelationshipCreate, db: Session = Depends(get_db)):
    db_rel = RelationshipModel(**rel.dict())
    db.add(db_rel)
    db.commit()
    db.refresh(db_rel)
    return db_rel

@router.get("/relationships/{case_id}", response_model=List[RelationshipResponse])
def get_case_relationships(case_id: UUID, db: Session = Depends(get_db)):
    return db.query(RelationshipModel).filter(RelationshipModel.case_id == case_id).all()