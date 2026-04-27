"""
Bradley-Terry-Ford strength iteration, after Bethel (2005).

Probability team t beats team t' on a neutral site is
  P(t > t') = s_t / (s_t + s_t')

Strengths are estimated by iterative maximum likelihood over observed
games. Real-team strengths are normalized so their geometric mean is 1.
"""
from __future__ import annotations

import math
import warnings
from collections import defaultdict


ANCHOR = "__anchor__"


def bethel_strengths(
    teams: list[str],
    games: list[tuple[str, str]],
    prior_games: float = 1,
    max_iter: int = 2000,
    tol: float = 1e-10,
    initial: dict[str, float] | None = None,
    warn_non_convergence: bool = True,
) -> tuple[dict[str, float], int, bool]:
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
    prior_games : float, default 1
        For each team, add `prior_games` fictional wins and `prior_games`
        fictional losses against a strength-1 anchor. Prevents undefeated
        teams from diverging to infinity and winless teams from collapsing
        to zero, as Bethel discusses in §8. Fractional values are allowed
        and are useful for sensitivity analysis. Set to 0 for pure MLE
        (only safe when every team has at least one win and one loss
        within its connected component).
    max_iter : int, default 2000
        Hard cap on iterations. Comfortable headroom over observed
        convergence on the full FL high-school baseball graph (~612
        iterations at tol=1e-10).
    tol : float, default 1e-10
        Convergence tolerance on the max strength delta between iterations.
    initial : dict, optional
        Warm-start strengths. Useful for leave-one-out recomputations
        where one game is being excluded from a converged solution.
    warn_non_convergence : bool, default True
        Emit a warnings.warn when the iteration terminates at max_iter
        without reaching tol. Set False for leave-one-out sweeps where
        warnings would be noisy and the caller inspects `converged`.

    Returns
    -------
    (strengths, iterations, converged) : tuple[dict[str, float], int, bool]
        Strength per team, the iteration count at termination, and a
        boolean indicating whether `tol` was actually reached. When
        `converged` is False, the strengths are the last iterate and
        should not be trusted beyond whatever delta remains.
    """
    wins: dict[str, float] = defaultdict(float)
    opps: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for w, l in games:
        wins[w] += 1
        opps[w].append((l, 1.0))
        opps[l].append((w, 1.0))

    if prior_games > 0:
        for t in teams:
            wins[t] += prior_games
            # One fictitious W and one fictitious L vs the anchor, each
            # weighted by `prior_games`. Supports fractional priors.
            opps[t].append((ANCHOR, 2.0 * prior_games))

    s_anchor = 1.0
    s: dict[str, float] = dict(initial) if initial else {t: 1.0 for t in teams}
    # Teams absent from `initial` get anchor strength.
    for t in teams:
        s.setdefault(t, 1.0)

    for iteration in range(1, max_iter + 1):
        s_new: dict[str, float] = {}
        for t in teams:
            denom = 0.0
            for o, w_go in opps[t]:
                s_o = s_anchor if o == ANCHOR else s[o]
                denom += w_go / (s[t] + s_o)
            s_new[t] = wins[t] / denom if denom > 0 else s[t]

        try:
            log_mean = sum(math.log(v) for v in s_new.values()) / len(teams)
        except ValueError as e:
            # Happens only when a strength has collapsed to 0 (or gone
            # negative from a numerical accident). With a strictly positive
            # Bayesian prior this is impossible; without one, winless teams
            # in disconnected components hit this. Surface it clearly.
            bad = [t for t, v in s_new.items() if v <= 0]
            raise ValueError(
                f"Bethel iteration produced non-positive strength for "
                f"{len(bad)} team(s) (example: {bad[0] if bad else '?'}). "
                f"This typically means prior_games=0 on a graph with "
                f"winless teams or disconnected components. Use "
                f"prior_games > 0 (Bethel §8)."
            ) from e
        scale = math.exp(log_mean)
        s_new = {t: v / scale for t, v in s_new.items()}

        converged = max(abs(s_new[t] - s[t]) for t in teams) < tol
        s = s_new
        if converged:
            return s, iteration, True

    if warn_non_convergence:
        warnings.warn(
            f"bethel_strengths did not converge within max_iter={max_iter} "
            f"at tol={tol:g}. Last iterate returned — treat strengths as "
            f"approximate. Increase max_iter or relax tol.",
            RuntimeWarning,
            stacklevel=2,
        )
    return s, max_iter, False
