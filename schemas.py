# schemas.py
from pydantic import BaseModel, EmailStr, conint, PositiveInt, NonNegativeInt, constr, StringConstraints, Field, \
    model_validator, ConfigDict
from typing_extensions import Annotated
from typing import Optional, List
from datetime import date, time, datetime
from models import SportEnum, ParticipantEnum, TournamentTypeEnum, VisibilityEnum, SortEnum
from pydantic import BaseModel, Field
from typing import Optional

# ==========================
# AUTH / TOKEN SCHEMAS
# ==========================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None

# ==========================
# PAGINATION
# ==========================

class Pagination(BaseModel):
    perPage: int
    page: int
    order: SortEnum

# ==========================
# USER SCHEMAS
# ==========================

# Password = Annotated[
#     str,
#     StringConstraints(
#         min_length=8,
#         pattern=r"^(?=.*[A-Z])(?=.*\d).+$"
#     )
# ]

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    nickname: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

    phone_number: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None

    tournament_notif: bool = True
    match_notif: bool = True
    general_notif: bool = True


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    nickname: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None

    tournament_notif: bool = True
    match_notif: bool = True
    general_notif: bool = True

class UserAlter(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    nickname: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None

    phone_number: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None

    tournament_notif: Optional[bool] = None
    match_notif: Optional[bool] = None
    general_notif: Optional[bool] = None

class UserInDB(UserBase):
    hashed_password: str

    id: int
    is_admin: bool
    is_verified: bool

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # SQLAlchemy compatibility

class UserResponse(UserInDB):
    age: Optional[int] = None

    @staticmethod
    def calculate_age(dob: Optional[date]) -> Optional[int]:
        if not dob:
            return None
        today = date.today()
        return today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )

class UserPublic(BaseModel):
    id: int
    name: str
    nickname: str
    age: Optional[int]
    is_verified: bool

    class Config:
        from_attributes = True

# ==========================
# USER MANUAL SCHEMAS
# ==========================

class ParticipantManualBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    created_by: int

class ParticipantManualCreate(ParticipantManualBase):
    pass

class ParticipantManualAlter(BaseModel):
    name: Optional[str] = Field(None, max_length=100)

class ParticipantManualResponse(ParticipantManualBase):
    id: int
    created_by: int | None

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # SQLAlchemy compatibility

# ==========================
# TEAM SCHEMAS
# ==========================

class TeamBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    sport: SportEnum
    visibility: VisibilityEnum

    max_players: int = Field(..., ge=1, le=100)
    min_age: Optional[int] = Field(None, ge=0, le=100)

    location: str = Field(..., min_length=2, max_length=100)

    rules: Optional[str] = Field(None, max_length=2000)

class TeamCreate(TeamBase):
    created_by: int
    hashed_password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=128,
        description="Optional team password (will be hashed)"
    )

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    visibility: Optional[VisibilityEnum] = None

    max_players: Optional[int] = Field(None, ge=1, le=100)
    min_age: Optional[int] = Field(None, ge=0, le=100)

    location: Optional[str] = Field(None, min_length=2, max_length=100)

    rules: Optional[str] = Field(None, max_length=2000)

    hashed_password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=128,
        description="Optional team password (will be hashed)"
    )

class TeamResponse(TeamBase):
    id: int
    created_by: int
    current_players: int

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class MessageResponse(BaseModel):
    message: str

class ListTeam(BaseModel):
    data: List[TeamResponse]
    total: int
    count: int
    pagination: dict
# ==========================
# SOLO TOURNAMENT SCHEMAS
# ==========================

class SoloTournamentBase(BaseModel):
    max_players: int = Field(..., ge=2, le=200)

class SoloTournamentCreate(SoloTournamentBase):
    pass

class SoloTournamentAlter(BaseModel):
    max_players: int = Field(None, ge=2, le=200)

class SoloTournamentResponse(SoloTournamentBase):
    tournament_id: int
    current_players: int

    model_config = {
        "from_attributes": True
    }

# ==========================
# TEAM TOURNAMENT SCHEMAS
# ==========================

class TeamTournamentBase(BaseModel):
    max_teams: int = Field(..., ge=2, le=200)
    players_per_team: int = Field(..., ge=1, le=50)

class TeamTournamentCreate(TeamTournamentBase):
    pass

class TeamTournamentAlter(BaseModel):
    max_teams: int = Field(None, ge=2, le=200)
    players_per_team: int = Field(None, ge=1, le=50)

class TeamTournamentResponse(TeamTournamentBase):
    tournament_id: int
    current_teams: int

    model_config = {
        "from_attributes": True
    }

# ==========================
# TOURNAMENT SCHEMAS
# ==========================

class TournamentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    organizer_contact: str = Field(..., min_length=5, max_length=50, description="Phone number, email, or messenger contact")

    bracket_type: TournamentTypeEnum
    visibility: VisibilityEnum
    sport: SportEnum
    participant_type: ParticipantEnum

    min_age: Optional[int] = Field(None, ge=0, le=100)
    hashed_password: Optional[str] = Field(None, min_length=6, max_length=255)

    start_date: date
    end_date: Optional[date] = None
    start_time: Optional[time] = None

    location: str = Field(..., min_length=2, max_length=100)

    rules: Optional[str] = Field(None, max_length=1000)

    team_details: TeamTournamentCreate | None = None
    solo_details: SoloTournamentCreate | None = None

class TournamentCreate(TournamentBase):
    created_by: int
    hashed_password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=128,
        description="Optional team password (will be hashed)"
    )

class TournamentAlter(TournamentBase):
    name: str = Field(None, min_length=3, max_length=150)
    organizer_contact: str = Field(None, min_length=5, max_length=50, description="Phone number, email, or messenger contact")

    start_date: date = None

    bracket_type: Optional[TournamentTypeEnum] = None
    visibility: Optional[VisibilityEnum] = None
    sport: Optional[SportEnum] = None
    participant_type: Optional[ParticipantEnum] = None

    location: str = Field(None, min_length=2, max_length=100)

    team_details: TeamTournamentAlter | None = None
    solo_details: SoloTournamentAlter | None = None

class TournamentResponse(TournamentBase):
    id: int
    created_by: int

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    team_details: TeamTournamentResponse | None = None
    solo_details: SoloTournamentResponse | None = None
    model_config = {
        "from_attributes": True
    }

class ListTournament(BaseModel):
    data: List[TournamentResponse]
    total: int
    count: int
    pagination: dict

# ==========================
# TEAM MEMBER
# ==========================

class TeamMember(BaseModel):
    team_id: int
    user_id: int

class JoinTeamRequest(TeamMember):
    password: Optional[str] = None

class TeamMemberResponse(TeamMember):
    id: int

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# ==========================
# TOURNAMENT PARTICIPANT
# ==========================

class TournamentParticipantBase(BaseModel):
    tournament_id: int

    team_id: Optional[int] = None
    user_id: Optional[int] = None
    manual_participant_id: Optional[int] = None

class TournamentParticipantBase(BaseModel):
    tournament_id: int = Field(..., gt=0)

    # apenas UM destes deve ser usado
    team_id: Optional[int] = Field(None, gt=0)
    user_id: Optional[int] = Field(None, gt=0)
    manual_participant_id: Optional[int] = Field(None, gt=0)


class JoinTournamentRequest(BaseModel):
    tournament_id: int
    team_id: Optional[int] = None
    user_id: Optional[int] = None
    manual_participant_id: Optional[int] = None

class JoinTournamentRequest(TournamentParticipantBase):
    password: Optional[str] = None


class LeaveTournamentRequest(TournamentParticipantBase):
    pass

class TournamentParticipantResponse(TournamentParticipantBase):
    id: int

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# ==========================
# REQUEST
# ==========================

class RequestResponse(BaseModel):
    id: int
    teams_id: Optional[int] = None
    participants_id: Optional[int] = None

    model_config = {
        "from_attributes": True
    }


class InviteResponse(BaseModel):
    id: int
    teams_id: Optional[int] = None
    participants_id: Optional[int] = None

    model_config = {
        "from_attributes": True
    }


# ==========================
# MATCH SCHEMA
# ==========================

class MatchBase(BaseModel):
    id: int
    tournament_id: int
    participant_type: ParticipantEnum

    participant1_id: Optional[int] = None
    participant2_id: Optional[int] = None

    winner_id: Optional[int] = None

    date: Optional[date] = None
    time: Optional[time] = None

    model_config = ConfigDict(from_attributes=True)


class MatchResponse(BaseModel):
    id: int
    date: Optional[date] = None
    time: Optional[time] = None

    model_config = ConfigDict(from_attributes=True)

class ReportWinnerRequest(BaseModel):
    match_id: int
    winner: int