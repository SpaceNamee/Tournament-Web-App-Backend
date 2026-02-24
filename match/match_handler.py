from typing import List, Optional
import math
import random
from datetime import date, time
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Tournament, TournamentParticipant, Match
from schemas import ParticipantEnum


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_participants(db: Session, tournament_id: int) -> List[dict]:
    """
    Returns participants as:
         { "type": "team" | "solo", "id": <id> }
    Reads TournamentParticipant table.
    """
    rows = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()

    parts = []
    for r in rows:
        if getattr(r, "team_id", None):
            parts.append({"type": "team", "id": r.team_id})
        elif getattr(r, "user_id", None):
            parts.append({"type": "solo", "id": r.user_id})
    return parts


def create_match_record(
    db: Session,
    tournament: Tournament,
    participant_type: str,
    part1_id: Optional[int],
    part2_id: Optional[int],
    match_date: Optional[date] = None,
    match_time: Optional[time] = None
) -> Match:
    m = Match(
        tournament_id=tournament.id,
        participant_type=participant_type,
        participant1_id=part1_id,
        participant2_id=part2_id,
        date=match_date,
        time=match_time
    )
    db.add(m)
    db.flush()
    return m



def next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 2 ** math.ceil(math.log2(n))


# ------------------------------------------------------------------
# Generators
# ------------------------------------------------------------------
def generate_single_elimination(
    db: Session,
    tournament: Tournament,
    participants: List[dict],
) -> List[Match]:

    ptype = (
        "team"
        if tournament.participant_type == ParticipantEnum.team.value
        else "solo"
    )

    ids = [p["id"] for p in participants if p["type"] == ptype]

    if len(ids) < 2:
        raise HTTPException(400, "Not enough participants")

    random.shuffle(ids)

    def next_power_of_two_single(n: int) -> int:
        return 1 << (n - 1).bit_length()

    target = next_power_of_two_single(len(ids))
    ids.extend([None] * (target - len(ids)))

    all_matches: List[Match] = []

    # -----------------------------
    # ROUND 1
    # -----------------------------
    round_matches: List[Match] = []

    for i in range(0, len(ids), 2):
        p1, p2 = ids[i], ids[i + 1]

        if p1 is None and p2 is None:
            continue

        m = create_match_record(
            db=db,
            tournament=tournament,
            participant_type=ptype,
            part1_id=p1,
            part2_id=p2,
        )

        round_matches.append(m)
        all_matches.append(m)

    # -----------------------------
    # NEXT ROUNDS
    # -----------------------------
    while len(round_matches) > 1:
        next_round: List[Match] = []
        i = 0

        while i < len(round_matches):
            if i + 1 < len(round_matches):
                parent = create_match_record(
                    db=db,
                    tournament=tournament,
                    participant_type=ptype,
                    part1_id=None,
                    part2_id=None,
                )

                m1 = round_matches[i]
                m2 = round_matches[i + 1]

                m1.winner_to_match_id = parent.id
                m1.winner_to_slot = 1

                m2.winner_to_match_id = parent.id
                m2.winner_to_slot = 2

                next_round.append(parent)
                all_matches.append(parent)
                i += 2
            else:
                next_round.append(round_matches[i])
                i += 1

        round_matches = next_round

    return all_matches


def generate_round_robin(
    db: Session,
    tournament: Tournament,
    participants: List[dict],
) -> List[Match]:

    ptype = (
        "team"
        if tournament.participant_type == ParticipantEnum.team.value
        else "solo"
    )

    ids = [p["id"] for p in participants if p["type"] == ptype]

    if len(ids) < 2:
        raise HTTPException(400, "Not enough participants")

    random.shuffle(ids)

    all_matches: List[Match] = []

    n = len(ids)

    for i in range(n):
        for j in range(i + 1, n):
            m = create_match_record(
                db=db,
                tournament=tournament,
                participant_type=ptype,
                part1_id=ids[i],
                part2_id=ids[j],
            )
            all_matches.append(m)

    return all_matches



def generate_double_elimination(
    db: Session,
    tournament: Tournament,
    participants: List[dict]
) -> List[Match]:

    ptype = "team" if tournament.participant_type == ParticipantEnum.team.value else "solo"
    ids = [p["id"] for p in participants if p["type"] == ptype]

    if len(ids) < 2:
        raise HTTPException(400, "Not enough participants")

    random.shuffle(ids)

    size = next_power_of_two(len(ids))
    ids.extend([None] * (size - len(ids)))

    all_matches: List[Match] = []

    # ======================
    # WINNERS BRACKET
    # ======================
    winners_rounds: List[List[Match]] = []

    # Round 1
    round1 = []
    for i in range(0, size, 2):
        m = create_match_record(db, tournament, ptype, ids[i], ids[i + 1])
        round1.append(m)
        all_matches.append(m)

    winners_rounds.append(round1)

    # Next rounds
    while len(winners_rounds[-1]) > 1:
        prev = winners_rounds[-1]
        curr = []

        for i in range(0, len(prev), 2):
            m = create_match_record(db, tournament, ptype, None, None)

            prev[i].winner_to_match_id = m.id
            prev[i].winner_to_slot = 1

            prev[i + 1].winner_to_match_id = m.id
            prev[i + 1].winner_to_slot = 2

            curr.append(m)
            all_matches.append(m)

        winners_rounds.append(curr)

    wb_final = winners_rounds[-1][0]

    # ======================
    # LOSERS BRACKET
    # ======================
    losers_rounds: List[List[Match]] = []

    # LB Round 1 (losers from WB R1)
    lb_round1 = []
    wb_r1 = winners_rounds[0]

    for i in range(0, len(wb_r1), 2):
        m = create_match_record(db, tournament, ptype, None, None)

        wb_r1[i].loser_to_match_id = m.id
        wb_r1[i].loser_to_slot = 1

        wb_r1[i + 1].loser_to_match_id = m.id
        wb_r1[i + 1].loser_to_slot = 2

        lb_round1.append(m)
        all_matches.append(m)

    losers_rounds.append(lb_round1)

    # LB subsequent rounds
    for r in range(1, len(winners_rounds) - 1):
        prev_lb = losers_rounds[-1]
        wb_round = winners_rounds[r]

        curr_lb = []

        for i in range(len(wb_round)):
            m = create_match_record(db, tournament, ptype, None, None)

            prev_lb[i].winner_to_match_id = m.id
            prev_lb[i].winner_to_slot = 1

            wb_round[i].loser_to_match_id = m.id
            wb_round[i].loser_to_slot = 2

            curr_lb.append(m)
            all_matches.append(m)

        losers_rounds.append(curr_lb)

    lb_final = losers_rounds[-1][0]

    # ======================
    # GRAND FINAL
    # ======================
    grand_final = create_match_record(db, tournament, ptype, None, None)

    wb_final.winner_to_match_id = grand_final.id
    wb_final.winner_to_slot = 1

    lb_final.winner_to_match_id = grand_final.id
    lb_final.winner_to_slot = 2

    all_matches.append(grand_final)

    return all_matches


def report_match_winner(
    db: Session,
    match: Match,
    winner_id: int
):
    match.winner_id = winner_id

    # winner goes forward
    if match.winner_to_match_id:
        next_match = db.get(Match, match.winner_to_match_id)
        if match.winner_to_slot == 1:
            next_match.participant1_id = winner_id
        else:
            next_match.participant2_id = winner_id

    # loser goes forward (double elimination)
    loser_id = (
        match.participant2_id
        if winner_id == match.participant1_id
        else match.participant1_id
    )

    if match.loser_to_match_id and loser_id is not None:
        loser_match = db.get(Match, match.loser_to_match_id)
        if match.loser_to_slot == 1:
            loser_match.participant1_id = loser_id
        else:
            loser_match.participant2_id = loser_id



def get_all_matches(
    db: Session,
    tournament_id: int,
):
    matches = db.query(Match).filter(Match.tournament_id == tournament_id).all()
    return matches
