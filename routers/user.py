from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import user
from database import get_db

from typing import List
import crud
import database
import schemas
from crud import alter_user, delete_manual_participant, delete_tournament, leave_team, get_active_user, \
    leave_tournament, leave_tournament_solo, leave_tournament_team
from models import ManualParticipant, Tournament
from schemas import ParticipantManualResponse, UserCreate, UserAlter, UserResponse
user_router = APIRouter(prefix="", tags=["Users"])

@user_router.post("/create", response_model=schemas.UserResponse)
def create_user_route(user_: schemas.UserCreate, db: Session = Depends(database.get_db)):
    existing_email = crud.get_user_by_email(db, user_.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already in use")

    existing_nickname = crud.get_user_by_nickname(db, user_.nickname)
    if existing_nickname:
        raise HTTPException(status_code=400, detail="Nickname already in use")

    new_user = crud.create_user(db, user_)

    new_user.age = UserResponse.calculate_age(new_user.date_of_birth)
    return new_user

@user_router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserAlter,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user



@user_router.get("/all", response_model=List[schemas.UserResponse])
def get_users_route(db: Session = Depends(database.get_db)):
    users = crud.get_user_all(db)
    if not users:
        raise HTTPException(status_code=204, detail="No Content")

    for user1 in users:
        user1.age = UserResponse.calculate_age(user1.date_of_birth)
    return users

@user_router.get("/all_active", response_model=List[schemas.UserResponse])
def get_active_users_route(db: Session = Depends(database.get_db)):
    users = crud.get_user_all_active(db)
    if not users:
        raise HTTPException(status_code=204, detail="No Content")

    for user1 in users:
        user1.age = UserResponse.calculate_age(user1.date_of_birth)
    return users

@user_router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user_route(user_id: int, db: Session = Depends(database.get_db)):
    user1 = crud.get_active_user(db, user_id)

    if not user1:
        raise HTTPException(status_code=404, detail="User not found")
    if user1.date_of_birth is not None:
        user1.age = UserResponse.calculate_age(user1.date_of_birth)
    return user1

@user_router.get("/email/{email}", response_model=schemas.UserResponse)
def get_user_by_email_route(email: str, db: Session = Depends(database.get_db)):
    user1 = crud.get_user_by_email(db, email)
    if not user1:
        raise HTTPException(status_code=404, detail="User not found")
    if user1.date_of_birth is not None:
        user1.age = UserResponse.calculate_age(user1.date_of_birth)
    return user1

@user_router.get("/nickname/{nickname}", response_model=schemas.UserResponse)
def get_user_by_nickname_route(nickname: str, db: Session = Depends(database.get_db)):
    user = crud.get_user_by_nickname(db, nickname)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.date_of_birth is not None:
        user.age = UserResponse.calculate_age(user.date_of_birth)
        
    return user

@user_router.patch("/alter/{user_id}", response_model=schemas.UserResponse)
def alter_user_route(user_id: int, update_data: schemas.UserAlter, db: Session = Depends(database.get_db)):
    db_user = crud.get_active_user(db, user_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_email = crud.get_user_by_email(db, update_data.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already in use")

    existing_nickname = crud.get_user_by_nickname(db, update_data.nickname)
    if existing_nickname:
        raise HTTPException(status_code=400, detail="Nickname already in use")

    updated_user = alter_user(db, db_user, update_data)

    updated_user_dict = updated_user.__dict__
    updated_user_dict['age'] = UserResponse.calculate_age(db_user.date_of_birth)
    response = UserResponse(**updated_user_dict)
    return response

@user_router.delete("/delete/{user_id}", response_model=schemas.UserResponse)
def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    db_user = get_active_user(db, user_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    active_created_manual_participants = db_user.manual_participants
    active_created_tournaments = db_user.tournaments_created
    active_created_teams = db_user.team_created
    active_joined_teams = db_user.team_memberships
    active_joined_tournaments = db_user.tournament_participations

    if active_created_manual_participants:
        for participant in active_created_manual_participants:
            participant.deleted_at = datetime.now(timezone.utc)
            try:
                db.commit()
                db.refresh(participant)
            except IntegrityError:
                raise HTTPException(status_code=400, detail="Can't delete the manually entered participant.")

    if active_created_tournaments:
        for tournament in active_created_tournaments:
            tournament.deleted_at = datetime.now(timezone.utc)
            try:
                db.commit()
                db.refresh(tournament)
            except IntegrityError:
                raise HTTPException(status_code=400, detail="Can't delete the tournament.")

    if active_created_teams:
        for team in active_created_teams:
            team.deleted_at = datetime.now(timezone.utc)
            try:
                db.commit()
                db.refresh(team)
            except IntegrityError:
                raise HTTPException(status_code=400, detail="Can't delete the team.")

    if active_joined_teams:
        for team_member in active_joined_teams:
            print(leave_team(db, team_member.team_id, user_id))

    if active_joined_tournaments:
        for tournament_member in active_joined_tournaments:
            if tournament_member.user_id:
                leave_tournament_solo(db, tournament_member.tournament_id, tournament_member.user_id)
            elif tournament_member.team_id:
                leave_tournament_team(db, tournament_member.tournament_id, tournament_member.team_id)
    db_user = crud.delete_user(db, user_id)

    db_user.age = UserResponse.calculate_age(db_user.date_of_birth)
    return db_user