from typing import Optional, List
from datetime import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from models import Tournament, Match
from schemas import TournamentTypeEnum, ParticipantEnum, MatchResponse, ReportWinnerRequest
from match.match_handler import get_participants, generate_single_elimination, \
    generate_double_elimination, get_all_matches, report_match_winner, generate_round_robin

bracket_router = APIRouter(prefix="", tags=["Matches"])


@bracket_router.post("/{tournament_id}/generate-matches")
def generate_matches_route(
    tournament_id: int,
    format1: Optional[str] = None,
    db: Session = Depends(get_db)
):
    tournament = (
        db.query(Tournament)
        .filter(Tournament.id == tournament_id)
        .first()
    )
    if not tournament:
        raise HTTPException(404, "Tournament not found")

    bracket_type = format1 or tournament.bracket_type
    participants = get_participants(db, tournament_id)

    if not participants:
        raise HTTPException(400, "No participants registered")

    if bracket_type == TournamentTypeEnum.singleElimination.value:
        created = generate_single_elimination(
            db=db,
            tournament=tournament,
            participants=participants
        )

    elif bracket_type == TournamentTypeEnum.doubleElimination.value:
        created = generate_double_elimination(
            db=db,
            tournament=tournament,
            participants=participants
        )

    elif bracket_type == TournamentTypeEnum.group.value:
        created = generate_round_robin(
            db=db,
            tournament=tournament,
            participants=participants
        )

    else:
        raise HTTPException(400, "Unknown bracket type")

    db.commit()

    for m in created:
        db.refresh(m)

    return {
        "created": len(created),
        "match_ids": [m.id for m in created]
    }


@bracket_router.get("/all/{tournament_id}", response_model=List[MatchResponse])
def get_matches_route(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(404, "Tournament not found")

    matches = get_all_matches(db, tournament_id)

    if not matches:
        raise HTTPException(404, "No matches not found")
    return matches


@bracket_router.put("/report_winner", response_model=MatchResponse)
def report_winner_route(payload: ReportWinnerRequest, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == payload.match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")

    if payload.winner == 1:
        winner_id = match.participant1_id
    elif payload.winner == 2:
        winner_id = match.participant2_id
    else:
        raise HTTPException(400, "Invalid winner")

    report_match_winner(db, match, winner_id)
    db.commit()
    return match
