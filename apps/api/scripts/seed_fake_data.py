# apps/api/scripts/seed_fake_data.py
"""Seed database with fake games and odds for testing."""
import sys
sys.path.insert(0, "/Users/zackdorward/dev/rinklabs/apps/api")

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from src.database import SessionLocal
from src.models import Game, OddsSnapshot

# NHL teams
TEAMS = [
    "Colorado Avalanche", "Vegas Golden Knights", "Dallas Stars", "Minnesota Wild",
    "Winnipeg Jets", "Nashville Predators", "St. Louis Blues", "Arizona Coyotes",
    "Edmonton Oilers", "Los Angeles Kings", "Vancouver Canucks", "Calgary Flames",
    "Seattle Kraken", "San Jose Sharks", "Anaheim Ducks", "Chicago Blackhawks",
    "Florida Panthers", "Boston Bruins", "Toronto Maple Leafs", "Tampa Bay Lightning",
    "Carolina Hurricanes", "New Jersey Devils", "New York Rangers", "Detroit Red Wings",
]

BOOKMAKERS = ["draftkings", "fanduel", "betmgm", "caesars", "pointsbet", "betrivers"]

def seed_data():
    db = SessionLocal()

    try:
        # Create 8 games over the next 5 days
        now = datetime.now(timezone.utc)
        games_data = []

        for i in range(8):
            home_idx = (i * 2) % len(TEAMS)
            away_idx = (i * 2 + 1) % len(TEAMS)

            game = Game(
                id=uuid4(),
                external_id=f"fake_game_{i}",
                home_team=TEAMS[home_idx],
                away_team=TEAMS[away_idx],
                commence_time=now + timedelta(days=i // 2, hours=19 + (i % 3)),
            )
            db.add(game)
            games_data.append(game)

        db.flush()

        # Add odds for each game from multiple bookmakers
        # Vary the odds to create edges and disagreements
        for game in games_data:
            base_home_prob = 0.35 + (hash(str(game.id)) % 30) / 100  # 35-65%

            for j, book in enumerate(BOOKMAKERS):
                # Add some variance per bookmaker to create edges
                variance = (hash(f"{game.id}_{book}") % 10 - 5) / 100  # -5% to +5%
                home_prob = base_home_prob + variance
                away_prob = 1 - home_prob

                # Convert to American odds (with vig)
                vig = 1.05  # 5% vig
                if home_prob > 0.5:
                    home_price = int(-100 * home_prob * vig / (1 - home_prob))
                else:
                    home_price = int(100 * (1 - home_prob) / (home_prob * vig))

                if away_prob > 0.5:
                    away_price = int(-100 * away_prob * vig / (1 - away_prob))
                else:
                    away_price = int(100 * (1 - away_prob) / (away_prob * vig))

                snapshot = OddsSnapshot(
                    id=uuid4(),
                    game_id=game.id,
                    bookmaker=book,
                    home_price=home_price,
                    away_price=away_price,
                    snapshot_time=now - timedelta(hours=j),  # Stagger times
                    is_opening=(j == len(BOOKMAKERS) - 1),
                )
                db.add(snapshot)

        db.commit()
        print(f"Created {len(games_data)} games with odds from {len(BOOKMAKERS)} bookmakers each")
        print("Total snapshots:", len(games_data) * len(BOOKMAKERS))

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
