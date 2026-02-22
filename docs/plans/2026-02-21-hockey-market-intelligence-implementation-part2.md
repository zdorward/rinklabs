# Hockey Market Intelligence MVP - Implementation Plan (Part 2)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Continues from:** `2026-02-21-hockey-market-intelligence-implementation.md`

---

## Phase 6: Ingestion Service

### Task 6.1: Create Ingestion Service

**Files:**
- Create: `apps/api/src/services/ingestion.py`

**Step 1: Create ingestion.py**

```python
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
```

**Step 2: Update services/__init__.py**

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
from src.services.ingestion import OddsIngestionService, IngestResult

__all__ = [
    "american_to_implied_prob",
    "remove_vig",
    "calculate_consensus",
    "calculate_edge_ev",
    "calculate_disagreement",
    "calculate_movement",
    "OddsIngestionService",
    "IngestResult",
]
```

**Step 3: Commit**

```bash
git add apps/api/src/services/
git commit -m "feat: add odds ingestion service"
```

---

## Phase 7: API Routers

### Task 7.1: Health Router

**Files:**
- Create: `apps/api/src/routers/health.py`

**Step 1: Create health.py**

```python
# apps/api/src/routers/health.py
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))
```

**Step 2: Commit**

```bash
git add apps/api/src/routers/health.py
git commit -m "feat: add health check endpoint"
```

---

### Task 7.2: Games Router

**Files:**
- Create: `apps/api/src/routers/games.py`

**Step 1: Create games.py**

```python
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

    # Calculate edges and find best
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

    # Get opening snapshot for movement
    opening_snapshot = (
        db.query(OddsSnapshot)
        .filter(OddsSnapshot.game_id == game_id, OddsSnapshot.is_opening == True)
        .first()
    )

    # Get 24h ago snapshot
    time_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    snapshot_24h = (
        db.query(OddsSnapshot)
        .filter(
            OddsSnapshot.game_id == game_id, OddsSnapshot.snapshot_time <= time_24h_ago
        )
        .order_by(OddsSnapshot.snapshot_time.desc())
        .first()
    )

    # Calculate movement
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
```

**Step 2: Commit**

```bash
git add apps/api/src/routers/games.py
git commit -m "feat: add games router with endpoints"
```

---

### Task 7.3: Markets Router

**Files:**
- Create: `apps/api/src/routers/markets.py`

**Step 1: Create markets.py**

```python
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
    is_pro: bool = False,  # Will be set by auth middleware
):
    """Get top edge opportunities across today's games."""
    effective_limit = limit if is_pro else FREE_LIMIT
    games = _get_today_games(db)

    all_edges = []

    for game in games:
        snapshots = _get_latest_snapshots_for_game(db, game.id)
        if not snapshots:
            continue

        # Calculate consensus
        home_probs = []
        for snap in snapshots:
            home_implied = american_to_implied_prob(snap.home_price)
            away_implied = american_to_implied_prob(snap.away_price)
            home_fair, _ = remove_vig(home_implied, away_implied)
            home_probs.append(home_fair)

        consensus_home = calculate_consensus(home_probs)
        consensus_away = 1 - consensus_home

        # Find edges per book
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

    # Sort by EV% descending
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

    # Sort by disagreement descending
    all_disagreements.sort(key=lambda x: x.disagreement_pct, reverse=True)
    total_count = len(all_disagreements)
    truncated = total_count > effective_limit

    return TopDisagreementsResponse(
        disagreements=all_disagreements[:effective_limit],
        truncated=truncated,
        total_count=total_count,
    )
```

**Step 2: Commit**

```bash
git add apps/api/src/routers/markets.py
git commit -m "feat: add markets router with top-edges and top-disagreements"
```

---

### Task 7.4: Users and Webhooks Routers

**Files:**
- Create: `apps/api/src/routers/users.py`
- Create: `apps/api/src/routers/webhooks.py`

**Step 1: Create users.py**

```python
# apps/api/src/routers/users.py
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.auth import get_current_user, require_user, require_pro

router = APIRouter()


class UserResponse(BaseModel):
    id: UUID
    email: str | None
    subscription_status: str
    current_period_end: datetime | None


class ProMarketsResponse(BaseModel):
    message: str
    # Full implementation would include all markets data


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_user)):
    """Get current user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        subscription_status=user.subscription_status,
        current_period_end=user.current_period_end,
    )


@router.get("/pro/markets/today")
async def get_pro_markets(
    user: User = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Get full market board for pro users."""
    # This would return all games with full details
    # For now, return a placeholder that indicates pro access
    return {"access": "pro", "user_id": str(user.id)}
```

**Step 2: Create webhooks.py**

```python
# apps/api/src/routers/webhooks.py
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db
from src.models import User

router = APIRouter()
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        clerk_user_id = session.get("metadata", {}).get("clerk_user_id")

        if clerk_user_id:
            user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
            if user:
                user.stripe_customer_id = session.get("customer")
                user.subscription_id = session.get("subscription")
                user.subscription_status = "active"
                user.updated_at = datetime.now(timezone.utc)
                db.commit()

    elif event["type"] == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")

        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = sub.get("status", "active")
            if sub.get("current_period_end"):
                user.current_period_end = datetime.fromtimestamp(
                    sub["current_period_end"], tz=timezone.utc
                )
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")

        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = "canceled"
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

    return {"received": True}
```

**Step 3: Update routers/__init__.py**

```python
# apps/api/src/routers/__init__.py
from src.routers.health import router as health_router
from src.routers.games import router as games_router
from src.routers.markets import router as markets_router
from src.routers.users import router as users_router
from src.routers.webhooks import router as webhooks_router

__all__ = [
    "health_router",
    "games_router",
    "markets_router",
    "users_router",
    "webhooks_router",
]
```

**Step 4: Commit**

```bash
git add apps/api/src/routers/
git commit -m "feat: add users and webhooks routers"
```

---

## Phase 8: Auth Module

### Task 8.1: Clerk Auth Dependencies

**Files:**
- Create: `apps/api/src/auth/__init__.py`

**Step 1: Create auth module**

```python
# apps/api/src/auth/__init__.py
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import httpx

from src.config import get_settings
from src.database import get_db
from src.models import User

settings = get_settings()


async def verify_clerk_token(token: str) -> dict | None:
    """Verify Clerk JWT and return session claims."""
    if not settings.clerk_secret_key:
        return None

    # For production, use Clerk's official SDK
    # This is a simplified version for MVP
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.clerk.com/v1/sessions/verify",
                headers={
                    "Authorization": f"Bearer {settings.clerk_secret_key}",
                },
                params={"token": token},
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


def get_or_create_user(db: Session, clerk_id: str, email: str | None = None) -> User:
    """Get existing user or create new one."""
    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        user = User(clerk_id=clerk_id, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        user.email = email
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
    return user


async def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Get current user from Clerk JWT.
    Returns None if no auth header (for optional auth routes).
    """
    if not authorization:
        return None

    token = authorization.replace("Bearer ", "")
    claims = await verify_clerk_token(token)

    if not claims:
        return None

    user_id = claims.get("user_id") or claims.get("sub")
    email = claims.get("email")

    if not user_id:
        return None

    return get_or_create_user(db, clerk_id=user_id, email=email)


async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Dependency that requires authenticated user."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_pro(
    user: User = Depends(require_user),
) -> User:
    """Dependency that requires active subscription."""
    if user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Pro subscription required")
    return user
```

**Step 2: Commit**

```bash
git add apps/api/src/auth/__init__.py
git commit -m "feat: add Clerk auth dependencies"
```

---

## Phase 9: Scheduler Setup

### Task 9.1: APScheduler Configuration

**Files:**
- Create: `apps/api/src/scheduler/jobs.py`
- Modify: `apps/api/src/scheduler/__init__.py`

**Step 1: Create jobs.py**

```python
# apps/api/src/scheduler/jobs.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings
from src.database import SessionLocal
from src.providers import TheOddsApiProvider
from src.services import OddsIngestionService

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def scheduled_ingest():
    """Run odds ingestion. Called every 10 minutes."""
    logger.info("Starting scheduled odds ingestion")

    if not settings.odds_api_key:
        logger.warning("ODDS_API_KEY not set, skipping ingestion")
        return

    db = SessionLocal()
    try:
        provider = TheOddsApiProvider(settings.odds_api_key)
        service = OddsIngestionService(provider, db)
        result = await service.ingest()
        logger.info(f"Ingestion complete: {result.games_processed} games, {result.snapshots_created} snapshots")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
    finally:
        db.close()


def setup_scheduler():
    """Called on app startup."""
    scheduler.add_job(
        scheduled_ingest,
        trigger=IntervalTrigger(minutes=10),
        id="odds_ingestion",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started - ingesting every 10 minutes")


def shutdown_scheduler():
    """Called on app shutdown."""
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")
```

**Step 2: Update scheduler/__init__.py**

```python
# apps/api/src/scheduler/__init__.py
from src.scheduler.jobs import setup_scheduler, shutdown_scheduler, scheduled_ingest

__all__ = ["setup_scheduler", "shutdown_scheduler", "scheduled_ingest"]
```

**Step 3: Commit**

```bash
git add apps/api/src/scheduler/
git commit -m "feat: add APScheduler for odds ingestion"
```

---

## Phase 10: FastAPI Main Application

### Task 10.1: Main App with Lifespan

**Files:**
- Create: `apps/api/src/main.py`

**Step 1: Create main.py**

```python
# apps/api/src/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.scheduler import setup_scheduler, shutdown_scheduler
from src.routers import (
    health_router,
    games_router,
    markets_router,
    users_router,
    webhooks_router,
)

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - start/stop scheduler."""
    logger.info("Starting application")
    setup_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Application stopped")


app = FastAPI(
    title="Rinklabs API",
    description="Hockey market intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(games_router)
app.include_router(markets_router)
app.include_router(users_router)
app.include_router(webhooks_router)
```

**Step 2: Commit**

```bash
git add apps/api/src/main.py
git commit -m "feat: add FastAPI main application"
```

---

### Task 10.2: Seed Script

**Files:**
- Create: `apps/api/scripts/seed_dev.py`

**Step 1: Create seed_dev.py**

```python
#!/usr/bin/env python
# apps/api/scripts/seed_dev.py
"""
One-time ingestion script for development.
Run: python scripts/seed_dev.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_settings
from src.database import SessionLocal
from src.providers import TheOddsApiProvider
from src.services import OddsIngestionService


async def main():
    settings = get_settings()

    if not settings.odds_api_key:
        print("ERROR: ODDS_API_KEY not set in environment")
        print("Set it in .env file or environment variable")
        sys.exit(1)

    print("Starting one-time odds ingestion...")

    db = SessionLocal()
    try:
        provider = TheOddsApiProvider(settings.odds_api_key)
        service = OddsIngestionService(provider, db)
        result = await service.ingest()
        print(f"Success! Ingested {result.games_processed} games with {result.snapshots_created} snapshots")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Commit**

```bash
git add apps/api/scripts/seed_dev.py
git commit -m "feat: add dev seed script for one-time ingestion"
```

---

## Phase 11: Frontend Setup

### Task 11.1: Next.js Project Initialization

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.js`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/postcss.config.js`
- Create: `apps/web/.env.example`

**Step 1: Create package.json**

```json
{
  "name": "rinklabs-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@clerk/nextjs": "^4.29.0",
    "@tanstack/react-query": "^5.17.0",
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.10.0",
    "stripe": "^14.12.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.56.0",
    "eslint-config-next": "14.1.0",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3"
  }
}
```

**Step 2: Create next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
```

**Step 3: Create tailwind.config.ts**

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        edge: {
          positive: '#22c55e',
          negative: '#ef4444',
        },
      },
    },
  },
  plugins: [],
}

export default config
```

**Step 4: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**Step 5: Create postcss.config.js**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 6: Create .env.example**

```bash
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx

# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

**Step 7: Commit**

```bash
git add apps/web/
git commit -m "chore: scaffold Next.js frontend project"
```

---

### Task 11.2: Frontend Lib and API Client

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/utils.ts`

**Step 1: Create directory structure**

```bash
mkdir -p apps/web/src/{app,components,lib}
```

**Step 2: Create api.ts**

```typescript
// apps/web/src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface GameSummary {
  id: string
  home_team: string
  away_team: string
  commence_time: string
  consensus_home_prob: number
  consensus_away_prob: number
  best_edge: {
    side: string
    bookmaker: string
    ev_pct: number
  } | null
  disagreement: number
  books_count: number
}

export interface EdgeOpportunity {
  game_id: string
  home_team: string
  away_team: string
  commence_time: string
  side: string
  bookmaker: string
  ev_pct: number
  book_price: number
  consensus_prob: number
}

export interface DisagreementInfo {
  game_id: string
  home_team: string
  away_team: string
  commence_time: string
  disagreement_pct: number
  range: { min_prob: number; max_prob: number }
}

export interface TopEdgesResponse {
  edges: EdgeOpportunity[]
  truncated: boolean
  total_count: number
}

export interface TopDisagreementsResponse {
  disagreements: DisagreementInfo[]
  truncated: boolean
  total_count: number
}

export interface UserInfo {
  id: string
  email: string | null
  subscription_status: string
  current_period_end: string | null
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit & { token?: string }
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }

  if (options?.token) {
    headers['Authorization'] = `Bearer ${options.token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export const api = {
  getGames: (date: string) =>
    fetchApi<{ games: GameSummary[] }>(`/games?date=${date}`),

  getGame: (gameId: string) =>
    fetchApi<GameSummary>(`/games/${gameId}`),

  getTopEdges: (limit?: number) =>
    fetchApi<TopEdgesResponse>(`/markets/today/top-edges${limit ? `?limit=${limit}` : ''}`),

  getTopDisagreements: (limit?: number) =>
    fetchApi<TopDisagreementsResponse>(`/markets/today/top-disagreements${limit ? `?limit=${limit}` : ''}`),

  getMe: (token: string) =>
    fetchApi<UserInfo>('/me', { token }),
}
```

**Step 3: Create utils.ts**

```typescript
// apps/web/src/lib/utils.ts
export function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`
}

export function formatProbability(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`
}

export function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function getEdgeColor(evPct: number): string {
  if (evPct >= 5) return 'text-green-600'
  if (evPct >= 2) return 'text-green-500'
  if (evPct > 0) return 'text-green-400'
  return 'text-gray-500'
}
```

**Step 4: Commit**

```bash
git add apps/web/src/lib/
git commit -m "feat: add API client and utility functions"
```

---

## Phase 12: Frontend App Structure

### Task 12.1: Layout and Middleware

**Files:**
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/middleware.ts`

**Step 1: Create layout.tsx**

```typescript
// apps/web/src/app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs'
import { QueryProvider } from '@/components/QueryProvider'
import { Navbar } from '@/components/Navbar'
import './globals.css'

export const metadata = {
  title: 'Rinklabs - Hockey Market Intelligence',
  description: 'Market intelligence for NHL betting',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-gray-50 min-h-screen">
          <QueryProvider>
            <Navbar />
            <main className="container mx-auto px-4 py-8">
              {children}
            </main>
          </QueryProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
```

**Step 2: Create globals.css**

```css
/* apps/web/src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: system-ui, -apple-system, sans-serif;
}
```

**Step 3: Create middleware.ts**

```typescript
// apps/web/src/middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isProtectedRoute = createRouteMatcher([
  '/pro(.*)',
  '/account(.*)',
])

export default clerkMiddleware((auth, req) => {
  if (isProtectedRoute(req)) {
    auth().protect()
  }
})

export const config = {
  matcher: ['/((?!.+\\.[\\w]+$|_next).*)', '/', '/(api|trpc)(.*)'],
}
```

**Step 4: Commit**

```bash
git add apps/web/src/app/layout.tsx apps/web/src/app/globals.css apps/web/src/middleware.ts
git commit -m "feat: add app layout and Clerk middleware"
```

---

### Task 12.2: Core Components

**Files:**
- Create: `apps/web/src/components/QueryProvider.tsx`
- Create: `apps/web/src/components/Navbar.tsx`
- Create: `apps/web/src/components/EdgeCard.tsx`
- Create: `apps/web/src/components/SubscriptionGate.tsx`

**Step 1: Create QueryProvider.tsx**

```typescript
// apps/web/src/components/QueryProvider.tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            refetchInterval: 10 * 60 * 1000,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
```

**Step 2: Create Navbar.tsx**

```typescript
// apps/web/src/components/Navbar.tsx
'use client'

import Link from 'next/link'
import { UserButton, useUser } from '@clerk/nextjs'

export function Navbar() {
  const { isSignedIn } = useUser()

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="font-bold text-xl text-gray-900">
              Rinklabs
            </Link>
            <div className="flex space-x-4">
              <Link
                href="/"
                className="text-gray-600 hover:text-gray-900 px-3 py-2"
              >
                Markets
              </Link>
              <Link
                href="/pro"
                className="text-gray-600 hover:text-gray-900 px-3 py-2"
              >
                Pro
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isSignedIn ? (
              <>
                <Link
                  href="/account"
                  className="text-gray-600 hover:text-gray-900"
                >
                  Account
                </Link>
                <UserButton afterSignOutUrl="/" />
              </>
            ) : (
              <Link
                href="/sign-in"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
```

**Step 3: Create EdgeCard.tsx**

```typescript
// apps/web/src/components/EdgeCard.tsx
import Link from 'next/link'
import { EdgeOpportunity } from '@/lib/api'
import { formatOdds, formatDateTime, getEdgeColor } from '@/lib/utils'

interface EdgeCardProps {
  edge: EdgeOpportunity
}

export function EdgeCard({ edge }: EdgeCardProps) {
  return (
    <Link href={`/games/${edge.game_id}`}>
      <div className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start mb-2">
          <div>
            <p className="text-sm text-gray-500">{formatDateTime(edge.commence_time)}</p>
            <p className="font-medium">
              {edge.away_team} @ {edge.home_team}
            </p>
          </div>
          <span className={`text-lg font-bold ${getEdgeColor(edge.ev_pct)}`}>
            +{edge.ev_pct.toFixed(1)}% EV
          </span>
        </div>
        <div className="flex justify-between text-sm text-gray-600">
          <span>
            {edge.side === 'home' ? edge.home_team : edge.away_team} ML
          </span>
          <span>
            {edge.bookmaker}: {formatOdds(edge.book_price)}
          </span>
        </div>
      </div>
    </Link>
  )
}
```

**Step 4: Create SubscriptionGate.tsx**

```typescript
// apps/web/src/components/SubscriptionGate.tsx
'use client'

import { useUser } from '@clerk/nextjs'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import Link from 'next/link'

interface SubscriptionGateProps {
  children: React.ReactNode
}

export function SubscriptionGate({ children }: SubscriptionGateProps) {
  const { isSignedIn, user } = useUser()

  const { data: userInfo, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      // Get token from Clerk - simplified for MVP
      return api.getMe('')
    },
    enabled: isSignedIn,
  })

  if (!isSignedIn) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Sign in required</h2>
        <p className="text-gray-600 mb-6">
          Sign in to access Pro features
        </p>
        <Link
          href="/sign-in"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
        >
          Sign In
        </Link>
      </div>
    )
  }

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (userInfo?.subscription_status !== 'active') {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Upgrade to Pro</h2>
        <p className="text-gray-600 mb-6">
          Get unlimited access to all market intelligence
        </p>
        <Link
          href="/account"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
        >
          Upgrade Now
        </Link>
      </div>
    )
  }

  return <>{children}</>
}
```

**Step 5: Commit**

```bash
git add apps/web/src/components/
git commit -m "feat: add core frontend components"
```

---

## Phase 13: Frontend Pages

### Task 13.1: Home Page

**Files:**
- Create: `apps/web/src/app/page.tsx`

**Step 1: Create page.tsx**

```typescript
// apps/web/src/app/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { EdgeCard } from '@/components/EdgeCard'
import Link from 'next/link'

export default function HomePage() {
  const { data: edgesData, isLoading: edgesLoading } = useQuery({
    queryKey: ['top-edges'],
    queryFn: () => api.getTopEdges(),
  })

  const { data: disagreementsData, isLoading: disagreementsLoading } = useQuery({
    queryKey: ['top-disagreements'],
    queryFn: () => api.getTopDisagreements(),
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">NHL Market Intelligence</h1>
        <p className="text-gray-600">
          Real-time odds analysis across major sportsbooks
        </p>
      </div>

      {/* Top Edges Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Top Edge Opportunities</h2>
          {edgesData?.truncated && (
            <Link href="/pro" className="text-blue-600 hover:underline text-sm">
              View all {edgesData.total_count} edges →
            </Link>
          )}
        </div>

        {edgesLoading ? (
          <div className="text-gray-500">Loading edges...</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {edgesData?.edges.map((edge) => (
              <EdgeCard key={`${edge.game_id}-${edge.bookmaker}-${edge.side}`} edge={edge} />
            ))}
          </div>
        )}

        {edgesData?.edges.length === 0 && !edgesLoading && (
          <p className="text-gray-500">No edge opportunities found</p>
        )}
      </section>

      {/* Top Disagreements Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Highest Market Disagreement</h2>
          {disagreementsData?.truncated && (
            <Link href="/pro" className="text-blue-600 hover:underline text-sm">
              View all {disagreementsData.total_count} →
            </Link>
          )}
        </div>

        {disagreementsLoading ? (
          <div className="text-gray-500">Loading...</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {disagreementsData?.disagreements.map((d) => (
              <Link key={d.game_id} href={`/games/${d.game_id}`}>
                <div className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
                  <p className="font-medium mb-1">
                    {d.away_team} @ {d.home_team}
                  </p>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Disagreement</span>
                    <span className="font-semibold text-amber-600">
                      {d.disagreement_pct.toFixed(1)}pp
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Range: {(d.range.min_prob * 100).toFixed(1)}% - {(d.range.max_prob * 100).toFixed(1)}%
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add apps/web/src/app/page.tsx
git commit -m "feat: add home page with top edges and disagreements"
```

---

### Task 13.2: Auth Pages

**Files:**
- Create: `apps/web/src/app/sign-in/[[...sign-in]]/page.tsx`
- Create: `apps/web/src/app/sign-up/[[...sign-up]]/page.tsx`

**Step 1: Create sign-in page**

```typescript
// apps/web/src/app/sign-in/[[...sign-in]]/page.tsx
import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="flex justify-center py-12">
      <SignIn />
    </div>
  )
}
```

**Step 2: Create sign-up page**

```typescript
// apps/web/src/app/sign-up/[[...sign-up]]/page.tsx
import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="flex justify-center py-12">
      <SignUp />
    </div>
  )
}
```

**Step 3: Commit**

```bash
mkdir -p "apps/web/src/app/sign-in/[[...sign-in]]"
mkdir -p "apps/web/src/app/sign-up/[[...sign-up]]"
git add apps/web/src/app/sign-in/ apps/web/src/app/sign-up/
git commit -m "feat: add Clerk auth pages"
```

---

### Task 13.3: Pro and Account Pages

**Files:**
- Create: `apps/web/src/app/pro/page.tsx`
- Create: `apps/web/src/app/account/page.tsx`

**Step 1: Create pro page**

```typescript
// apps/web/src/app/pro/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { SubscriptionGate } from '@/components/SubscriptionGate'
import { api } from '@/lib/api'
import { EdgeCard } from '@/components/EdgeCard'

export default function ProPage() {
  return (
    <SubscriptionGate>
      <ProContent />
    </SubscriptionGate>
  )
}

function ProContent() {
  const { data: edgesData, isLoading } = useQuery({
    queryKey: ['top-edges', 'unlimited'],
    queryFn: () => api.getTopEdges(100),
  })

  const { data: disagreementsData } = useQuery({
    queryKey: ['top-disagreements', 'unlimited'],
    queryFn: () => api.getTopDisagreements(100),
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Pro Market Board</h1>
        <p className="text-gray-600">Full access to all market intelligence</p>
      </div>

      <section>
        <h2 className="text-xl font-semibold mb-4">
          All Edge Opportunities ({edgesData?.total_count || 0})
        </h2>
        {isLoading ? (
          <div>Loading...</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {edgesData?.edges.map((edge) => (
              <EdgeCard
                key={`${edge.game_id}-${edge.bookmaker}-${edge.side}`}
                edge={edge}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">
          All Disagreements ({disagreementsData?.total_count || 0})
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {disagreementsData?.disagreements.map((d) => (
            <div
              key={d.game_id}
              className="bg-white rounded-lg shadow-sm border p-4"
            >
              <p className="font-medium mb-1">
                {d.away_team} @ {d.home_team}
              </p>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Disagreement</span>
                <span className="font-semibold text-amber-600">
                  {d.disagreement_pct.toFixed(1)}pp
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
```

**Step 2: Create account page**

```typescript
// apps/web/src/app/account/page.tsx
'use client'

import { useUser } from '@clerk/nextjs'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'

export default function AccountPage() {
  const { user } = useUser()
  const searchParams = useSearchParams()
  const upgraded = searchParams.get('upgraded')

  const { data: userInfo, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: () => api.getMe(''),
    enabled: !!user,
  })

  const handleUpgrade = async () => {
    const response = await fetch('/api/create-checkout-session', {
      method: 'POST',
    })
    const { url } = await response.json()
    if (url) {
      window.location.href = url
    }
  }

  const handleManageBilling = async () => {
    const response = await fetch('/api/create-portal-session', {
      method: 'POST',
    })
    const { url } = await response.json()
    if (url) {
      window.location.href = url
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Account</h1>

      {upgraded && (
        <div className="bg-green-100 text-green-800 p-4 rounded-lg mb-6">
          Welcome to Pro! You now have full access.
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-xl font-semibold mb-4">Subscription</h2>

        {isLoading ? (
          <div>Loading...</div>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600">Status</span>
              <span
                className={`font-medium ${
                  userInfo?.subscription_status === 'active'
                    ? 'text-green-600'
                    : 'text-gray-600'
                }`}
              >
                {userInfo?.subscription_status === 'active' ? 'Pro' : 'Free'}
              </span>
            </div>

            {userInfo?.current_period_end && (
              <div className="flex justify-between">
                <span className="text-gray-600">Renews</span>
                <span>
                  {new Date(userInfo.current_period_end).toLocaleDateString()}
                </span>
              </div>
            )}

            <div className="pt-4">
              {userInfo?.subscription_status === 'active' ? (
                <button
                  onClick={handleManageBilling}
                  className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"
                >
                  Manage Billing
                </button>
              ) : (
                <button
                  onClick={handleUpgrade}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                >
                  Upgrade to Pro
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add apps/web/src/app/pro/ apps/web/src/app/account/
git commit -m "feat: add pro and account pages"
```

---

### Task 13.4: Stripe API Routes

**Files:**
- Create: `apps/web/src/app/api/create-checkout-session/route.ts`
- Create: `apps/web/src/app/api/create-portal-session/route.ts`

**Step 1: Create checkout session route**

```typescript
// apps/web/src/app/api/create-checkout-session/route.ts
import { auth, currentUser } from '@clerk/nextjs/server'
import Stripe from 'stripe'
import { NextResponse } from 'next/server'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
})

export async function POST() {
  const { userId } = auth()

  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const user = await currentUser()
  const email = user?.emailAddresses[0]?.emailAddress

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      customer_email: email,
      line_items: [
        {
          price: process.env.STRIPE_PRO_PRICE_ID,
          quantity: 1,
        },
      ],
      metadata: {
        clerk_user_id: userId,
      },
      success_url: `${process.env.NEXT_PUBLIC_APP_URL}/account?upgraded=true`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/account`,
    })

    return NextResponse.json({ url: session.url })
  } catch (error) {
    console.error('Stripe error:', error)
    return NextResponse.json({ error: 'Failed to create session' }, { status: 500 })
  }
}
```

**Step 2: Create portal session route**

```typescript
// apps/web/src/app/api/create-portal-session/route.ts
import { auth } from '@clerk/nextjs/server'
import Stripe from 'stripe'
import { NextResponse } from 'next/server'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
})

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST() {
  const { userId, getToken } = auth()

  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    // Get user's stripe_customer_id from our API
    const token = await getToken()
    const response = await fetch(`${API_URL}/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      throw new Error('Failed to get user info')
    }

    const userInfo = await response.json()

    if (!userInfo.stripe_customer_id) {
      return NextResponse.json({ error: 'No subscription found' }, { status: 400 })
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: userInfo.stripe_customer_id,
      return_url: `${process.env.NEXT_PUBLIC_APP_URL}/account`,
    })

    return NextResponse.json({ url: session.url })
  } catch (error) {
    console.error('Portal error:', error)
    return NextResponse.json({ error: 'Failed to create portal session' }, { status: 500 })
  }
}
```

**Step 3: Commit**

```bash
mkdir -p apps/web/src/app/api/create-checkout-session
mkdir -p apps/web/src/app/api/create-portal-session
git add apps/web/src/app/api/
git commit -m "feat: add Stripe checkout and portal API routes"
```

---

## Phase 14: Deployment Config

### Task 14.1: Backend Dockerfile and Railway Config

**Files:**
- Create: `apps/api/Dockerfile`
- Create: `apps/api/railway.toml`

**Step 1: Create Dockerfile**

```dockerfile
# apps/api/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Step 2: Create railway.toml**

```toml
# apps/api/railway.toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
```

**Step 3: Commit**

```bash
git add apps/api/Dockerfile apps/api/railway.toml
git commit -m "feat: add backend Dockerfile and Railway config"
```

---

### Task 14.2: Frontend Vercel Config

**Files:**
- Create: `apps/web/vercel.json`

**Step 1: Create vercel.json**

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next"
}
```

**Step 2: Commit**

```bash
git add apps/web/vercel.json
git commit -m "feat: add Vercel config for frontend"
```

---

## Final Checkpoint

After completing all phases, verify the full setup:

```bash
# Backend
cd apps/api
docker-compose up -d
pip install -e ".[dev]"
alembic upgrade head
pytest -v
uvicorn src.main:app --reload --port 8000

# Frontend (new terminal)
cd apps/web
npm install
npm run dev
```

Visit:
- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000

---

**Plan complete and saved to `docs/plans/2026-02-21-hockey-market-intelligence-implementation.md` and `docs/plans/2026-02-21-hockey-market-intelligence-implementation-part2.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
