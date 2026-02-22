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


class TestCalculateEdgeEV:
    def test_positive_edge(self):
        from src.services.odds_calculator import calculate_edge_ev

        edge = calculate_edge_ev(book_vig_free_prob=0.52, consensus_prob=0.58)
        assert edge == pytest.approx(11.54, rel=0.01)

    def test_negative_edge(self):
        from src.services.odds_calculator import calculate_edge_ev

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
