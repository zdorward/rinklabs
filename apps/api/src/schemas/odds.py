# apps/api/src/schemas/odds.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class SnapshotBook(BaseModel):
    bookmaker: str
    home_price: int
    away_price: int


class OddsSnapshot(BaseModel):
    timestamp: datetime
    books: list[SnapshotBook]
    consensus_home_prob: float


class OddsHistoryResponse(BaseModel):
    game_id: UUID
    snapshots: list[OddsSnapshot]


class EdgeOpportunity(BaseModel):
    game_id: UUID
    home_team: str
    away_team: str
    commence_time: datetime
    side: str
    bookmaker: str
    ev_pct: float
    book_price: int
    consensus_prob: float


class TopEdgesResponse(BaseModel):
    edges: list[EdgeOpportunity]
    truncated: bool
    total_count: int


class DisagreementInfo(BaseModel):
    game_id: UUID
    home_team: str
    away_team: str
    commence_time: datetime
    disagreement_pct: float
    range: dict  # {"min_prob": float, "max_prob": float}


class TopDisagreementsResponse(BaseModel):
    disagreements: list[DisagreementInfo]
    truncated: bool
    total_count: int
