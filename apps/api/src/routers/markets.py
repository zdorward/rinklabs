# apps/api/src/routers/markets.py
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.database import get_db
from src.models import Game, OddsSnapshot
from src.schemas import (
    TopEdgesResponse,
    EdgeOpportunity,
    TopDisagreementsResponse,
    DisagreementInfo,
)
from src.services import (
    american_to_implied_prob,
    remove_vig,
    calculate_consensus,
    calculate_edge_ev,
    calculate_disagreement,
)

router = APIRouter()

FREE_LIMIT = 3


def _get_today_games(db: Session) -> list[Game]:
    """Get games for today and next 3 days."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=4)
    return (
        db.query(Game)
        .filter(Game.commence_time >= now, Game.commence_time < end)
        .order_by(Game.commence_time)
        .all()
    )


def _get_latest_snapshots_for_game(db: Session, game_id) -> list[OddsSnapshot]:
    """Get most recent snapshot per bookmaker for a game."""
    subq = (
        db.query(
            OddsSnapshot.bookmaker,
            func.max(OddsSnapshot.snapshot_time).label("max_time"),
        )
        .filter(OddsSnapshot.game_id == game_id)
        .group_by(OddsSnapshot.bookmaker)
        .subquery()
    )

    return (
        db.query(OddsSnapshot)
        .join(
            subq,
            and_(
                OddsSnapshot.bookmaker == subq.c.bookmaker,
                OddsSnapshot.snapshot_time == subq.c.max_time,
            ),
        )
        .filter(OddsSnapshot.game_id == game_id)
        .all()
    )


@router.get("/markets/today/top-edges", response_model=TopEdgesResponse)
async def get_top_edges(
    limit: int = Query(default=FREE_LIMIT, le=100),
    db: Session = Depends(get_db),
    is_pro: bool = False,
):
    """Get top edge opportunities across today's games."""
    effective_limit = limit if is_pro else FREE_LIMIT
    games = _get_today_games(db)

    all_edges = []

    for game in games:
        snapshots = _get_latest_snapshots_for_game(db, game.id)
        if not snapshots:
            continue

        home_probs = []
        for snap in snapshots:
            home_implied = american_to_implied_prob(snap.home_price)
            away_implied = american_to_implied_prob(snap.away_price)
            home_fair, _ = remove_vig(home_implied, away_implied)
            home_probs.append(home_fair)

        consensus_home = calculate_consensus(home_probs)
        consensus_away = 1 - consensus_home

        for snap in snapshots:
            home_implied = american_to_implied_prob(snap.home_price)
            away_implied = american_to_implied_prob(snap.away_price)
            home_fair, away_fair = remove_vig(home_implied, away_implied)

            home_edge = calculate_edge_ev(home_fair, consensus_home)
            away_edge = calculate_edge_ev(away_fair, consensus_away)

            if home_edge > 0:
                all_edges.append(
                    EdgeOpportunity(
                        game_id=game.id,
                        home_team=game.home_team,
                        away_team=game.away_team,
                        commence_time=game.commence_time,
                        side="home",
                        bookmaker=snap.bookmaker,
                        ev_pct=round(home_edge, 2),
                        book_price=snap.home_price,
                        consensus_prob=round(consensus_home, 4),
                    )
                )

            if away_edge > 0:
                all_edges.append(
                    EdgeOpportunity(
                        game_id=game.id,
                        home_team=game.home_team,
                        away_team=game.away_team,
                        commence_time=game.commence_time,
                        side="away",
                        bookmaker=snap.bookmaker,
                        ev_pct=round(away_edge, 2),
                        book_price=snap.away_price,
                        consensus_prob=round(consensus_away, 4),
                    )
                )

    all_edges.sort(key=lambda x: x.ev_pct, reverse=True)
    total_count = len(all_edges)
    truncated = total_count > effective_limit

    return TopEdgesResponse(
        edges=all_edges[:effective_limit],
        truncated=truncated,
        total_count=total_count,
    )


@router.get("/markets/today/top-disagreements", response_model=TopDisagreementsResponse)
async def get_top_disagreements(
    limit: int = Query(default=FREE_LIMIT, le=100),
    db: Session = Depends(get_db),
    is_pro: bool = False,
):
    """Get games with highest market disagreement."""
    effective_limit = limit if is_pro else FREE_LIMIT
    games = _get_today_games(db)

    all_disagreements = []

    for game in games:
        snapshots = _get_latest_snapshots_for_game(db, game.id)
        if len(snapshots) < 2:
            continue

        home_probs = []
        for snap in snapshots:
            home_implied = american_to_implied_prob(snap.home_price)
            away_implied = american_to_implied_prob(snap.away_price)
            home_fair, _ = remove_vig(home_implied, away_implied)
            home_probs.append(home_fair)

        consensus = calculate_consensus(home_probs)
        disagreement = calculate_disagreement(home_probs, consensus)

        all_disagreements.append(
            DisagreementInfo(
                game_id=game.id,
                home_team=game.home_team,
                away_team=game.away_team,
                commence_time=game.commence_time,
                disagreement_pct=round(disagreement, 2),
                range={"min_prob": round(min(home_probs), 4), "max_prob": round(max(home_probs), 4)},
            )
        )

    all_disagreements.sort(key=lambda x: x.disagreement_pct, reverse=True)
    total_count = len(all_disagreements)
    truncated = total_count > effective_limit

    return TopDisagreementsResponse(
        disagreements=all_disagreements[:effective_limit],
        truncated=truncated,
        total_count=total_count,
    )
