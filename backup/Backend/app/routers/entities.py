from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import EntityModel, RelationshipModel, CaseModel, UserModel
from app.schemas.entities import EntityCreate, EntityResponse, RelationshipCreate, RelationshipResponse

router = APIRouter(prefix="/graph", tags=["Entities & Relationships"])

def check_case(case_id, user, db):
    if not db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first():
        raise HTTPException(status_code=404, detail="Case not found")

@router.post("/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity(data: EntityCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(data.case_id, user, db)
    obj = EntityModel(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/entities/{case_id}", response_model=list[EntityResponse])
def list_entities(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(case_id, user, db)
    return db.query(EntityModel).filter(EntityModel.case_id == case_id).all()

@router.post("/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(data: RelationshipCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(data.case_id, user, db)
    for entity_id in (data.source_entity_id, data.target_entity_id):
        entity = db.query(EntityModel).filter(EntityModel.id == entity_id, EntityModel.case_id == data.case_id).first()
        if not entity: raise HTTPException(status_code=404, detail="Relationship entity not found in this case")
    obj = RelationshipModel(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/relationships/{case_id}", response_model=list[RelationshipResponse])
def list_relationships(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(case_id, user, db)
    return db.query(RelationshipModel).filter(RelationshipModel.case_id == case_id).all()
