"""
Regression test against Bethel (2005) Table 2 — the 1999 NFL final solution.

Bethel's paper publishes the converged Bradley-Terry-Ford strengths for all
31 NFL teams after the 1999 regular season (Table 2, p. 14). Our
implementation must reproduce those values exactly to 4 decimal places
given the actual 1999 schedule, or the math is wrong somewhere.

The 1999 NFL had no undefeated/winless teams and no ties, so the pure MLE
(prior_games=0) is well-defined — that's the configuration Bethel used in
the paper. With the Bayesian prior enabled (prior_games=1) we should NOT
expect an exact match, by design.

Fixture: tests/fixtures/nfl_1999.csv — all 248 regular-season games.
"""
from __future__ import annotations

from pathlib import Path

from open_bethel.bethel import bethel_strengths
from open_bethel.io import load_games

# Bethel 2005, Table 2 (p. 14), mapped onto pro-football-reference team codes.
# Strengths are normalized so Σ log(s_t) = 0 (geometric mean 1).
TABLE2 = {
    "IND": 6.9927, "JAX": 5.0117, "BUF": 3.8538, "TEN": 3.7348,
    "MIA": 2.5624, "TB":  2.2356, "NYJ": 2.1129, "STL": 2.0762,
    "WAS": 1.7842, "KC":  1.7660, "MIN": 1.7598, "OAK": 1.6575,
    "SEA": 1.6179, "NE":  1.5941, "DET": 1.2561, "SD":  1.2465,
    "GB":  1.0705, "DEN": 1.0331, "DAL": 1.0171, "NYG": 0.9479,
    "CHI": 0.7546, "BAL": 0.7478, "ARI": 0.5909, "PHI": 0.5693,
    "CAR": 0.4306, "PIT": 0.3533, "ATL": 0.2434, "CIN": 0.2023,
    "SF":  0.1591, "NO":  0.1062, "CLE": 0.0830,
}

FIXTURE = Path(__file__).parent / "fixtures" / "nfl_1999.csv"


def test_reproduces_bethel_1999_nfl_table_2() -> None:
    """Exact reproduction of Bethel's Table 2 strengths to 4 decimals."""
    teams, games = load_games(FIXTURE)
    assert len(games) == 248
    assert len(teams) == 31

    strengths, iters, converged = bethel_strengths(
        teams, games, prior_games=0, max_iter=5000, tol=1e-12
    )
    assert converged, f"failed to converge: stopped at iter {iters}"

    for team, expected in TABLE2.items():
        got = strengths[team]
        # Bethel reports 4 decimals. We require agreement to 5e-5, which is
        # the worst-case implied precision of his published values.
        assert abs(got - expected) < 5e-5, (
            f"{team}: got {got:.6f}, Bethel published {expected:.4f}"
        )


def test_1999_nfl_rank_order_matches_bethel() -> None:
    """Ranking order must match Bethel's exactly, all 31 positions."""
    teams, games = load_games(FIXTURE)
    strengths, _, converged = bethel_strengths(
        teams, games, prior_games=0, max_iter=5000, tol=1e-12
    )
    assert converged

    our_order = sorted(TABLE2, key=lambda t: -strengths[t])
    bethel_order = sorted(TABLE2, key=lambda t: -TABLE2[t])
    assert our_order == bethel_order


def test_1999_nfl_log_strengths_sum_to_zero() -> None:
    """Bethel's normalization: Σ log(s_t) = 0 over real teams."""
    import math
    teams, games = load_games(FIXTURE)
    strengths, _, converged = bethel_strengths(
        teams, games, prior_games=0, max_iter=5000, tol=1e-12
    )
    assert converged
    log_sum = sum(math.log(strengths[t]) for t in TABLE2)
    assert abs(log_sum) < 1e-8


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
