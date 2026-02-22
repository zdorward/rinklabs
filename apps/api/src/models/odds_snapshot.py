import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)
    home_price: Mapped[int] = mapped_column(Integer, nullable=False)
    away_price: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_opening: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    game: Mapped["Game"] = relationship(back_populates="odds_snapshots")

    __table_args__ = (
        Index("ix_odds_snapshots_game_book_time", "game_id", "bookmaker", "snapshot_time"),
        Index("ix_odds_snapshots_snapshot_time", "snapshot_time"),
    )
