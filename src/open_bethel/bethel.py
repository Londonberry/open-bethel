"""
Bradley-Terry-Ford strength iteration, after Bethel (2005).

Probability team t beats team t' on a neutral site is
  P(t > t') = s_t / (s_t + s_t')

Strengths are estimated by iterative maximum likelihood over observed
games. Real-team strengths are normalized so their geometric mean is 1.
"""
from __future__ import annotations

import math
from collections import defaultdict


ANCHOR = "__anchor__"


def bethel_strengths(
    teams: list[str],
    games: list[tuple[str, str]],
    prior_games: int = 1,
    max_iter: int = 500,
    tol: float = 1e-10,
    initial: dict[str, float] | None = None,
) -> tuple[dict[str, float], int]:
    """
    Iterative MLE for Bradley-Terry-Ford strengths with a Bayesian prior.

    Parameters
    ----------
    teams : list[str]
        Every team that should receive a strength estimate. Teams with no
        games still appear in the output at the anchor strength.
    games : list[tuple[str, str]]
        Winners and losers. Each tuple is (winner, loser). Ties must be
        excluded upstream.
    prior_games : int, default 1
        For each team, add `prior_games` fictional wins and `prior_games`
        fictional losses against a strength-1 anchor. Prevents undefeated
        teams from diverging to infinity and winless teams from collapsing
        to zero, as Bethel discusses in §8.
    max_iter : int, default 500
        Hard cap on iterations. On typical baseball-scale graphs the method
        converges well before this.
    tol : float, default 1e-10
        Convergence tolerance on the max strength delta between iterations.
    initial : dict, optional
        Warm-start strengths. Useful for leave-one-out recomputations
        where one game is being excluded from a converged solution.

    Returns
    -------
    (strengths, iterations) : tuple[dict[str, float], int]
        Strength per team, and the iteration count at termination
        (equal to `max_iter` if convergence was not reached).
    """
    wins: dict[str, float] = defaultdict(float)
    opps: dict[str, list[str]] = defaultdict(list)

    for w, l in games:
        wins[w] += 1
        opps[w].append(l)
        opps[l].append(w)

    for t in teams:
        wins[t] += prior_games
        opps[t].extend([ANCHOR] * (2 * prior_games))

    s_anchor = 1.0
    s: dict[str, float] = dict(initial) if initial else {t: 1.0 for t in teams}
    # Teams absent from `initial` get anchor strength.
    for t in teams:
        s.setdefault(t, 1.0)

    for iteration in range(1, max_iter + 1):
        s_new: dict[str, float] = {}
        for t in teams:
            denom = 0.0
            for o in opps[t]:
                s_o = s_anchor if o == ANCHOR else s[o]
                denom += 1.0 / (s[t] + s_o)
            s_new[t] = wins[t] / denom if denom > 0 else s[t]

        log_mean = sum(math.log(v) for v in s_new.values()) / len(teams)
        scale = math.exp(log_mean)
        s_new = {t: v / scale for t, v in s_new.items()}

        if max(abs(s_new[t] - s[t]) for t in teams) < tol:
            return s_new, iteration
        s = s_new

    return s, max_iter
