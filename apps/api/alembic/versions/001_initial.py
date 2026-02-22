"""initial

Revision ID: 001
Revises:
Create Date: 2026-02-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("home_team", sa.String(100), nullable=False),
        sa.Column("away_team", sa.String(100), nullable=False),
        sa.Column("commence_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("bookmaker", sa.String(50), nullable=False),
        sa.Column("home_price", sa.Integer(), nullable=False),
        sa.Column("away_price", sa.Integer(), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_opening", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_odds_snapshots_game_book_time",
        "odds_snapshots",
        ["game_id", "bookmaker", "snapshot_time"],
    )
    op.create_index(
        "ix_odds_snapshots_snapshot_time", "odds_snapshots", ["snapshot_time"]
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clerk_id", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("subscription_status", sa.String(20), nullable=False),
        sa.Column("subscription_id", sa.String(100), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_id"),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_index("ix_odds_snapshots_snapshot_time", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_game_book_time", table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_table("games")
