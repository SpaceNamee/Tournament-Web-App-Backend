from datetime import datetime, date, timezone

from enum import member

from typing import Type, Union

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, DeclarativeMeta
from sqlalchemy.orm import joinedload

from fastapi import HTTPException, Query

from models import User, Tournament, SoloTournament, TeamTournament, Team, TeamMember, ManualParticipant, \
    TournamentParticipant, VisibilityEnum, TournamentTimeFilter, SortEnum, TournamentTeamMember
from schemas import UserCreate, UserAlter, SportEnum, ParticipantManualCreate, ParticipantManualAlter, ParticipantEnum, \
    TournamentCreate, Pagination, TournamentAlter, TeamUpdate, TournamentResponse, SoloTournamentAlter, \
    TeamTournamentAlter


# -------------------------
# CRUD OPERATIONS
# -------------------------

# ---- PAGINATION ----
def pagination_params(
        page: int = Query(ge=1, required=False, default=1, le=50000),
        perpage: int = Query(ge=1, le=100, required=False, default=10),
        order: SortEnum = SortEnum.desc
    ):
    return Pagination(perPage=perpage, page=page, order=order.value)

def get_number_of_instances_active(db: Session, model: Type[DeclarativeMeta]):
    return db.query(func.count(model.id)).filter(model.deleted_at.is_(None)).scalar()

def get_number_of_instances_all(db: Session, model: Type[DeclarativeMeta]):
    return db.query(func.count(model.id)).scalar()

def get_number_of_instances_by_id_active(db: Session, model: Type[DeclarativeMeta], instance_id: int):
    return db.query(func.count(model.id)).filter(model.created_by == instance_id, model.deleted_at.is_(None)).scalar()

def get_number_of_instances_by_id_all(db: Session, model: Type[DeclarativeMeta], instance_id: int):
    return db.query(func.count(model.id)).filter(model.created_by == instance_id).scalar()

# -- -- MANUAL PARTICIPANTS CRUD ----

# TODO Remake with current_user dependence (current_user: User = Depends(get_current_user),)
def create_manual_participant(db: Session, participant: ParticipantManualCreate):
    db_manual_participant = ManualParticipant(
        name= participant.name,
        created_by = participant.created_by
    )

    try:
        db.add(db_manual_participant)
        db.commit()
        db.refresh(db_manual_participant)
        return db_manual_participant
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't add new manual participant."
        )

def get_manual_participant_by_id(db: Session, man_id: int):
    return db.query(ManualParticipant).filter(ManualParticipant.id == man_id, ManualParticipant.deleted_at.is_(None)).first()

def get_manual_participant_by_name(db: Session, name: str):
    return db.query(ManualParticipant).filter(ManualParticipant.name == name, ManualParticipant.deleted_at.is_(None)).first()

def get_manual_participant_by_name_and_creator(db: Session, name: str, created_by: int):
    return db.query(ManualParticipant).filter(ManualParticipant.name == name, ManualParticipant.created_by == created_by, ManualParticipant.deleted_at.is_(None)).first()

def get_manual_active_participants(db: Session):
    return db.query(ManualParticipant).filter(ManualParticipant.deleted_at.is_(None)).all()

def get_manual_participants(db: Session):
    return db.query(ManualParticipant).all()

def delete_manual_participant(db: Session, manual_participant_id: int):
    manual_participant = get_manual_participant_by_id(db, manual_participant_id)

    if not manual_participant:
        return None

    if manual_participant.deleted_at is None:
        manual_participant.deleted_at = datetime.now(timezone.utc)

        try:
            db.commit()
            db.refresh(manual_participant)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Invalid creator_id or duplicate participant"
            )

    return manual_participant

def delete_all_participants_by_organizator_id(db: Session, created_by: int):
    user_db = get_active_user(db, created_by)

    if not user_db:
        return None

    manual_participants = user_db.manual_participants

    for manual_participant in manual_participants:
        manual_participant.deleted_at = datetime.now(timezone.utc)
        try:
            db.commit()
            db.refresh(manual_participant)
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Can't delete the manually entered participant."
            )
    return 200
def alter_manual_participant(db: Session, participant_id: int, update_data: ParticipantManualAlter):
    db_manual_participant = get_manual_participant_by_id(db, participant_id)

    if not db_manual_participant:
        return None  # Signal “not found”

    if update_data.name is not None:
        db_manual_participant.name = update_data.name

    try:
        db.commit()
        db.refresh(db_manual_participant)
        return db_manual_participant
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )

# ---- USER CRUD ----
def base_user_query(db: Session):
    return db.query(User).filter(User.deleted_at.is_(None))

def create_user(db: Session, user: UserCreate):
    db_user = User(
        name=user.name,
        nickname=user.nickname,
        email=user.email,

        # optional fields
        phone_number=user.phone_number,
        date_of_birth=user.date_of_birth,

        # notification settings (have defaults anyway)
        tournament_notif=user.tournament_notif,
        match_notif=user.match_notif,
        general_notif=user.general_notif,
        # TODO hash password
        hashed_password=user.password,
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )

def get_active_user(db: Session, user_id: int):
    return base_user_query(db).filter(User.id == user_id).first()

def get_user_all(db: Session):
    return db.query(User).all()

def get_user_all_active(db: Session):
    return base_user_query(db).all()

def alter_user(db: Session, db_user: User, data: UserAlter):
    # Update only fields that were provided
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(db_user, field, value)
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )

def get_user_by_email(db: Session, email: str):
    return base_user_query(db).filter(User.email == email).first()

def get_user_by_nickname(db: Session, nickname: str):
    return base_user_query(db).filter(User.nickname == nickname).first()

def delete_user(db: Session, user_id: int):
    user = get_active_user(db, user_id)

    if not user:
        return None

    user.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )

# ---- TOURNAMENT CRUD ----

def base_tournament_query(db: Session):
    return db.query(Tournament).filter(Tournament.deleted_at.is_(None))

def add_detail_filed_all_active(db, tournament: Tournament, user_id: int = None):
    tournament_dict = tournament.__dict__
    detail = get_tournament_detail_by_id_include_deleted(db, tournament.id)
    
    tournament_dict["team_details" if tournament.participant_type == ParticipantEnum.team else "solo_details"] = detail
    
    if user_id:
        tournaments_user_participated = get_tournaments_by_participant_id(db, user_id)
        tournament_dict["joined"] = any(t.id == tournament.id for t in tournaments_user_participated)
    else:
        tournament_dict["joined"] = False

    return TournamentResponse(**tournament_dict)


def create_tournament(db: Session, data: TournamentCreate):
    tournament = Tournament(
        created_by=data.created_by,
        name=data.name,
        sport=data.sport,
        bracket_type=data.bracket_type,
        visibility=data.visibility,
        participant_type=data.participant_type,
        organizer_contact=data.organizer_contact,
        hashed_password=data.hashed_password,
        min_age=data.min_age,
        start_date=data.start_date,
        end_date=data.end_date,
        start_time=data.start_time,
        location=data.location,
        rules=data.rules,
    )
    try:
        db.add(tournament)
        db.flush()  # get tournament.id
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )

    if data.participant_type == ParticipantEnum.team:

        team = TeamTournament(
            tournament_id=tournament.id,
            max_teams=data.team_details.max_teams,
            players_per_team=data.team_details.players_per_team,
        )

        try:
            db.add(team)
            db.commit()
            db.refresh(team)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Invalid creator_id or duplicate participant"
            )

    if data.participant_type == ParticipantEnum.solo:
        solo = SoloTournament(
            tournament_id=tournament.id,
            max_players=data.solo_details.max_players,
        )
        try:
            db.add(solo)
            db.commit()
            db.refresh(solo)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Invalid creator_id or duplicate participant"
            )

    db.refresh(tournament)

    return tournament

def alter_tournament(db: Session, db_tournament: Tournament, data: TournamentAlter):
    tournament_detail = get_tournament_detail_by_id_active(db, db_tournament.id)

    if not tournament_detail:
        raise HTTPException(status_code=404, detail="Not found tournament detail")

    for field, value in data.model_dump(exclude_none=True).items():
        print(field)
        if field == "solo_details":
            alter_solo_tournament_detail_by_tournament_id(db, tournament_detail, value)
        elif field == "team_details":
            alter_team_tournament_detail_by_tournament_id(db, tournament_detail, value)
        else:
            setattr(db_tournament, field, value)

    try:
        db.commit()
        db.refresh(db_tournament)
        return add_detail_filed_all_active(db, db_tournament)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't save changes"
        )

def get_solo_tournament_by_tournament_id(db: Session, tournament_id: int):
    return db.query(SoloTournament).filter(SoloTournament.tournament_id == tournament_id).first()

def get_team_tournament_by_tournament_id(db: Session, tournament_id:int):
    return db.query(TeamTournament).filter(TeamTournament.tournament_id == tournament_id).first()

def get_tournament_detail_by_id_active(db: Session, tournament_id: int):
    db_tournament = get_tournament_active(db, tournament_id)

    if not db_tournament:
        return None

    if db_tournament.participant_type == ParticipantEnum.team:
        detail = get_team_tournament_by_tournament_id(db, tournament_id)
        return detail

    if db_tournament.participant_type == ParticipantEnum.solo:
        detail = get_solo_tournament_by_tournament_id(db, tournament_id)
        return detail
    return None
def get_tournament_detail_by_id_include_deleted(db: Session, tournament_id: int):
    db_tournament = get_tournament_including_deleted(db, tournament_id)

    if not db_tournament:
        return None

    if db_tournament.participant_type == ParticipantEnum.team:
        detail = get_team_tournament_by_tournament_id(db, tournament_id)
        return detail

    if db_tournament.participant_type == ParticipantEnum.solo:
        detail = get_solo_tournament_by_tournament_id(db, tournament_id)
        return detail
    return None
def alter_solo_tournament_detail_by_tournament_id(db: Session, tournament_detail: SoloTournament,
                                                  updated_data: SoloTournamentAlter):
    for field, value in updated_data.items():
        if value is not None:
            setattr(tournament_detail, field, value)

    try:
        db.commit()
        db.refresh(tournament_detail)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Can't save changes to tournament detail")

def alter_team_tournament_detail_by_tournament_id(db: Session, tournament_detail: TeamTournament,
                                                  updated_data: TeamTournamentAlter):
    for field, value in updated_data.items():
        if value is not None:
            setattr(tournament_detail, field, value)

    try:
        db.commit()
        db.refresh(tournament_detail)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Can't save changes to tournament detail")

# def get_all_solo_tournament(db: Session, tournament_id: int):
#     return db.query(SoloTournament).all()

# def get_all_team_tournament(db: Session, tournament_id:int):
#     return db.query(TeamTournament).all()

def get_tournaments_all_active(db: Session, pagination: Pagination, order_by, start: int):
    return (
        base_tournament_query(db)
        .order_by(order_by(Tournament.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_tournaments_all(db: Session, pagination: Pagination, order_by, start: int):
    return (
        db.query(Tournament)
        .order_by(order_by(Tournament.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_mytournaments_all_active(db: Session, pagination: Pagination, order_by, start: int, created_by: int):
    return (
        base_tournament_query(db)
        .filter(Tournament.created_by == created_by)
        .order_by(order_by(Tournament.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_mytournaments_all(db: Session, pagination: Pagination, order_by, start: int, created_by: int):
    return (
        db.query(Tournament)
        .filter(Tournament.created_by == created_by)
        .order_by(order_by(Tournament.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_mytournaments_organized_history(db: Session, pagination: Pagination, order_by, start: int, created_by: int):
    today = datetime.date.today()
    return (
        db.query(Tournament)
        .filter(
            Tournament.created_by == created_by,
            or_(
                Tournament.end_date < today,
                (Tournament.end_date.is_(None)) & (Tournament.start_date < today),
            )
        )
        .order_by(order_by(Tournament.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_mytournaments_history(db: Session, pagination: Pagination, order_by, start: int, created_by: int):
    today = date.today()
    return (
        db.query(Tournament)
        .filter(
            Tournament.created_by == created_by,
            or_(
                Tournament.end_date < today,
                (Tournament.end_date.is_(None)) & (Tournament.start_date < today),
            )
        )
        .order_by(order_by(Tournament.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_tournament_active(db: Session, tournament_id: int):
    return base_tournament_query(db).filter(Tournament.id == tournament_id).first()

def get_tournament_including_deleted(db: Session, tournament_id: int):
    return db.query(Tournament).filter(Tournament.id == tournament_id).first()

def get_tournaments_by_sport(db: Session, sport: SportEnum):
    return base_tournament_query(db).filter(Tournament.sport == sport).all()

def get_tournaments_by_location(db: Session, location: str):
    return base_tournament_query(db).filter(Tournament.location == location).all()

def get_tournaments_by_visibility(db: Session, visibility: VisibilityEnum):
    return base_tournament_query(db).filter(Tournament.visibility == visibility).all()

def get_tournaments_by_start_date(db: Session, start_date: datetime):
    return base_tournament_query(db).filter(Tournament.start_date == start_date).all()

def get_tournaments_by_period(db: Session, start_date: datetime):
    return base_tournament_query(db).filter(Tournament.start_date == start_date).all()

def get_tournaments_by_min_age(db: Session, min_age: int):
    return base_tournament_query(db).filter(Tournament.min_age >= min_age).all()

def get_tournaments_by_participant_id(db: Session, user_id: int):
    tournaments = []

    solo_participants = db.query(TournamentParticipant).filter(TournamentParticipant.user_id == user_id).all()
    for sp in solo_participants:
        t = base_tournament_query(db).filter(Tournament.id == sp.tournament_id).first()
        if t and t not in tournaments:
            tournaments.append(t)

    team_members = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
    for tm in team_members:
        ttm_entries = db.query(TournamentTeamMember).filter(TournamentTeamMember.team_id == tm.team_id).all()
        for ttm in ttm_entries:
            t = base_tournament_query(db).filter(Tournament.id == ttm.tournament_id).first()
            if t and t not in tournaments:
                tournaments.append(t)

    return tournaments



def delete_tournament(db: Session, tournament_id: int):
    db_tournament = get_tournament_active(db, tournament_id)

    if not db_tournament:
        return None

    db_tournament.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(db_tournament)
        return db_tournament
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid creator_id or duplicate participant"
        )

# ---- TEAM CRUD ----
def base_team_query(db: Session):
    return db.query(Team).filter(Team.deleted_at.is_(None))

def create_team(db: Session, data, creator_id: int):
    team_data = {k: v for k, v in data.__dict__.items() if k != "created_by"}
    team = Team(**team_data, created_by=creator_id)  

    try:
        db.add(team)
        db.commit()
        db.refresh(team)
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == creator_id
        ).first()

        if not existing_member:
            creator_member = TeamMember(team_id=team.id, user_id=creator_id)
            db.add(creator_member)
            db.commit()
            db.refresh(creator_member)

        return team
    except IntegrityError:
        db.rollback()
        return None




def get_active_team(db: Session, team_id: int):
    return base_team_query(db).filter(Team.id == team_id).first()

def get_teams_all(db: Session, pagination: Pagination, order_by, start: int):
    return (
        db.query(Team)
        .order_by(order_by(Team.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_teams_all_active(db: Session, pagination: Pagination, order_by, start: int):
    return (
        base_team_query(db)
        .order_by(order_by(Team.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_my_all_teams(db: Session, pagination: Pagination, order_by, start: int, created_by: int):
    return (
        db.query(Team)
        .filter(Team.created_by == created_by)
        .order_by(order_by(Team.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_my_active_teams(db: Session, pagination: Pagination, order_by, start: int, created_by: int):
    return (
        base_team_query(db)
        .filter(Team.created_by == created_by)
        .order_by(order_by(Team.id))
        .limit(pagination.perPage)
        .offset(start)
        .all()
    )

def get_teams_by_user_and_sport(db: Session, user_id: int, sport: SportEnum):
    return base_team_query(db).filter(Team.created_by == user_id,
                                 Team.sport == sport,).all()

def get_teams_by_location(db: Session, location: str):
    return base_team_query(db).filter(Team.location == location).all()

def get_teams_by_visibility(db: Session, visibility: int):
    return base_team_query(db).filter(Team.visibility == visibility).all()

def get_teams_by_sport(db: Session, sport: SportEnum):
    return base_team_query(db).filter(Team.sport == sport).all()

def get_teams_by_min_age(db: Session, min_age: int):
    return base_team_query(db).filter(Team.min_age >= min_age).all()

def get_teams_by_user_id(db: Session, user: User):
    teams = (
        db.query(Team)
        .filter(Team.created_by == user.id, Team.deleted_at.is_(None))
        .options(joinedload(Team.members))
        .all()
    )
    for team in teams:
        team.current_players = len([m for m in team.members if m.deleted_at is None])

    return teams

def get_teams_with_members_by_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        return []

    teams = (
        db.query(Team)
        .filter(Team.created_by == user_id, Team.deleted_at.is_(None))
        .options(joinedload(Team.members).joinedload(TeamMember.user))
        .all()
    )

    result = []
    for team in teams:
        active_members_count = len([m for m in team.members if m.deleted_at is None])
        result.append({
            "id": team.id,
            "name": team.name,
            "sport": team.sport.value if team.sport else None,
            "max_players": team.max_players,
            "current_players": active_members_count,  # ⚡ Calculado dinamicamente
            "members": [{"id": m.user.id, "name": m.user.name} for m in team.members if m.deleted_at is None],
            "location": team.location,
            "min_age": team.min_age,
            "visibility": team.visibility.value if team.visibility else None,
        })
    return result



def alter_team(db: Session, updated_data: TeamUpdate, db_team: Team):
    for field, value in updated_data.model_dump(exclude_none=True).items():
        setattr(db_team, field, value)

    try:
        db.commit()
        db.refresh(db_team)
        return db_team
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't save changes"
        )

def delete_team(db: Session, team_id: int):
    db_team = get_active_team(db, team_id)

    if not db_team:
        return None

    db_team.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(db_team)
        return db_team
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Something go wrong with deleting."
        )

# ---- INVITE CRUD ----


# ---- MATCH CRUD ----


# ---- REQUESTS CRUD ----


# ---- TOURNAMENT MEMBERS CRUD ----

def get_tournament_members(db: Session, tournament_id: int):
    return db.query(TournamentParticipant).filter(TournamentParticipant.tournament_id == tournament_id).all()

def get_tournament_member_by_user_id(db: Session, user_id: int, tournament_id: int):
    return db.query(TournamentParticipant).filter(TournamentParticipant.tournament_id == tournament_id,
                                                   TournamentParticipant.user_id == user_id).first()

def get_tournament_member_by_team_id(db: Session, team_id: int, tournament_id: int):
    return db.query(TournamentParticipant).filter(TournamentParticipant.tournament_id == tournament_id,
                                                   TournamentParticipant.team_id == team_id).first()

def get_tournament_participant_active(db: Session, tournament_id: int, user_id: int):
    return db.query(TournamentParticipant).filter(TournamentParticipant.user_id == user_id,
                                           TournamentParticipant.tournament_id == tournament_id).first()

def delete_tournament_members(db: Session, tournament_id: int, user_id: int):
    db_tournament_participant = get_tournament_participant_active(db, tournament_id, user_id)

    if not db_tournament_participant:
        return None

    db_tournament_participant.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(db_tournament_participant)
        return None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Something go wrong."
        )

def delete_tournament_team_members(db: Session, team_id: int, tournament_id: int):
    db.query(TournamentParticipant).filter(TournamentParticipant.team_id == team_id,
                                            TournamentParticipant.tournament_id == tournament_id).delete()
    db.commit()
    db.refresh(TournamentParticipant)
    return None

# ---- TEAM MEMBERS CRUD ----
def get_team_members(db: Session, team_id: int):
    return db.query(TeamMember).filter(TeamMember.team_id == team_id).all()

def get_team_member_by_user_id(db: Session, user_id: int, team_id: int):
    return db.query(TeamMember).filter(TeamMember.team_id == team_id,
                                        TeamMember.user_id == user_id,).first()

# ---- JOIN TEAM/TOURNAMENTS CRUD ----
def join_team(db: Session, team_id: int, user_id: int, password: str | None):
    from models import TeamMember

    team = get_active_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    player = get_active_user(db, user_id)
    if not player:
        raise HTTPException(status_code=404, detail="User not found")

    # --- PASSWORD CHECK ---
    """
    if team.visibility == VisibilityEnum.closed:
        if not password:
            raise HTTPException(status_code=400, detail="Password is required to join this team")
        if team.hashed_password != password:
            raise HTTPException(status_code=401, detail="Incorrect password")
    """

    # Already member
    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
        TeamMember.deleted_at.is_(None)
    ).first()

    if existing_member:
        return existing_member

    # Team full
    if len(team.members) >= team.max_players:
        raise HTTPException(status_code=403, detail="Team is full")

    new_member = TeamMember(team_id=team_id, user_id=user_id)

    try:
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return new_member

def leave_team(db: Session, team_id: int, user_id: int):
    team = get_active_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    player = get_active_user(db, user_id)
    if not player:
        raise HTTPException(status_code=404, detail="User not found")

    # Already member
    existing_member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id,
                                                  TeamMember.deleted_at.is_(None)).first()

    if not existing_member:
        raise HTTPException(status_code=404, detail="User is not in this team")

    existing_member.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(existing_member)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't delete the instance of TeamMember table."
        )

    team.current_players -= 1
    try:
        db.commit()
        db.refresh(team)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't change the current number of players."
        )

    # if someone leave the team, team is not full and can't take part in tournament
    if team.tournament_participations:
        for tournament_participant in team.tournament_participations:
            tournament_participant.deleted_at = datetime.now(timezone.utc)

    return {"message": "Left the team successfully"}

def join_tournament_solo(db: Session, tournament: Tournament, user_id: int):
    if not tournament.solo_tournament:
        raise HTTPException(
            status_code=400,
            detail="Solo tournament details not configured."
        )
    if tournament.solo_tournament.current_players >= tournament.solo_tournament.max_players:
        raise HTTPException(
            status_code=400,
            detail="Tournament is full."
        )
    player = get_active_user(db, user_id)
    if not player:
        raise HTTPException(status_code=404, detail="User not found")
    existing_member = (
        db.query(TournamentParticipant)
        .filter(
            TournamentParticipant.tournament_id == tournament.id,
            TournamentParticipant.user_id == user_id,
            TournamentParticipant.deleted_at.is_(None)
        )
        .first()
    )
    if existing_member:
        raise HTTPException(status_code=409, detail="Already joined the tournament")

    # 5️⃣ Cria o participante
    new_participant = TournamentParticipant(tournament_id=tournament.id, user_id=user_id)
    try:
        db.add(new_participant)
        db.commit()
        db.refresh(new_participant)
    except:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't add new participant."
        )
    tournament_detail = get_tournament_detail_by_id_active(db, tournament.id)
    tournament_detail.current_players += 1
    try:
        db.commit()
        db.refresh(tournament_detail)
    except:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Can't update current number of participants."
        )

    return new_participant

def join_tournament_team(db: Session, tournament: Tournament, team_id: int, user_id: int):
    team = get_active_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if not tournament.team_tournament:
        raise HTTPException(status_code=400, detail="Tournament team setup missing")

    if team.current_players < tournament.team_tournament.players_per_team:
        raise HTTPException(status_code=400, detail="Your team is not full.")
    existing_team = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id,
        TournamentParticipant.team_id == team_id,
        TournamentParticipant.deleted_at.is_(None)
    ).first()
    if existing_team:
        raise HTTPException(status_code=409, detail="Already joined the tournament")
    tournament_team = TournamentParticipant(tournament_id=tournament.id, team_id=team_id)
    db.add(tournament_team)
    tournament.team_tournament.current_teams += 1

    try:
        db.flush() 
        for member in team.members:
            if not member.user_id:
                print(f"⚠️ Skipping member with invalid user_id: {member.id}")
                continue
            snapshot = TournamentTeamMember(
                tournament_id=tournament.id,
                team_id=team_id,
                user_id=member.user_id
            )
            db.add(snapshot)
            print(f"Added snapshot for user {member.user_id}")

        db.commit()
        db.refresh(tournament_team)
        db.refresh(tournament.team_tournament)
        print("✅ Tournament team joined successfully")

    except IntegrityError as e:
        db.rollback()
        print(f"❌ IntegrityError: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to join tournament: {str(e)}")

    return tournament_team

def leave_tournament(db: Session, tournament_id: int, user_id: int):
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if tournament.participant_type == 'solo':
        existing_member = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament.id,
            TournamentParticipant.user_id == user_id, TournamentParticipant.deleted_at.is_(None)
        ).first()
        if existing_member:
            db.delete(existing_member)
            if tournament.solo_tournament.current_players > 0:
                tournament.solo_tournament.current_players -= 1
            db.add(tournament)
            db.commit()
            db.refresh(tournament)
            return tournament
        return None
    elif tournament.participant_type == 'team':
        team = db.query(Team).filter(Team.created_by == user_id,
                                     Team.sport == tournament.sport).first()
        if not team:
            raise HTTPException(status_code=404, detail="No suitable team found")
        existing_team = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.team_id == team.id,
        ).first()
        if not existing_team:
            raise HTTPException(status_code=404, detail="Team has not joined the tournament")
        db.delete(existing_team)
        if tournament.team_tournament.current_teams > 0:
            tournament.team_tournament.current_teams -= 1
        db.add(tournament)
        db.commit()
        db.refresh(tournament)
        return tournament
    else:
        return None

def leave_tournament_solo(db: Session, tournament_id: int, user_id: int):
    tournament = get_tournament_active(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    existing_member = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id,
        TournamentParticipant.user_id == user_id, TournamentParticipant.deleted_at.is_(None)
    ).first()

    if existing_member:
        existing_member.deleted_at = datetime.now(timezone.utc)

        tournament_detail = get_tournament_detail_by_id_active(db, tournament_id)
        tournament_detail.current_players -= 1

        try:
            db.commit()
            db.refresh(tournament_detail)
            db.refresh(existing_member)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail='Something went wrong during leaving tournament.')

        return existing_member
    return None

def leave_tournament_team(db: Session, tournament_id: int, team_id: int):
    tournament = get_tournament_active(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    existing_team = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id,
        TournamentParticipant.team_id == team_id, TournamentParticipant.deleted_at.is_(None)
    ).first()

    if existing_team:
        existing_team.deleted_at = datetime.now(timezone.utc)

        tournament_detail = get_tournament_detail_by_id_active(db, tournament_id)
        tournament_detail.current_teams -= 1
        try:
            db.commit()
            db.refresh(tournament_detail)
            db.refresh(existing_team)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail='Something went wrong during leaving tournament.')

        return existing_team
    return None