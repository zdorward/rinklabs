# Hockey Market Intelligence MVP - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-ready hockey betting market intelligence MVP with odds aggregation, edge calculation, and Stripe subscriptions.

**Architecture:** Monorepo with FastAPI backend (APScheduler in-process) and Next.js frontend. Postgres for storage. Clerk for auth. Stripe for payments.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, APScheduler, Next.js 14, TypeScript, Tailwind, Clerk, Stripe, PostgreSQL, Docker

---

## Phase 1: Project Scaffolding

### Task 1.1: Root Configuration Files

**Files:**
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: rinklabs
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Step 2: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
.next/
out/

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Testing
.coverage
htmlcov/
.pytest_cache/

# Logs
*.log
```

**Step 3: Create README.md**

```markdown
# Rinklabs - Hockey Market Intelligence

Market intelligence for NHL betting. Aggregates odds, calculates consensus probabilities, identifies edges.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### Setup

1. Start database:
   ```bash
   docker-compose up -d
   ```

2. Backend:
   ```bash
   cd apps/api
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   alembic upgrade head
   uvicorn src.main:app --reload --port 8000
   ```

3. Frontend:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

## Environment Variables

See `apps/api/.env.example` and `apps/web/.env.example`
```

**Step 4: Commit**

```bash
git add docker-compose.yml .gitignore README.md
git commit -m "chore: add root config files"
```

---

### Task 1.2: Backend Project Structure

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/.env.example`
- Create: `apps/api/src/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p apps/api/src/{models,schemas,routers,services,providers,scheduler,auth}
mkdir -p apps/api/tests
mkdir -p apps/api/scripts
```

**Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "rinklabs-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.25",
    "psycopg2-binary>=2.9.9",
    "alembic>=1.13.1",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "httpx>=0.26.0",
    "apscheduler>=3.10.4",
    "stripe>=7.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.4",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.3",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

**Step 3: Create .env.example**

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rinklabs

# Odds Provider
ODDS_API_KEY=your_odds_api_key_here

# Clerk
CLERK_SECRET_KEY=sk_test_xxxxx

# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PRO_PRICE_ID=price_xxxxx

# App
ENV=development
LOG_LEVEL=INFO
```

**Step 4: Create __init__.py files**

Create empty `__init__.py` in each directory:
- `apps/api/src/__init__.py`
- `apps/api/src/models/__init__.py`
- `apps/api/src/schemas/__init__.py`
- `apps/api/src/routers/__init__.py`
- `apps/api/src/services/__init__.py`
- `apps/api/src/providers/__init__.py`
- `apps/api/src/scheduler/__init__.py`
- `apps/api/src/auth/__init__.py`
- `apps/api/tests/__init__.py`

**Step 5: Commit**

```bash
git add apps/api/
git commit -m "chore: scaffold backend project structure"
```

---

### Task 1.3: Backend Config and Database Setup

**Files:**
- Create: `apps/api/src/config.py`
- Create: `apps/api/src/database.py`

**Step 1: Create config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/rinklabs"

    # Odds Provider
    odds_api_key: str = ""

    # Clerk
    clerk_secret_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""

    # App
    env: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 2: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 3: Commit**

```bash
git add apps/api/src/config.py apps/api/src/database.py
git commit -m "feat: add config and database setup"
```

---

## Phase 2: Database Models and Migrations

### Task 2.1: SQLAlchemy Models

**Files:**
- Create: `apps/api/src/models/game.py`
- Create: `apps/api/src/models/odds_snapshot.py`
- Create: `apps/api/src/models/user.py`
- Modify: `apps/api/src/models/__init__.py`

**Step 1: Create game.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship(back_populates="game")
```

**Step 2: Create odds_snapshot.py**

```python
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
```

**Step 3: Create user.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clerk_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    subscription_status: Mapped[str] = mapped_column(String(20), default="free")
    subscription_id: Mapped[str | None] = mapped_column(String(100))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**Step 4: Update models/__init__.py**

```python
from src.models.game import Game
from src.models.odds_snapshot import OddsSnapshot
from src.models.user import User

__all__ = ["Game", "OddsSnapshot", "User"]
```

**Step 5: Commit**

```bash
git add apps/api/src/models/
git commit -m "feat: add SQLAlchemy models for games, odds, users"
```

---

### Task 2.2: Alembic Setup and Initial Migration

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/001_initial.py`

**Step 1: Create alembic.ini**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/rinklabs

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

**Step 2: Create alembic directory and env.py**

```bash
mkdir -p apps/api/alembic/versions
```

```python
# apps/api/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Base
from src.models import Game, OddsSnapshot, User

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 3: Create initial migration**

```python
# apps/api/alembic/versions/001_initial.py
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
```

**Step 4: Create alembic script.py.mako**

```bash
mkdir -p apps/api/alembic
```

```python
# apps/api/alembic/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

**Step 5: Commit**

```bash
git add apps/api/alembic.ini apps/api/alembic/
git commit -m "feat: add Alembic migrations setup"
```

---

## Phase 3: Odds Calculator Service (TDD)

### Task 3.1: Test and Implement american_to_implied_prob

**Files:**
- Create: `apps/api/tests/test_odds_calculator.py`
- Create: `apps/api/src/services/odds_calculator.py`

**Step 1: Write the failing test**

```python
# apps/api/tests/test_odds_calculator.py
import pytest


class TestAmericanToImpliedProb:
    def test_negative_odds_favorite(self):
        from src.services.odds_calculator import american_to_implied_prob

        result = american_to_implied_prob(-150)
        assert result == pytest.approx(0.6, rel=0.01)

    def test_positive_odds_underdog(self):
        from src.services.odds_calculator import american_to_implied_prob

        result = american_to_implied_prob(130)
        assert result == pytest.approx(0.4348, rel=0.01)

    def test_even_odds(self):
        from src.services.odds_calculator import american_to_implied_prob

        result = american_to_implied_prob(100)
        assert result == pytest.approx(0.5)

    def test_heavy_favorite(self):
        from src.services.odds_calculator import american_to_implied_prob

        result = american_to_implied_prob(-300)
        assert result == pytest.approx(0.75)
```

**Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestAmericanToImpliedProb -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

```python
# apps/api/src/services/odds_calculator.py
def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)
```

**Step 4: Run test to verify it passes**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestAmericanToImpliedProb -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add apps/api/tests/test_odds_calculator.py apps/api/src/services/odds_calculator.py
git commit -m "feat: add american_to_implied_prob with tests"
```

---

### Task 3.2: Test and Implement remove_vig

**Files:**
- Modify: `apps/api/tests/test_odds_calculator.py`
- Modify: `apps/api/src/services/odds_calculator.py`

**Step 1: Write the failing test**

```python
# Add to apps/api/tests/test_odds_calculator.py

class TestRemoveVig:
    def test_typical_line(self):
        from src.services.odds_calculator import american_to_implied_prob, remove_vig

        home_prob = american_to_implied_prob(-150)
        away_prob = american_to_implied_prob(130)

        home_fair, away_fair = remove_vig(home_prob, away_prob)

        assert home_fair + away_fair == pytest.approx(1.0)
        assert home_fair == pytest.approx(0.58, rel=0.02)
        assert away_fair == pytest.approx(0.42, rel=0.02)

    def test_even_line(self):
        from src.services.odds_calculator import american_to_implied_prob, remove_vig

        home_prob = american_to_implied_prob(-110)
        away_prob = american_to_implied_prob(-110)

        home_fair, away_fair = remove_vig(home_prob, away_prob)

        assert home_fair == pytest.approx(0.5)
        assert away_fair == pytest.approx(0.5)
```

**Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestRemoveVig -v`
Expected: FAIL with "ImportError: cannot import name 'remove_vig'"

**Step 3: Write minimal implementation**

```python
# Add to apps/api/src/services/odds_calculator.py

def remove_vig(home_prob: float, away_prob: float) -> tuple[float, float]:
    """Remove vig by normalizing probabilities to sum to 1.0."""
    total = home_prob + away_prob
    return home_prob / total, away_prob / total
```

**Step 4: Run test to verify it passes**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestRemoveVig -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add apps/api/tests/test_odds_calculator.py apps/api/src/services/odds_calculator.py
git commit -m "feat: add remove_vig with tests"
```

---

### Task 3.3: Test and Implement calculate_consensus

**Files:**
- Modify: `apps/api/tests/test_odds_calculator.py`
- Modify: `apps/api/src/services/odds_calculator.py`

**Step 1: Write the failing test**

```python
# Add to apps/api/tests/test_odds_calculator.py

class TestCalculateConsensus:
    def test_median_odd_count(self):
        from src.services.odds_calculator import calculate_consensus

        probs = [0.55, 0.58, 0.60]
        assert calculate_consensus(probs) == pytest.approx(0.58)

    def test_median_even_count(self):
        from src.services.odds_calculator import calculate_consensus

        probs = [0.55, 0.57, 0.59, 0.60]
        assert calculate_consensus(probs) == pytest.approx(0.58)

    def test_single_book(self):
        from src.services.odds_calculator import calculate_consensus

        probs = [0.55]
        assert calculate_consensus(probs) == pytest.approx(0.55)

    def test_empty_list(self):
        from src.services.odds_calculator import calculate_consensus

        assert calculate_consensus([]) == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestCalculateConsensus -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# Add to apps/api/src/services/odds_calculator.py
import statistics


def calculate_consensus(vig_free_probs: list[float]) -> float:
    """Calculate median of vig-free probabilities across all books."""
    if not vig_free_probs:
        return 0.0
    return statistics.median(vig_free_probs)
```

**Step 4: Run test to verify it passes**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestCalculateConsensus -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add apps/api/tests/test_odds_calculator.py apps/api/src/services/odds_calculator.py
git commit -m "feat: add calculate_consensus with tests"
```

---

### Task 3.4: Test and Implement calculate_edge_ev

**Files:**
- Modify: `apps/api/tests/test_odds_calculator.py`
- Modify: `apps/api/src/services/odds_calculator.py`

**Step 1: Write the failing test**

```python
# Add to apps/api/tests/test_odds_calculator.py

class TestCalculateEdgeEV:
    def test_positive_edge(self):
        from src.services.odds_calculator import calculate_edge_ev

        # Consensus: 58%, Book implies: 52% -> book underestimates
        edge = calculate_edge_ev(book_vig_free_prob=0.52, consensus_prob=0.58)
        assert edge == pytest.approx(11.54, rel=0.01)

    def test_negative_edge(self):
        from src.services.odds_calculator import calculate_edge_ev

        # Consensus: 52%, Book implies: 58% -> book overestimates
        edge = calculate_edge_ev(book_vig_free_prob=0.58, consensus_prob=0.52)
        assert edge == pytest.approx(-10.34, rel=0.01)

    def test_no_edge(self):
        from src.services.odds_calculator import calculate_edge_ev

        edge = calculate_edge_ev(book_vig_free_prob=0.55, consensus_prob=0.55)
        assert edge == pytest.approx(0.0)

    def test_zero_book_prob(self):
        from src.services.odds_calculator import calculate_edge_ev

        edge = calculate_edge_ev(book_vig_free_prob=0.0, consensus_prob=0.55)
        assert edge == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestCalculateEdgeEV -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# Add to apps/api/src/services/odds_calculator.py

def calculate_edge_ev(book_vig_free_prob: float, consensus_prob: float) -> float:
    """
    Calculate Expected Value percentage.

    Positive EV% means the book is offering better odds than consensus
    (book underestimates probability = better payout for us).
    """
    if book_vig_free_prob == 0:
        return 0.0
    return ((consensus_prob - book_vig_free_prob) / book_vig_free_prob) * 100
```

**Step 4: Run test to verify it passes**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestCalculateEdgeEV -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add apps/api/tests/test_odds_calculator.py apps/api/src/services/odds_calculator.py
git commit -m "feat: add calculate_edge_ev with tests"
```

---

### Task 3.5: Test and Implement calculate_disagreement and calculate_movement

**Files:**
- Modify: `apps/api/tests/test_odds_calculator.py`
- Modify: `apps/api/src/services/odds_calculator.py`

**Step 1: Write the failing tests**

```python
# Add to apps/api/tests/test_odds_calculator.py

class TestCalculateDisagreement:
    def test_high_disagreement(self):
        from src.services.odds_calculator import calculate_disagreement

        probs = [0.50, 0.55, 0.60]
        disagreement = calculate_disagreement(probs, consensus=0.55)
        assert disagreement == pytest.approx(5.0)

    def test_low_disagreement(self):
        from src.services.odds_calculator import calculate_disagreement

        probs = [0.54, 0.55, 0.56]
        disagreement = calculate_disagreement(probs, consensus=0.55)
        assert disagreement == pytest.approx(1.0)

    def test_empty_list(self):
        from src.services.odds_calculator import calculate_disagreement

        assert calculate_disagreement([], consensus=0.55) == 0.0


class TestCalculateMovement:
    def test_line_moved_toward_home(self):
        from src.services.odds_calculator import calculate_movement

        movement = calculate_movement(current_prob=0.55, reference_prob=0.50)
        assert movement == pytest.approx(5.0)

    def test_line_moved_toward_away(self):
        from src.services.odds_calculator import calculate_movement

        movement = calculate_movement(current_prob=0.48, reference_prob=0.52)
        assert movement == pytest.approx(-4.0)

    def test_no_movement(self):
        from src.services.odds_calculator import calculate_movement

        movement = calculate_movement(current_prob=0.55, reference_prob=0.55)
        assert movement == pytest.approx(0.0)
```

**Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_odds_calculator.py::TestCalculateDisagreement tests/test_odds_calculator.py::TestCalculateMovement -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# Add to apps/api/src/services/odds_calculator.py

def calculate_disagreement(vig_free_probs: list[float], consensus: float) -> float:
    """
    Calculate maximum absolute deviation from consensus across all books.
    Returns deviation in percentage points.
    """
    if not vig_free_probs:
        return 0.0
    deviations = [abs(p - consensus) for p in vig_free_probs]
    return max(deviations) * 100


def calculate_movement(current_prob: float, reference_prob: float) -> float:
    """
    Calculate change in consensus probability.
    Returns change in percentage points.
    Positive = moved toward home, Negative = moved toward away.
    """
    return (current_prob - reference_prob) * 100
```

**Step 4: Run test to verify it passes**

Run: `cd apps/api && pytest tests/test_odds_calculator.py -v`
Expected: PASS (all 17 tests)

**Step 5: Commit**

```bash
git add apps/api/tests/test_odds_calculator.py apps/api/src/services/odds_calculator.py
git commit -m "feat: add calculate_disagreement and calculate_movement with tests"
```

---

### Task 3.6: Update services __init__.py

**Files:**
- Modify: `apps/api/src/services/__init__.py`

**Step 1: Export all calculator functions**

```python
# apps/api/src/services/__init__.py
from src.services.odds_calculator import (
    american_to_implied_prob,
    remove_vig,
    calculate_consensus,
    calculate_edge_ev,
    calculate_disagreement,
    calculate_movement,
)

__all__ = [
    "american_to_implied_prob",
    "remove_vig",
    "calculate_consensus",
    "calculate_edge_ev",
    "calculate_disagreement",
    "calculate_movement",
]
```

**Step 2: Commit**

```bash
git add apps/api/src/services/__init__.py
git commit -m "chore: export odds calculator functions"
```

---

## Phase 4: Pydantic Schemas

### Task 4.1: Game and Odds Schemas

**Files:**
- Create: `apps/api/src/schemas/game.py`
- Create: `apps/api/src/schemas/odds.py`
- Modify: `apps/api/src/schemas/__init__.py`

**Step 1: Create game.py schemas**

```python
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
```

**Step 2: Create odds.py schemas**

```python
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
```

**Step 3: Update schemas/__init__.py**

```python
# apps/api/src/schemas/__init__.py
from src.schemas.game import (
    GameSummary,
    GamesResponse,
    GameDetail,
    BestEdge,
    ConsensusInfo,
    BookOdds,
    MovementInfo,
)
from src.schemas.odds import (
    OddsSnapshot,
    OddsHistoryResponse,
    EdgeOpportunity,
    TopEdgesResponse,
    DisagreementInfo,
    TopDisagreementsResponse,
)

__all__ = [
    "GameSummary",
    "GamesResponse",
    "GameDetail",
    "BestEdge",
    "ConsensusInfo",
    "BookOdds",
    "MovementInfo",
    "OddsSnapshot",
    "OddsHistoryResponse",
    "EdgeOpportunity",
    "TopEdgesResponse",
    "DisagreementInfo",
    "TopDisagreementsResponse",
]
```

**Step 4: Commit**

```bash
git add apps/api/src/schemas/
git commit -m "feat: add Pydantic schemas for games and odds"
```

---

## Phase 5: Odds Provider Adapter

### Task 5.1: Provider Interface and The Odds API Implementation

**Files:**
- Create: `apps/api/src/providers/base.py`
- Create: `apps/api/src/providers/the_odds_api.py`
- Modify: `apps/api/src/providers/__init__.py`

**Step 1: Create base.py interface**

```python
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
```

**Step 2: Create the_odds_api.py implementation**

```python
# apps/api/src/providers/the_odds_api.py
import httpx
from datetime import datetime, timezone
import logging

from src.providers.base import OddsProvider, GameOdds, BookmakerOdds

logger = logging.getLogger(__name__)


class TheOddsApiProvider(OddsProvider):
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_nhl_odds(self) -> list[GameOdds]:
        """Fetch NHL moneyline odds for upcoming games."""
        url = f"{self.BASE_URL}/sports/icehockey_nhl/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        games = []
        for game_data in data:
            bookmakers = []
            for book in game_data.get("bookmakers", []):
                outcomes = {
                    o["name"]: o["price"]
                    for o in book.get("markets", [{}])[0].get("outcomes", [])
                }
                home_team = game_data["home_team"]
                away_team = game_data["away_team"]

                if home_team in outcomes and away_team in outcomes:
                    bookmakers.append(
                        BookmakerOdds(
                            key=book["key"],
                            title=book["title"],
                            home_price=outcomes[home_team],
                            away_price=outcomes[away_team],
                        )
                    )

            if bookmakers:
                games.append(
                    GameOdds(
                        external_id=game_data["id"],
                        home_team=game_data["home_team"],
                        away_team=game_data["away_team"],
                        commence_time=datetime.fromisoformat(
                            game_data["commence_time"].replace("Z", "+00:00")
                        ),
                        bookmakers=bookmakers,
                    )
                )

        logger.info(f"Fetched {len(games)} NHL games with odds")
        return games
```

**Step 3: Update providers/__init__.py**

```python
# apps/api/src/providers/__init__.py
from src.providers.base import OddsProvider, GameOdds, BookmakerOdds
from src.providers.the_odds_api import TheOddsApiProvider

__all__ = ["OddsProvider", "GameOdds", "BookmakerOdds", "TheOddsApiProvider"]
```

**Step 4: Commit**

```bash
git add apps/api/src/providers/
git commit -m "feat: add odds provider adapter with The Odds API implementation"
```

---

## Phase 6: Continue in Next Section

This plan continues with:
- Phase 6: Ingestion Service
- Phase 7: API Routers
- Phase 8: Scheduler Setup
- Phase 9: Auth Integration
- Phase 10: Stripe Webhooks
- Phase 11: FastAPI Main App
- Phase 12: Frontend Setup
- Phase 13: Frontend Pages
- Phase 14: Deployment Config

Due to plan length, these will be in a continuation document.

---

**Checkpoint:** After completing Phase 5, run all tests and verify the backend foundation works:

```bash
cd apps/api
docker-compose up -d  # Start Postgres
pip install -e ".[dev]"
pytest -v  # All 17 tests should pass
alembic upgrade head  # Apply migrations
```
