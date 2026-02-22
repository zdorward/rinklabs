# apps/api/src/providers/base.py
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel


class BookmakerOdds(BaseModel):
    key: str
    title: str
    home_price: int
    away_price: int


class GameOdds(BaseModel):
    external_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmakers: list[BookmakerOdds]


class OddsProvider(ABC):
    @abstractmethod
    async def fetch_nhl_odds(self) -> list[GameOdds]:
        """Fetch NHL moneyline odds for upcoming games."""
        pass
