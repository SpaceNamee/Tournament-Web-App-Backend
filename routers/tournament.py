from datetime import datetime
from sqlalchemy.orm import joinedload
from typing import List, Union
from sqlalchemy import desc, asc
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from crud import create_tournament, get_tournament_active, get_tournaments_all, \
    leave_tournament, get_tournaments_by_min_age, get_tournaments_by_visibility, get_tournaments_by_sport, \
    get_tournaments_by_start_date, get_tournaments_by_location, get_tournaments_by_participant_id, \
    get_tournament_detail_by_id_active, get_solo_tournament_by_tournament_id, get_team_tournament_by_tournament_id, \
    delete_tournament, pagination_params, get_mytournaments_all, alter_tournament, get_active_user, \
    get_tournaments_all_active, get_number_of_instances_all, get_number_of_instances_active, \
    get_number_of_instances_by_id_all, get_mytournaments_all_active, get_number_of_instances_by_id_active, \
    get_tournament_detail_by_id_include_deleted, get_mytournaments_history, join_tournament_team, join_tournament_solo, \
    leave_tournament_team, leave_tournament_solo, add_detail_filed_all_active

from database import get_db
from models import ParticipantEnum, SortEnum, Tournament
from schemas import TournamentCreate, TournamentResponse, JoinTournamentRequest, LeaveTournamentRequest, \
    TournamentParticipantResponse, VisibilityEnum, SportEnum, SoloTournamentResponse, TeamTournamentResponse, \
    ListTournament, Pagination, TournamentAlter, SoloTournamentCreate
from datetime import date

tournament_router = APIRouter(tags=["Tournaments"])

def validate_tournament_logic(data: Union[TournamentCreate]):
    today = date.today()

    if data.start_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be in the past"
        )

    if data.end_date and data.end_date < data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date cannot be before start date"
        )

    '''if data.visibility == VisibilityEnum.closed and not data.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Private tournament requires a password"
        )'''

    if data.participant_type == ParticipantEnum.team:
        if not data.team_details:
            raise ValueError("team_details required for 'Team' tournament")
        if data.solo_details:
            raise ValueError("solo_details not allowed for 'Team' tournament")
    if  data.participant_type == ParticipantEnum.solo:
        if not data.solo_details:
            raise ValueError("solo_details required for 'Team' tournament")
        if data.team_details:
            raise ValueError("team_details not allowed for 'Team' tournament")

def validate_tournament_altering(db: Session, db_tournament: Tournament, updated_data: TournamentAlter):
    today = date.today()

    if updated_data.start_date and updated_data.start_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be in the past"
        )

    if updated_data.end_date and updated_data.start_date and updated_data.end_date < updated_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date cannot be before start date"
        )

    if updated_data.end_date and not updated_data.start_date and updated_data.end_date < db_tournament.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date cannot be before start date"
        )

    """if updated_data.visibility == VisibilityEnum.closed and not updated_data.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Private tournament requires a password"
        )"""

    if updated_data.participant_type and updated_data.participant_type == ParticipantEnum.team:
        if not updated_data.team_details:
            raise ValueError("team_details required for 'Team' tournament")
        if updated_data.solo_details:
            raise ValueError("solo_details not allowed for 'Team' tournament")
    if updated_data.participant_type and updated_data.participant_type == ParticipantEnum.solo:
        if not updated_data.solo_details:
            raise ValueError("solo_details required for 'Team' tournament")
        if updated_data.team_details:
            raise ValueError("team_details not allowed for 'Team' tournament")



def add_detail_filed_all(db, tournament: TournamentCreate):
    """Add "detail" filed for tournament."""
    tournament = tournament.__dict__

    detail = get_tournament_detail_by_id_include_deleted(db, tournament["id"])

    if tournament["participant_type"] == ParticipantEnum.solo:
        tournament["solo_details"] = detail
        return TournamentResponse(**tournament)

    if tournament["participant_type"] == ParticipantEnum.team:
        tournament["team_details"] = detail
        return TournamentResponse(**tournament)

    return None

@tournament_router.post("/create", response_model=TournamentResponse, operation_id="create_tournament")
def create_tournament_route(data: TournamentCreate, db: Session = Depends(get_db)):
    user = get_active_user(db, data.created_by)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    validate_tournament_logic(data)

    tournament = create_tournament(db, data)

    if not tournament:
        raise ValueError("Something went wrong.")

    user.tournaments_created.append(tournament) # relationship work

    tournament = add_detail_filed_all_active(db, tournament)
    return tournament


"""test something to connect with frontend"""
@tournament_router.get("/all_active", response_model=ListTournament)
def get_all_active_tournaments_route(db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    tournaments = get_tournaments_all_active(db, pagination, order_by, start)
    total = get_number_of_instances_active(db, Tournament)

    tournaments_with_details = []
    for t in tournaments:
        t_detail = add_detail_filed_all_active(db, t)
        if t_detail:
            tournaments_with_details.append(t_detail)

    response = {
        "data": tournaments_with_details,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None
        response['pagination']["previous"] = f"/tournaments/all_active?page={pagination.page-1}&perPage={pagination.perPage}" if pagination.page > 1 else None
    else:
        response['pagination']['next'] = f"/tournaments/all_active?page={pagination.page+1}&perPage={pagination.perPage}"
        response['pagination']["previous"] = f"/tournaments/all_active?page={pagination.page-1}&perPage={pagination.perPage}" if pagination.page > 1 else None

    return response

@tournament_router.get("/mytournaments/all_active", response_model=ListTournament)
def get_tournament_by_organization_id_route(created_by: int, db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    db_user = get_active_user(db, created_by)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    tournaments = get_mytournaments_all_active(db, pagination, order_by, start, created_by)

    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")

    total = get_number_of_instances_by_id_active(db, Tournament, created_by)

    for i in range(len(tournaments)):
        tournaments[i] = add_detail_filed_all(db, tournaments[i])

        if not tournaments[i]:
            raise ValueError("Something went wrong.")

    response = {
        "data": tournaments,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"]["previous"] = f"/mytournaments/active?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"]['previous'] = f"/mytournaments/active?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/mytournaments/active?page={pagination.page+1}&perPage={pagination.perPage}"
    return response

@tournament_router.get("/mytournaments/all", response_model=ListTournament)
def get_all_mytournaments_route(created_by: int, db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    db_user = get_active_user(db, created_by)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    tournaments = get_mytournaments_all(db, pagination, order_by, start, created_by)

    total = get_number_of_instances_by_id_all(db, Tournament, created_by)

    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")

    for i in range(len(tournaments)):
        tournaments[i] = add_detail_filed_all(db, tournaments[i])

        if not tournaments[i]:
            raise ValueError("Something went wrong.")

    response = {
        "data": tournaments,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"]["previous"] = f"/mytournaments/all?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"]['previous'] = f"/mytournaments/all?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/mytournaments/all?page={pagination.page+1}&perPage={pagination.perPage}"
    return response

@tournament_router.get("/mytournaments/history", response_model=ListTournament)
def get_history_mytournaments_route(created_by: int, db: Session = Depends(get_db), pagination: Pagination = Depends(pagination_params)):
    db_user = get_active_user(db, created_by)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    tournaments = get_mytournaments_history(db, pagination, order_by, start, created_by)

    total = get_number_of_instances_by_id_active(db, Tournament, created_by)

    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")

    for i in range(len(tournaments)):
        tournaments[i] = add_detail_filed_all_active(db, tournaments[i])

        if not tournaments[i]:
            raise ValueError("Something went wrong.")

    response = {
        "data": tournaments,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response['pagination']["next"] = None

        if pagination.page > 1:
            response["pagination"]["previous"] = f"/mytournaments/all?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None
    else:
        if pagination.page > 1:
            response["pagination"]['previous'] = f"/mytournaments/all?page={pagination.page-1}&perPage={pagination.perPage}"
        else:
            response["pagination"]["previous"] = None

        response['pagination']['next'] = f"/mytournaments/all?page={pagination.page+1}&perPage={pagination.perPage}"
    return response

from fastapi import Query

def pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    perPage: int = Query(10, ge=1, le=100, description="Items per page"),
    order: SortEnum = Query(SortEnum.desc, description="Sorting order: asc or desc")
):
    return Pagination(page=page, perPage=perPage, order=order)

@tournament_router.get("/all", response_model=ListTournament)
def get_all_tournaments_route(
    db: Session = Depends(get_db),
    pagination: Pagination = Depends(pagination_params)
):
    order_by = desc if pagination.order == SortEnum.desc else asc

    start = (pagination.page - 1) * pagination.perPage
    end = start + pagination.perPage

    tournaments = get_tournaments_all(db, pagination, order_by, start)
    total = get_number_of_instances_all(db, Tournament)

    tournaments_with_details = []
    for t in tournaments:
        t_detail = add_detail_filed_all(db, t)
        if t_detail:
            tournaments_with_details.append(t_detail)

    response = {
        "data": tournaments_with_details,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    # Configura paginação
    if end >= total:
        response['pagination']["next"] = None
    else:
        response['pagination']['next'] = f"/tournaments/all?page={pagination.page+1}&perPage={pagination.perPage}"

    if pagination.page > 1:
        response["pagination"]["previous"] = f"/tournaments/all?page={pagination.page-1}&perPage={pagination.perPage}"
    else:
        response["pagination"]["previous"] = None

    return response


@tournament_router.get("/details/active/{tournament_id}", response_model=Union[TeamTournamentResponse, SoloTournamentResponse])
def get_active_tournament_detail_route(tournament_id: int, db: Session = Depends(get_db)):
    db_detail = get_tournament_detail_by_id_active(db, tournament_id)

    if not db_detail:
        raise HTTPException(status_code=404, detail="Not Found")

    return db_detail

@tournament_router.get("/details/all/{tournament_id}", response_model=Union[TeamTournamentResponse, SoloTournamentResponse])
def get_all_active_tournament_detail_route(tournament_id: int, db: Session = Depends(get_db)):
    db_detail = get_tournament_detail_by_id_include_deleted(db, tournament_id)

    if not db_detail:
        raise HTTPException(status_code=404, detail="Not Found")

    return db_detail

@tournament_router.delete("/delete/{tournament_id}", response_model=TournamentResponse)
def delete_tournament_route(tournament_id: int, db: Session = Depends(get_db)):
    tournament = delete_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return tournament

@tournament_router.put("/alter/{tournament_id}", response_model=TournamentResponse)
def alter_tournament_route(tournament_id: int, data: TournamentAlter, db: Session = Depends(get_db)):
    db_tournament = get_tournament_active(db, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    validate_tournament_altering(db, db_tournament, data)

    updated_tournament = alter_tournament(db, db_tournament, data)

    return updated_tournament

@tournament_router.post("/join", response_model=TournamentParticipantResponse)
def join_tournament_route(request: JoinTournamentRequest, db: Session = Depends(get_db)):

    tournament = db.query(Tournament)\
        .options(joinedload(Tournament.team_tournament))\
        .filter(Tournament.id == request.tournament_id)\
        .first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tournament.participant_type == ParticipantEnum.team:
        if not request.team_id or not request.user_id:
            raise HTTPException(
                status_code=400,
                detail="team_id and user_id are required for team tournaments"
            )

        participant = join_tournament_team(
            db,
            tournament,
            request.team_id,
            request.user_id
        )

        if not participant:
            raise HTTPException(
                status_code=400,
                detail="Could not join tournament with this team"
            )

        return participant

    # 👉 TORNEIO SOLO
    if tournament.participant_type == ParticipantEnum.solo:
        if not request.user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id is required for solo tournaments"
            )

        participant = join_tournament_solo(
            db,
            tournament,
            request.user_id
        )

        if not participant:
            raise HTTPException(
                status_code=400,
                detail="Could not join tournament as solo participant"
            )

        return participant

@tournament_router.post("/leave", response_model=TournamentParticipantResponse)
def leave_tournament_route(request: LeaveTournamentRequest, db: Session = Depends(get_db)):

    participant = None

    if request.team_id:
        participant = leave_tournament_team(
            db,
            tournament_id=request.tournament_id,
            team_id=request.team_id,
            user_id=request.user_id
        )

    elif request.user_id:
        participant = leave_tournament_solo(
            db,
            tournament_id=request.tournament_id,
            user_id=request.user_id
        )

    if not participant:
        raise HTTPException(
            status_code=400,
            detail="User is not participating in this tournament"
        )

    return participant




@tournament_router.get("/filter/min_age", response_model=List[TournamentResponse])
def filter_min_age_tournament_route(min_age: int, db: Session = Depends(get_db)):
    tournaments = get_tournaments_by_min_age(db, min_age)
    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")
    return tournaments

@tournament_router.get("/filter/visibility", response_model=List[TournamentResponse])
def filter_visibility_tournament_route(visibility: VisibilityEnum, db: Session = Depends(get_db)):
    tournaments = get_tournaments_by_visibility(db, visibility.value)
    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")
    return tournaments

@tournament_router.get("/filter/sport", response_model=List[TournamentResponse])
def filter_sport_tournament_route(sport: SportEnum, db: Session = Depends(get_db)):
    tournaments = get_tournaments_by_sport(db, sport.value)
    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")
    return tournaments

@tournament_router.get("/filter/start_date", response_model=List[TournamentResponse])
def filter_visibility_tournament_route(start_date: datetime, db: Session = Depends(get_db)):
    tournaments = get_tournaments_by_start_date(db, start_date)
    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")
    return tournaments

@tournament_router.get("/filter/location", response_model=List[TournamentResponse])
def filter_location_route(location: str, db: Session = Depends(get_db)):
    tournaments = get_tournaments_by_location(db, location)
    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")
    return tournaments


@tournament_router.get("/filter/joined", response_model=ListTournament)
def filter_joined_route(
    user_id: int,
    db: Session = Depends(get_db),
    pagination: Pagination = Depends(pagination_params)
):
    order_by = desc if pagination.order == SortEnum.desc else asc

    start = 0 if pagination.page == 1 else (pagination.page - 1) * pagination.perPage
    end = pagination.perPage + start

    tournaments = get_tournaments_by_participant_id(db, user_id)
    total = len(tournaments)

    tournaments = tournaments[start:end]

    tournaments_with_details = []
    for t in tournaments:
        t_detail = add_detail_filed_all_active(db, t)
        if t_detail:
            tournaments_with_details.append(t_detail)

    response = {
        "data": tournaments_with_details,
        "total": total,
        "count": pagination.perPage,
        "pagination": {}
    }

    if end >= total:
        response["pagination"]["next"] = None
    else:
        response["pagination"]["next"] = f"/tournaments/filter/joined?user_id={user_id}&page={pagination.page+1}&perPage={pagination.perPage}"

    response["pagination"]["previous"] = (
        f"/tournaments/filter/joined?user_id={user_id}&page={pagination.page-1}&perPage={pagination.perPage}"
        if pagination.page > 1 else None
    )

    return response

"""
@tournament_router.get("/filter/joined", response_model=List[TournamentResponse])
def filter_joined_route(user_id: int, db: Session = Depends(get_db)):
    tournaments = get_tournaments_by_participant_id(db, user_id)
    if not tournaments:
        raise HTTPException(status_code=404, detail="No tournaments found")
    return tournaments
"""

@tournament_router.get("/{tournament_id}", response_model=TournamentResponse)
def get_tournament_route(tournament_id: int, db: Session = Depends(get_db)):
    db_tournament = get_tournament_active(db, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    tournament = add_detail_filed_all_active(db, db_tournament)

    if not tournament:
        raise ValueError("Something went wrong.")

    return tournament

@tournament_router.get("/tournaments/{tournament_id}")
async def get_tournament_details(tournament_id: int):
    tournament = get_tournament_by_id(tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return {
        "id": tournament.id,
        "name": tournament.name,
        "start_date": tournament.start_date,
        "end_date": tournament.end_date,
        "location": tournament.location,
        "participant_type": tournament.participant_type,
        "team_details": tournament.team_details,
        "solo_details": tournament.solo_details,
        "rules": tournament.rules,
        "organizer_name": tournament.organizer.name,
        "organizer_email": tournament.organizer.email,
        "organizer_phone": tournament.organizer.phone,
        "participants_list": tournament.participants_list,
    }
