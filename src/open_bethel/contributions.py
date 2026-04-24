"""
Per-game contribution analysis via leave-one-out strength recomputation.

For each game we care about, we rebuild Bethel strengths from the rest of
the graph and report how much the team's strength changed once that game
was included. The sign tells the obvious story — positive means the game
raised the team's strength, negative means it lowered it — and the
magnitude tells the less-obvious story: against what calibre of opponent
did that outcome actually move the number?

This is the math behind the "how did each game help or hurt my ranking?"
feature.
"""
from __future__ import annotations

from dataclasses import dataclass

from .bethel import bethel_strengths


@dataclass(frozen=True)
class Contribution:
    """How much including one game changed one team's strength."""
    team: str
    winner: str
    loser: str
    game_index: int
    strength_with: float
    strength_without: float

    @property
    def delta(self) -> float:
        return self.strength_with - self.strength_without


def loo_contributions(
    teams: list[str],
    games: list[tuple[str, str]],
    target_team: str,
    *,
    baseline_strengths: dict[str, float] | None = None,
    max_iter: int = 200,
    tol: float = 1e-8,
) -> list[Contribution]:
    """
    Compute the leave-one-out contribution of each of `target_team`'s games
    to `target_team`'s Bethel strength.

    Uses the full-graph strengths as a warm start for the LOO recomputations
    so each excluded game converges quickly. On typical baseball-scale
    inputs (hundreds of teams, thousands of games) this is tractable to
    run for one team in seconds.

    Parameters
    ----------
    baseline_strengths : dict, optional
        Pre-computed full-graph strengths. If omitted, the function
        computes them. Passing this in avoids redundant work when calling
        `loo_contributions` for multiple teams.

    Returns a list of `Contribution`s in the same order as the team's
    games appeared in `games`.
    """
    if baseline_strengths is None:
        baseline_strengths, _, _ = bethel_strengths(teams, games, max_iter=max_iter, tol=tol)

    s_with = baseline_strengths[target_team]
    results: list[Contribution] = []

    for i, (w, l) in enumerate(games):
        if w != target_team and l != target_team:
            continue
        without_games = games[:i] + games[i + 1 :]
        s_without, _, _ = bethel_strengths(
            teams,
            without_games,
            max_iter=max_iter,
            tol=tol,
            initial=baseline_strengths,
            warn_non_convergence=False,
        )
        results.append(
            Contribution(
                team=target_team,
                winner=w,
                loser=l,
                game_index=i,
                strength_with=s_with,
                strength_without=s_without[target_team],
            )
        )

    return results
