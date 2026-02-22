# apps/api/src/services/ingestion.py
import logging
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.models import Game, OddsSnapshot
from src.providers.base import OddsProvider, GameOdds

logger = logging.getLogger(__name__)


class IngestResult(BaseModel):
    games_processed: int
    snapshots_created: int


class OddsIngestionService:
    def __init__(self, provider: OddsProvider, db: Session):
        self.provider = provider
        self.db = db

    async def ingest(self) -> IngestResult:
        """
        Fetch odds and store snapshots.
        1. Fetch odds from provider
        2. Upsert games
        3. Create odds snapshots
        """
        games_data = await self.provider.fetch_nhl_odds()
        snapshots_created = 0

        for game_data in games_data:
            game = self._upsert_game(game_data)

            for book in game_data.bookmakers:
                is_opening = not self._has_prior_snapshot(game.id, book.key)
                self._create_snapshot(
                    game_id=game.id,
                    bookmaker=book.key,
                    home_price=book.home_price,
                    away_price=book.away_price,
                    is_opening=is_opening,
                )
                snapshots_created += 1

        self.db.commit()
        logger.info(
            f"Ingestion complete: {len(games_data)} games, {snapshots_created} snapshots"
        )

        return IngestResult(
            games_processed=len(games_data), snapshots_created=snapshots_created
        )

    def _upsert_game(self, game_data: GameOdds) -> Game:
        """Get existing game or create new one."""
        game = (
            self.db.query(Game)
            .filter(Game.external_id == game_data.external_id)
            .first()
        )

        if game:
            game.commence_time = game_data.commence_time
            game.updated_at = datetime.now(timezone.utc)
        else:
            game = Game(
                external_id=game_data.external_id,
                home_team=game_data.home_team,
                away_team=game_data.away_team,
                commence_time=game_data.commence_time,
            )
            self.db.add(game)
            self.db.flush()

        return game

    def _has_prior_snapshot(self, game_id: UUID, bookmaker: str) -> bool:
        """Check if we have any prior snapshot for this game/book combo."""
        return (
            self.db.query(OddsSnapshot)
            .filter(OddsSnapshot.game_id == game_id, OddsSnapshot.bookmaker == bookmaker)
            .first()
            is not None
        )

    def _create_snapshot(
        self,
        game_id: UUID,
        bookmaker: str,
        home_price: int,
        away_price: int,
        is_opening: bool,
    ) -> OddsSnapshot:
        """Create a new odds snapshot."""
        snapshot = OddsSnapshot(
            game_id=game_id,
            bookmaker=bookmaker,
            home_price=home_price,
            away_price=away_price,
            snapshot_time=datetime.now(timezone.utc),
            is_opening=is_opening,
        )
        self.db.add(snapshot)
        return snapshot
