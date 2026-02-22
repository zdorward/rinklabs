# apps/api/src/schemas/game.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class BestEdge(BaseModel):
    side: str  # "home" or "away"
    bookmaker: str
    ev_pct: float


class GameSummary(BaseModel):
    id: UUID
    home_team: str
    away_team: str
    commence_time: datetime
    consensus_home_prob: float
    consensus_away_prob: float
    best_edge: BestEdge | None
    disagreement: float
    books_count: int


class GamesResponse(BaseModel):
    games: list[GameSummary]


class ConsensusInfo(BaseModel):
    home_prob: float
    away_prob: float


class BookOdds(BaseModel):
    bookmaker: str
    home_price: int
    away_price: int
    home_vig_free_prob: float
    away_vig_free_prob: float
    home_edge_ev: float
    away_edge_ev: float
    last_updated: datetime


class MovementInfo(BaseModel):
    home_open: float | None
    home_current: float
    change_from_open: float | None
    change_24h: float | None


class GameDetail(BaseModel):
    id: UUID
    home_team: str
    away_team: str
    commence_time: datetime
    consensus: ConsensusInfo
    odds_by_book: list[BookOdds]
    movement: MovementInfo
    disagreement: float
