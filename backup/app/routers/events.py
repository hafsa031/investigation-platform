from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import EventModel, TimelineEventModel
from app.schemas.events import (
    EventCreate, EventResponse,
    TimelineEventCreate, TimelineEventResponse
)

router = APIRouter(prefix="/timeline", tags=["Events & Timeline"])

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = EventModel(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("/events/{case_id}", response_model=List[EventResponse])
def get_case_events(case_id: UUID, db: Session = Depends(get_db)):
    return db.query(EventModel).filter(EventModel.case_id == case_id).all()

@router.post("/timeline-items", response_model=TimelineEventResponse, status_code=status.HTTP_201_CREATED)
def create_timeline_item(item: TimelineEventCreate, db: Session = Depends(get_db)):
    db_item = TimelineEventModel(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/items/{case_id}", response_model=List[TimelineEventResponse])
def get_case_timeline(case_id: UUID, db: Session = Depends(get_db)):
    return db.query(TimelineEventModel).filter(TimelineEventModel.case_id == case_id).all()