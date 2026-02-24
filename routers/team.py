from typing import List
from venv import create
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime
from models import TeamMember
from crud import create_team, get_active_team, get_teams_by_user_id, delete_team, get_teams_by_user_and_sport, \
    join_team, \
    leave_team, get_active_user, get_my_active_teams, pagination_params, get_number_of_instances_by_id_active, \
    get_my_all_teams, get_number_of_instances_by_id_all, get_teams_all, get_number_of_instances_all, \
    get_teams_all_active, get_number_of_instances_active, alter_team
from database import get_db
from models import VisibilityEnum, SortEnum, Team
from schemas import TeamCreate, TeamResponse, SportEnum, JoinTeamRequest, Pagination, ListTeam, TeamUpdate, \
    TeamMemberResponse, MessageResponse
team_router = APIRouter(prefix="", tags=["Teams"])

@team_router.post("/create", response_model=TeamResponse)
def create_team_route(data: TeamCreate, db: Session = Depends(get_db)):
    db_user = get_active_user(db, data.created_by)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    new_team = create_team(db, data, creator_id=data.created_by)

    if not new_team:
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )
    new_team.current_players = db.query(TeamMember).filter(TeamMember.team_id == new_team.id).count()
    db.commit()
    db.refresh(new_team)
    db_user.team_created.append(new_team)

    return new_team

@team_router.get("/myteams/all_active", response_model=ListTeam)
def get_active_teams_by_org_id(created_by: int, db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    user = get_active_user(db, created_by)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    teams = get_my_active_teams(db, pagination, order_by, start, created_by)
    total = get_number_of_instances_by_id_active(db, Team, created_by)

    response = {
        "data": teams,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"]["previous"] = f"/myteams/all_active?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"]['previous'] = f"/myteams/all_active?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/myteams/all_active?page={pagination.page+1}&perPage={pagination.perPage}"
    return response

@team_router.get("/myteams/all", response_model=ListTeam)
def get_all_teams_by_org_id(created_by: int, db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    user = get_active_user(db, created_by)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    teams = get_my_all_teams(db, pagination, order_by, start, created_by)

    total = get_number_of_instances_by_id_all(db, Team, created_by)

    response = {
        "data": teams,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"][
                "previous"] = f"/myteams/all?page={pagination.page - 1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"][
                'previous'] = f"/myteams/all?page={pagination.page - 1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/myteams/all?page={pagination.page + 1}&perPage={pagination.perPage}"
    return response

@team_router.get("/all", response_model=ListTeam)
def get_all_teams_route(db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    teams = get_teams_all(db, pagination, order_by, start)
    total = get_number_of_instances_all(db, Team)

    response = {
        "data": teams,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"][
                "previous"] = f"/all?page={pagination.page - 1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"][
                'previous'] = f"/all?page={pagination.page - 1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/all?page={pagination.page + 1}&perPage={pagination.perPage}"
    return response

@team_router.get("/all_active", response_model=ListTeam)
def get_active_teams_route(db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    teams = get_teams_all_active(db, pagination, order_by, start)
    total = get_number_of_instances_active(db, Team)

    response = {
        "data": teams,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"][
                "previous"] = f"/all?page={pagination.page - 1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"][
                'previous'] = f"/all?page={pagination.page - 1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/all?page={pagination.page + 1}&perPage={pagination.perPage}"
    return response

@team_router.get("/{team_id}", response_model=TeamResponse)
def get_team_route(team_id: int, db: Session = Depends(get_db)):
    team = get_active_team(db, team_id)
    return team

@team_router.patch("/alter/{team_id}", response_model=TeamResponse)
def alter_team_route(team_id: int, updated_data: TeamUpdate, db: Session = Depends(get_db)):
    db_team = get_active_team(db, team_id)

    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    """if updated_data.visibility == VisibilityEnum.closed and not updated_data.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Private tournament requires a password"
        )"""

    if updated_data.max_players < db_team.current_players:
        raise HTTPException(status_code=400, detail="You can't set maximum value less than current number of joined players.")
    db_team = alter_team(db, updated_data, db_team)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    return db_team

@team_router.delete("/delete/{team_id}", response_model=TeamResponse)
def delete_team_route(team_id: int, db: Session = Depends(get_db)):
    db_team = delete_team(db, team_id)
    return db_team

@team_router.get("/sport/", response_model=List[TeamResponse])
def get_teams_by_sport_id(user_id: int, sport: SportEnum, db: Session = Depends(get_db)):
    teams = get_teams_by_user_and_sport(db, user_id, sport)
    return teams

@team_router.get("/joined_participants/{user_id}", response_model=List[TeamResponse])
def get_teams_by_joined_user_id(user_id: int, db: Session = Depends(get_db)):
    db_user = get_active_user(db, user_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

    teams = get_teams_by_user_id(db, db_user)

    if not teams:
        return []

    valid_teams = [team for team in teams if team is not None]

    return valid_teams


@team_router.post("/join", response_model=TeamMemberResponse)
def join_team_route(request: JoinTeamRequest, db: Session = Depends(get_db)):
    return join_team(db, request.team_id, request.user_id, request.password)

@team_router.post("/leave", response_model=MessageResponse)
def leave_team_route(request: JoinTeamRequest, db: Session = Depends(get_db)):
    return leave_team(db, request.team_id, request.user_id)