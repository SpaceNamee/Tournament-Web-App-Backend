from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from typing import List

import crud
import database
import schemas
from crud import alter_manual_participant, get_active_user

manual_participant_router = APIRouter(tags=["Manual Participants"])

@manual_participant_router.post("/create_manual", response_model=schemas.ParticipantManualResponse)
def create_participant_manual_route(participant_: schemas.ParticipantManualCreate, db: Session = Depends(database.get_db)):
    user = get_active_user(db, participant_.created_by)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = crud.get_manual_participant_by_name_and_creator(db, participant_.name, participant_.created_by)
    if existing:
        raise HTTPException(status_code=400, detail="This participant already in use")

    new_participant = crud.create_manual_participant(db, participant_)

    if not new_participant:
        raise ValueError("Something went wrong.")

    user.manual_participants.append(new_participant)
    return new_participant

@manual_participant_router.get("/all_active", response_model=List[schemas.ParticipantManualResponse])
def get_manual_active_participant_route(db: Session = Depends(database.get_db)):
    manual_participant = crud.get_manual_active_participants(db)

    if not manual_participant:
        raise HTTPException(status_code=204, detail="No Content")

    return manual_participant

@manual_participant_router.get("/all", response_model=List[schemas.ParticipantManualResponse])
def get_manual_participant_route(db: Session = Depends(database.get_db)):
    manual_participant = crud.get_manual_participants(db)

    if not manual_participant:
        raise HTTPException(status_code=204, detail="No Content")

    return manual_participant

@manual_participant_router.get("/{manual_participant_id}", response_model=schemas.ParticipantManualResponse)
def get_manual_participant_route(manual_participant_id: int, db: Session = Depends(database.get_db)):
    manual_participant = crud.get_manual_participant_by_id(db, manual_participant_id)

    if not manual_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return manual_participant

@manual_participant_router.get("/by_name/{manual_participant_name}", response_model=schemas.ParticipantManualResponse)
def get_manual_participant_by_name_route(manual_participant_name: str, db: Session = Depends(database.get_db)):
    manual_participant = crud.get_manual_participant_by_name(db, manual_participant_name)

    if not manual_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return manual_participant

@manual_participant_router.put("/alter/{participant_id}", response_model=schemas.ParticipantManualAlter)
def alter_manual_participant_route(manual_participant_id: int, update_data: schemas.ParticipantManualAlter, db: Session = Depends(database.get_db)):
    db_participant = alter_manual_participant(db, manual_participant_id, update_data)

    if not db_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return db_participant

@manual_participant_router.delete("/delete/{manual_participant_id}", response_model=schemas.ParticipantManualResponse)
def delete_participant_route(manual_participant_id: int, db: Session = Depends(database.get_db)):
    db_participant = crud.delete_manual_participant(db, manual_participant_id)

    if not db_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return db_participant
    

