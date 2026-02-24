import enum
from datetime import datetime, time , timezone
from enum import unique
from sqlalchemy import func, and_
from sqlalchemy import (
    Column, Integer, String, Enum, Date, Time, Boolean, ForeignKey,
    DateTime, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base
Base = declarative_base()

# ===================== ENUMS =====================

class VisibilityEnum(str, enum.Enum):
    visible = "visible"
    invisible = "invisible"

class SportEnum(str, enum.Enum):
    football = "football"
    basketball = "basketball"
    tennis = "tennis"

class ParticipantEnum(str, enum.Enum):
    team = "team"
    solo = "solo"

class TournamentTypeEnum(str, enum.Enum):
    singleElimination = "Single Elimination"
    group = "Group"
    doubleElimination = "Double Elimination"

class TournamentTimeFilter(str, enum.Enum):
    tomorrow = "tomorrow"
    next_week = "next_week"
    next_2_week = "next_2_weeks"
    next_month = "next_month"
    upcoming = "upcoming"

class SortEnum(str, enum.Enum):
    asc = 'asc'
    desc = 'desc'

# ===================== USER =====================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    nickname = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    # age = Column(Integer, nullable=True) 
    phone_number = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True) # calculate the age only when needed

    tournament_notif = Column(Boolean, default=True)
    match_notif = Column(Boolean, default=True)
    general_notif = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    # relationships
    tournaments_created = relationship("Tournament",
                    primaryjoin="and_(Tournament.created_by == User.id, Tournament.deleted_at.is_(None))",
                    back_populates="organizer")
    team_created = relationship("Team",
                                primaryjoin="and_(Team.created_by == User.id, Team.deleted_at.is_(None))",
                                back_populates="organizer")
    team_memberships = relationship("TeamMember",
                                    primaryjoin="and_(TeamMember.user_id == User.id, TeamMember.deleted_at.is_(None))",
                                    back_populates="user")
    tournament_participations = relationship("TournamentParticipant",
                                             primaryjoin="and_(TournamentParticipant.user_id == User.id, TournamentParticipant.deleted_at.is_(None))",
                                             back_populates="user")
    manual_participants = relationship("ManualParticipant",
                                       primaryjoin="and_(ManualParticipant.created_by == User.id, ManualParticipant.deleted_at.is_(None))",
                                       back_populates="creator")

    __table_args__ = (
        # For user search by name (case-insensitive)
        Index('ix_user_name_lower', func.lower(name)),

        # For finding verified users (admin panels, user lists)
        Index('ix_user_verified', 'is_verified', 'created_at'),

        # For admin queries
        Index('ix_user_admin', 'is_admin'),

        # For finding users by age range (tournaments with min_age)
        Index('ix_user_dob', 'date_of_birth'),

        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=Column("deleted_at").is_(None),
        ),
        Index(
            "uq_users_nickname_active",
            "nickname",
            unique=True,
            postgresql_where=Column("deleted_at").is_(None),
        ),
    )

# ===================== MANUAL PARTICIPANT =====================
class ManualParticipant(Base):
    __tablename__ = "manual_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_manual_participant_name", "name", "created_by", unique=True, postgresql_where=Column("deleted_at").is_(None)),
        # Index("ix_manual_participant_origanizer", created_by)
    )

    # relationships
    creator = relationship("User", back_populates="manual_participants")
    tournament_participations = relationship("TournamentParticipant", back_populates="manual_participant")

# ===================== TOURNAMENT =====================
class Tournament(Base):
    __tablename__ = "tournaments"
    id = Column(Integer, primary_key=True)#, autoincrement=True)
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),        # default = RESTRICT
        nullable=False,
        index=True
    )
    # soft delete approach allow us to set nullable attr to False

    organizer_contact = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False, index=True)
    sport = Column(Enum(SportEnum), nullable=False)
    bracket_type = Column(Enum(TournamentTypeEnum), nullable=False)
    visibility = Column(Enum(VisibilityEnum), nullable=False)
    hashed_password = Column(String(255), nullable=True)

    participant_type = Column(Enum(ParticipantEnum), nullable=False)
    team_tournament = relationship("TournamentParticipant", back_populates="tournament")

    min_age = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)

    location = Column(String(100), nullable=False)

    rules = Column(String(1000), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    # relationship
    organizer = relationship("User",
                             primaryjoin="and_(Tournament.created_by == User.id, User.deleted_at.is_(None))",
                             back_populates="tournaments_created")
    matches = relationship("Match", back_populates="tournament")
    team_tournament = relationship("TeamTournament", uselist=False, cascade="all, delete-orphan", back_populates="tournament")
    solo_tournament = relationship("SoloTournament", uselist=False, cascade="all, delete-orphan", back_populates="tournament")
    participants = relationship("TournamentParticipant",
                                primaryjoin="and_(TournamentParticipant.tournament_id == Tournament.id, TournamentParticipant.deleted_at.is_(None))",
                                back_populates="tournament")

    __table_args__ = (
        # Most common: "Find upcoming football tournaments in Stryi"
        Index('ix_tournament_search', 'sport', 'location', 'start_date', postgresql_where=(Column('deleted_at').is_(None))),

        # For: "Upcoming tournaments" / "Browse by date"
        Index('ix_tournament_upcoming', 'start_date', 'visibility', postgresql_where=(Column('deleted_at').is_(None))),

        # For: "Find tournaments in Ukraine > Lviv > Stryi"
        Index('ix_tournament_location', 'location', postgresql_where=(Column('deleted_at').is_(None))),

        # For: "Team tournaments vs Solo tournaments by sport"
        Index('ix_tournament_type_sport', 'participant_type', 'sport', postgresql_where=(Column('deleted_at').is_(None))),

        # For: "Active tournaments" (exclude soft-deleted)
        Index(
            'ix_tournament_active',
            'sport',
            'start_date',
            postgresql_where=(Column('deleted_at').is_(None))
        ),

        # Optional: For date range queries "tournaments this month"
        # Index('ix_tournament_date_range', 'start_date', 'end_date'),
    )

# ===================== TEAM TOURNAMENT =====================
class TeamTournament(Base):
    __tablename__ = "team_tournaments"

    tournament_id = Column(
        ForeignKey("tournaments.id", ondelete="RESTRICT"),
        nullable=False,
        primary_key=True
    )
    max_teams = Column(Integer, nullable=False)
    current_teams = Column(Integer, default=0, nullable=False)
    players_per_team = Column(Integer, nullable=False)

    tournament = relationship("Tournament", back_populates="team_tournament")

# ===================== SOLO TOURNAMENT =====================
class SoloTournament(Base):
    __tablename__ = "solo_tournaments"

    tournament_id = Column(
        ForeignKey("tournaments.id", ondelete="RESTRICT"),
        nullable=False,
        primary_key=True
    )
    max_players = Column(Integer, nullable=False)
    current_players = Column(Integer, default=0, nullable=False)

    tournament = relationship("Tournament", back_populates="solo_tournament")

# ===================== TEAMS =====================
class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    name = Column(String(100), nullable=False, index=True)
    sport = Column(Enum(SportEnum), nullable=False)
    visibility = Column(Enum(VisibilityEnum), nullable=False)
    hashed_password = Column(String(255), nullable=True)

    max_players = Column(Integer, nullable=False)
    current_players = Column(Integer, default=0)  

    location = Column(String(100), nullable=False)
    min_age = Column(Integer)
    rules = Column(String(1000), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    members = relationship(
        "TeamMember",
        primaryjoin="and_(TeamMember.team_id == Team.id, TeamMember.deleted_at.is_(None))",
        back_populates="team"
    )
    organizer = relationship(
        "User",
        primaryjoin="and_(Team.created_by == User.id, User.deleted_at.is_(None))",
        back_populates="team_created"
    )
    tournament_participations = relationship(
        "TournamentParticipant",
        primaryjoin="and_(TournamentParticipant.team_id == Team.id, TournamentParticipant.deleted_at.is_(None))",
        back_populates="team"
    )

    __table_args__ = (
        Index('ix_team_search', 'sport', 'visibility', 'location'),
        Index('ix_team_location', 'location'),
        Index('ix_team_has_space', 'sport', 'location',
              postgresql_where=(current_players < max_players)),
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, autoincrement=True)

    team_id = Column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    team = relationship("Team",
                        primaryjoin="and_(TeamMember.team_id == Team.id, Team.deleted_at.is_(None))",
                        back_populates="members")
    user = relationship("User",
                        primaryjoin="and_(TeamMember.user_id == User.id, User.deleted_at.is_(None))",
                        back_populates="team_memberships")

    __table_args__ = (
        # Enforce ONE active membership
        Index(
            "uq_active_team_user",
            "team_id",
            "user_id",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
    )

# ===================== TOURNAMENT PARTICIPANT =====================
class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(
        Integer,
        ForeignKey("tournaments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    manual_participant_id = Column(Integer, ForeignKey("manual_participants.id"),nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    # relationships
    user = relationship("User",
                        primaryjoin="and_(TournamentParticipant.user_id == User.id, User.deleted_at.is_(None))",
                        back_populates="tournament_participations")
    team = relationship("Team",
                        primaryjoin="and_(TournamentParticipant.team_id == Team.id, Team.deleted_at.is_(None))",
                        back_populates="tournament_participations")
    manual_participant = relationship("ManualParticipant",
                                      primaryjoin="and_(TournamentParticipant.manual_participant_id == ManualParticipant.id, ManualParticipant.deleted_at.is_(None))",
                                      back_populates="tournament_participations")
    tournament = relationship("Tournament",
                              primaryjoin="and_(TournamentParticipant.tournament_id == Tournament.id, Tournament.deleted_at.is_(None))",
                              back_populates="participants")
    __table_args__ = (
        # Exactly ONE participant reference must be present
        CheckConstraint(
            """
            (
                (user_id IS NOT NULL)::int +
                (team_id IS NOT NULL)::int +
                (manual_participant_id IS NOT NULL)::int
            ) = 1
            """,
            name="ck_exactly_one_participant"
        ),

        Index(
            "idx_tp_tournament_user",
            "tournament_id",
            "user_id",
            unique=True,
            postgresql_where=and_(user_id.isnot(None), deleted_at.is_(None)),
        ),
        Index(
            "idx_tp_tournament_team",
            "tournament_id",
            "team_id",
            unique=True,
            postgresql_where=and_(team_id.isnot(None), deleted_at.is_(None))
        ),
        Index(
            "idx_tp_tournament_manual",
            "tournament_id",
            "manual_participant_id",
            unique=True,
            postgresql_where=and_(user_id.isnot(None),  deleted_at.is_(None)),
        ),
    )

# Snapshot table
class TournamentTeamMember(Base):
    __tablename__ = "tournament_team_members"

    id = Column(Integer, primary_key=True)
    tournament_id = Column(ForeignKey("tournaments.id"), nullable=False)
    team_id = Column(ForeignKey("teams.id"), nullable=False)

    user_id = Column(ForeignKey("users.id"), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class Request(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    teams_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

class Invite(Base):
    __tablename__ = "invites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    teams_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    participant_type = Column(String, nullable=False)
    participant1_id = Column(Integer, nullable=True)
    participant2_id = Column(Integer, nullable=True)
    winner_id = Column(Integer, nullable=True)
    winner_to_match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    winner_to_slot = Column(Integer, nullable=True)
    loser_to_match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    loser_to_slot = Column(Integer, nullable=True)
    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)

    tournament = relationship("Tournament", back_populates="matches")

