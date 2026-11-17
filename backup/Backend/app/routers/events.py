from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import EventModel, TimelineEventModel, CaseModel, EvidenceModel, UserModel
from app.schemas.events import EventCreate, EventResponse, TimelineEventCreate, TimelineEventResponse

router = APIRouter(prefix="/timeline", tags=["Events & Timeline"])

def check_case(case_id, user, db):
    if not db.query(CaseModel).filter(CaseModel.id == case_id, CaseModel.created_by == user.id).first():
        raise HTTPException(status_code=404, detail="Case not found")

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(data.case_id, user, db)
    if data.source_evidence_id and not db.query(EvidenceModel).filter(EvidenceModel.id == data.source_evidence_id, EvidenceModel.case_id == data.case_id).first():
        raise HTTPException(status_code=404, detail="Source evidence not found in this case")
    obj = EventModel(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/events/{case_id}", response_model=list[EventResponse])
def list_events(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(case_id, user, db)
    return db.query(EventModel).filter(EventModel.case_id == case_id).order_by(EventModel.occurred_at.desc()).all()

@router.post("/timeline-items", response_model=TimelineEventResponse, status_code=status.HTTP_201_CREATED)
def create_timeline_item(data: TimelineEventCreate, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(data.case_id, user, db)
    event = db.query(EventModel).filter(EventModel.id == data.event_id, EventModel.case_id == data.case_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found in this case")
    obj = TimelineEventModel(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/items/{case_id}", response_model=list[TimelineEventResponse])
def list_timeline(case_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    check_case(case_id, user, db)
    return db.query(TimelineEventModel).filter(TimelineEventModel.case_id == case_id).order_by(TimelineEventModel.timestamp.asc()).all()
