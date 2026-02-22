import statistics


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def remove_vig(home_prob: float, away_prob: float) -> tuple[float, float]:
    """Remove vig by normalizing probabilities to sum to 1.0."""
    total = home_prob + away_prob
    return home_prob / total, away_prob / total


def calculate_consensus(vig_free_probs: list[float]) -> float:
    """Calculate median of vig-free probabilities across all books."""
    if not vig_free_probs:
        return 0.0
    return statistics.median(vig_free_probs)


def calculate_edge_ev(book_vig_free_prob: float, consensus_prob: float) -> float:
    """
    Calculate Expected Value percentage.

    Positive EV% means the book is offering better odds than consensus
    (book underestimates probability = better payout for us).
    """
    if book_vig_free_prob == 0:
        return 0.0
    return ((consensus_prob - book_vig_free_prob) / book_vig_free_prob) * 100


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
