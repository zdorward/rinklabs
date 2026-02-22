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
