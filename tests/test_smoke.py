"""
Smoke tests — small, hand-checkable scenarios that pin down algorithm
behavior against facts Bethel's paper (or basic sanity) commits us to.
"""
from __future__ import annotations

import math

from open_bethel import bethel_strengths, classical_rpi, indirection, loo_contributions


def test_symmetric_two_teams_have_equal_strength() -> None:
    """Round-robin between two teams → equal strengths with the anchor prior."""
    teams = ["a", "b"]
    games = [("a", "b"), ("b", "a")]
    s, _, converged = bethel_strengths(teams, games)
    assert converged
    assert abs(s["a"] - s["b"]) < 1e-8
    assert abs(s["a"] * s["b"] - 1.0) < 1e-8  # geometric mean = 1


def test_undefeated_team_does_not_diverge() -> None:
    """With the Bayesian prior, an undefeated team has a bounded strength."""
    teams = ["a", "b", "c"]
    games = [("a", "b"), ("a", "c"), ("a", "b"), ("a", "c")]
    s, _, converged = bethel_strengths(teams, games)
    assert converged
    assert math.isfinite(s["a"])
    assert s["a"] > s["b"]
    assert s["a"] > s["c"]


def test_bethel_converges_quickly_on_small_input() -> None:
    teams = ["a", "b", "c", "d"]
    games = [
        ("a", "b"), ("a", "c"), ("a", "d"),
        ("b", "c"), ("b", "d"),
        ("c", "d"),
    ]
    _, iters, converged = bethel_strengths(teams, games, tol=1e-10)
    assert converged
    assert iters < 100


def test_bethel_flags_non_convergence() -> None:
    """A too-small max_iter must return converged=False rather than lie."""
    import warnings
    teams = ["a", "b", "c", "d"]
    games = [
        ("a", "b"), ("a", "c"), ("a", "d"),
        ("b", "c"), ("b", "d"),
        ("c", "d"),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, iters, converged = bethel_strengths(
            teams, games, max_iter=2, tol=1e-10
        )
    assert iters == 2
    assert converged is False


def test_rpi_components_sum_correctly() -> None:
    teams = ["a", "b", "c"]
    games = [("a", "b"), ("a", "c"), ("b", "c")]
    r = classical_rpi(teams, games)
    for t in teams:
        expected = 0.25 * r[t]["wp"] + 0.50 * r[t]["owp"] + 0.25 * r[t]["oowp"]
        assert abs(r[t]["rpi"] - expected) < 1e-12


def test_indirection_finds_common_opponent() -> None:
    teams = ["a", "b", "c"]
    games = [("a", "c"), ("b", "c")]  # a and b both played c; never each other
    assert indirection(teams, games, "a", "c") == 0
    assert indirection(teams, games, "a", "b") == 1


def test_indirection_returns_none_when_disconnected() -> None:
    teams = ["a", "b", "c", "d"]
    games = [("a", "b"), ("c", "d")]
    assert indirection(teams, games, "a", "c") is None


def test_loo_contribution_for_win_is_positive() -> None:
    """Removing a game a team won should reduce their strength → delta > 0."""
    teams = ["a", "b", "c", "d"]
    games = [("a", "b"), ("a", "c"), ("a", "d"), ("b", "c"), ("d", "b")]
    contribs = loo_contributions(teams, games, "a")
    # All of a's games are wins. Each one's removal should reduce a's strength.
    for c in contribs:
        assert c.delta > 0, f"Win vs {c.loser} should give positive delta, got {c.delta}"


def test_loo_contribution_for_loss_is_negative() -> None:
    teams = ["a", "b", "c"]
    games = [("a", "b"), ("b", "a"), ("c", "b"), ("b", "c")]
    # b's wins/losses are balanced but one of b's losses to a:
    b_contribs = loo_contributions(teams, games, "b")
    # The game (a, b) — a beat b — is a loss for b; its removal should raise b's strength,
    # meaning its contribution (delta = with − without) is negative.
    loss_contrib = next(c for c in b_contribs if c.winner == "a" and c.loser == "b")
    assert loss_contrib.delta < 0


if __name__ == "__main__":
    import sys
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    sys.exit(1 if failed else 0)
