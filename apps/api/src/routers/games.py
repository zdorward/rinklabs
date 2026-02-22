# apps/api/src/routers/games.py
from datetime import date, datetime, timezone, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.database import get_db
from src.models import Game, OddsSnapshot
from src.schemas import (
    GamesResponse,
    GameSummary,
    GameDetail,
    BestEdge,
    ConsensusInfo,
    BookOdds,
    MovementInfo,
)
from src.services import (
    american_to_implied_prob,
    remove_vig,
    calculate_consensus,
    calculate_edge_ev,
    calculate_disagreement,
    calculate_movement,
)

router = APIRouter()


def _get_latest_snapshots(db: Session, game_id: UUID) -> list[OddsSnapshot]:
    """Get most recent snapshot per bookmaker for a game."""
    from sqlalchemy import func

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


def _calculate_game_metrics(snapshots: list[OddsSnapshot]) -> dict:
    """Calculate consensus, edges, disagreement from snapshots."""
    if not snapshots:
        return {
            "consensus_home": 0.5,
            "consensus_away": 0.5,
            "best_edge": None,
            "disagreement": 0.0,
            "book_odds": [],
        }

    home_probs = []
    book_odds = []

    for snap in snapshots:
        home_implied = american_to_implied_prob(snap.home_price)
        away_implied = american_to_implied_prob(snap.away_price)
        home_fair, away_fair = remove_vig(home_implied, away_implied)
        home_probs.append(home_fair)
        book_odds.append(
            {
                "bookmaker": snap.bookmaker,
                "home_price": snap.home_price,
                "away_price": snap.away_price,
                "home_fair": home_fair,
                "away_fair": away_fair,
                "last_updated": snap.snapshot_time,
            }
        )

    consensus_home = calculate_consensus(home_probs)
    consensus_away = 1 - consensus_home

    best_edge = None
    best_ev = 0.0

    for i, odds in enumerate(book_odds):
        home_edge = calculate_edge_ev(odds["home_fair"], consensus_home)
        away_edge = calculate_edge_ev(odds["away_fair"], consensus_away)
        odds["home_edge"] = home_edge
        odds["away_edge"] = away_edge

        if home_edge > best_ev:
            best_ev = home_edge
            best_edge = {
                "side": "home",
                "bookmaker": odds["bookmaker"],
                "ev_pct": home_edge,
            }
        if away_edge > best_ev:
            best_ev = away_edge
            best_edge = {
                "side": "away",
                "bookmaker": odds["bookmaker"],
                "ev_pct": away_edge,
            }

    disagreement = calculate_disagreement(home_probs, consensus_home)

    return {
        "consensus_home": consensus_home,
        "consensus_away": consensus_away,
        "best_edge": best_edge,
        "disagreement": disagreement,
        "book_odds": book_odds,
    }


@router.get("/games", response_model=GamesResponse)
async def get_games(
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
):
    """Get all games for a given date with summary metrics."""
    start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    games = (
        db.query(Game)
        .filter(Game.commence_time >= start, Game.commence_time < end)
        .order_by(Game.commence_time)
        .all()
    )

    summaries = []
    for game in games:
        snapshots = _get_latest_snapshots(db, game.id)
        metrics = _calculate_game_metrics(snapshots)

        summaries.append(
            GameSummary(
                id=game.id,
                home_team=game.home_team,
                away_team=game.away_team,
                commence_time=game.commence_time,
                consensus_home_prob=metrics["consensus_home"],
                consensus_away_prob=metrics["consensus_away"],
                best_edge=BestEdge(**metrics["best_edge"]) if metrics["best_edge"] else None,
                disagreement=metrics["disagreement"],
                books_count=len(snapshots),
            )
        )

    return GamesResponse(games=summaries)


@router.get("/games/{game_id}", response_model=GameDetail)
async def get_game(game_id: UUID, db: Session = Depends(get_db)):
    """Get detailed game info with odds from all books."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    snapshots = _get_latest_snapshots(db, game.id)
    metrics = _calculate_game_metrics(snapshots)

    opening_snapshot = (
        db.query(OddsSnapshot)
        .filter(OddsSnapshot.game_id == game_id, OddsSnapshot.is_opening == True)
        .first()
    )

    time_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    snapshot_24h = (
        db.query(OddsSnapshot)
        .filter(
            OddsSnapshot.game_id == game_id, OddsSnapshot.snapshot_time <= time_24h_ago
        )
        .order_by(OddsSnapshot.snapshot_time.desc())
        .first()
    )

    home_open = None
    change_from_open = None
    change_24h = None

    if opening_snapshot:
        open_home_implied = american_to_implied_prob(opening_snapshot.home_price)
        open_away_implied = american_to_implied_prob(opening_snapshot.away_price)
        home_open, _ = remove_vig(open_home_implied, open_away_implied)
        change_from_open = calculate_movement(metrics["consensus_home"], home_open)

    if snapshot_24h:
        h24_home_implied = american_to_implied_prob(snapshot_24h.home_price)
        h24_away_implied = american_to_implied_prob(snapshot_24h.away_price)
        home_24h, _ = remove_vig(h24_home_implied, h24_away_implied)
        change_24h = calculate_movement(metrics["consensus_home"], home_24h)

    book_odds = [
        BookOdds(
            bookmaker=o["bookmaker"],
            home_price=o["home_price"],
            away_price=o["away_price"],
            home_vig_free_prob=o["home_fair"],
            away_vig_free_prob=o["away_fair"],
            home_edge_ev=o["home_edge"],
            away_edge_ev=o["away_edge"],
            last_updated=o["last_updated"],
        )
        for o in metrics["book_odds"]
    ]

    return GameDetail(
        id=game.id,
        home_team=game.home_team,
        away_team=game.away_team,
        commence_time=game.commence_time,
        consensus=ConsensusInfo(
            home_prob=metrics["consensus_home"], away_prob=metrics["consensus_away"]
        ),
        odds_by_book=book_odds,
        movement=MovementInfo(
            home_open=home_open,
            home_current=metrics["consensus_home"],
            change_from_open=change_from_open,
            change_24h=change_24h,
        ),
        disagreement=metrics["disagreement"],
    )
