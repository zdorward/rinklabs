# Hockey Market Intelligence MVP - Design Document

**Date:** 2026-02-21
**Status:** Approved

## Overview

A production-ready MVP for a hockey betting market intelligence web app. Aggregates odds from multiple sportsbooks, calculates vig-free consensus probabilities, identifies market inefficiencies (edges), and tracks line movement. Monetized via Stripe subscriptions with free-tier limitations.

## Key Decisions

| Decision | Choice |
|----------|--------|
| Auth Provider | Clerk |
| Odds API | The Odds API |
| Edge Calculation | EV% |
| Hosting | Railway (API + Postgres) + Vercel (frontend) |
| Pricing Model | Single Pro tier |
| Architecture | Unified backend process with APScheduler |

## Repository Structure

```
rinklabs/
├── README.md
├── docker-compose.yml
├── .gitignore
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/versions/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── routers/
│   │   │   ├── services/
│   │   │   ├── providers/
│   │   │   ├── scheduler/
│   │   │   └── auth/
│   │   ├── tests/
│   │   ├── scripts/
│   │   ├── .env.example
│   │   └── Dockerfile
│   └── web/                        # Next.js frontend
│       ├── package.json
│       ├── next.config.js
│       ├── tailwind.config.ts
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   └── lib/
│       ├── .env.example
│       └── Dockerfile
└── docs/plans/
```

## Database Schema

### games
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| external_id | VARCHAR(100) | Unique ID from Odds API |
| home_team | VARCHAR(100) | Home team name |
| away_team | VARCHAR(100) | Away team name |
| commence_time | TIMESTAMP TZ | Game start time |
| created_at | TIMESTAMP TZ | Record created |
| updated_at | TIMESTAMP TZ | Record updated |

### odds_snapshots
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| game_id | UUID | FK to games |
| bookmaker | VARCHAR(50) | Bookmaker key |
| home_price | INTEGER | American odds for home |
| away_price | INTEGER | American odds for away |
| snapshot_time | TIMESTAMP TZ | When snapshot was taken |
| is_opening | BOOLEAN | True if first snapshot |
| created_at | TIMESTAMP TZ | Record created |

### users
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| clerk_id | VARCHAR(100) | Clerk user ID |
| email | VARCHAR(255) | User email |
| stripe_customer_id | VARCHAR(100) | Stripe customer |
| subscription_status | VARCHAR(20) | free/active/canceled/past_due |
| subscription_id | VARCHAR(100) | Stripe subscription ID |
| current_period_end | TIMESTAMP TZ | Subscription end date |
| created_at | TIMESTAMP TZ | Record created |
| updated_at | TIMESTAMP TZ | Record updated |

## Calculation Logic

### American Odds to Implied Probability
```
if odds > 0: prob = 100 / (odds + 100)
if odds < 0: prob = |odds| / (|odds| + 100)
```

### Vig Removal (Two-Outcome Normalization)
```
home_fair = home_prob / (home_prob + away_prob)
away_fair = away_prob / (home_prob + away_prob)
```

### Consensus Probability
Median of vig-free probabilities across all bookmakers.

### Edge (EV%)
```
edge = ((consensus_prob - book_vig_free_prob) / book_vig_free_prob) * 100
```
Positive EV% = book underestimates probability = betting value.

### Disagreement
Max absolute deviation from consensus across all books (in percentage points).

### Line Movement
Change in consensus probability from opening or 24h ago (in percentage points).

## API Endpoints

### Public
- `GET /health` - Health check
- `GET /games?date=YYYY-MM-DD` - Games for date with summary
- `GET /games/{game_id}` - Full game detail with odds
- `GET /games/{game_id}/odds` - Historical snapshots

### Free-Limited
- `GET /markets/today/top-edges?limit=3` - Top edge opportunities
- `GET /markets/today/top-disagreements?limit=3` - Top disagreement games

### Auth Required
- `GET /me` - Current user info
- `GET /pro/markets/today` - Full board (requires active subscription)

### Webhooks
- `POST /webhooks/stripe` - Stripe subscription events

## Frontend Pages

| Route | Description | Access |
|-------|-------------|--------|
| `/` | Home with top edges/disagreements | Public (limited) |
| `/games/[gameId]` | Game detail with odds table | Public |
| `/pro` | Full market board | Pro only |
| `/account` | Subscription management | Auth required |
| `/sign-in`, `/sign-up` | Clerk auth pages | Public |

## Components

- `Navbar` - Navigation with auth state
- `EdgeCard` - Edge opportunity display
- `OddsTable` - Bookmaker odds comparison
- `MovementSparkline` - Line movement chart
- `SubscriptionGate` - Pro content wrapper
- `UpgradeCTA` - Subscription upsell

## Auth Flow

1. User signs in via Clerk
2. Frontend includes Clerk JWT in API requests
3. Backend verifies JWT with Clerk SDK
4. Backend creates/retrieves user record
5. Subscription status checked for protected routes

## Payment Flow

1. User clicks "Upgrade to Pro"
2. Frontend calls Next.js API route
3. Route creates Stripe Checkout session
4. User completes payment on Stripe
5. Stripe webhook fires to backend
6. Backend updates user subscription_status
7. User redirected to account page

## Scheduler

APScheduler runs in-process with FastAPI:
- Job: `scheduled_ingest` every 10 minutes
- Fetches NHL odds from The Odds API
- Upserts games, creates odds snapshots
- Structured for future extraction to Celery

## Deployment

### Railway (Backend)
- PostgreSQL service (provisioned by Railway)
- FastAPI service with Dockerfile
- Start command: `alembic upgrade head && uvicorn src.main:app`
- Health check: `/health`

### Vercel (Frontend)
- Next.js with App Router
- Root directory: `apps/web`
- Auto-deploy on push to main

### Environment Variables

**Backend:**
- `DATABASE_URL`
- `ODDS_API_KEY`
- `CLERK_SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRO_PRICE_ID`

**Frontend:**
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_APP_URL`

## Testing Strategy

### Unit Tests
- Odds conversion functions
- Vig removal
- Consensus calculation
- Edge calculation
- Disagreement calculation
- Movement calculation

### Integration Tests
- API endpoint responses
- Auth middleware
- Webhook handling

## Out of Scope (MVP)

- Multiple sports (NHL only)
- Bet types beyond moneyline
- Real-time WebSocket updates
- Mobile app
- AI/ML predictions
- Historical analytics
- Multiple subscription tiers
