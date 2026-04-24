"""Classical Rating Percentage Index."""
from __future__ import annotations

from collections import defaultdict


def classical_rpi(
    teams: list[str],
    games: list[tuple[str, str]],
) -> dict[str, dict[str, float]]:
    """
    Compute classical RPI = 0.25 * WP + 0.50 * OWP + 0.25 * OOWP.

    OWP(t):  average of each opponent's WP, with games against t removed.
    OOWP(t): average of each opponent's OWP.

    Teams with zero games receive 0.0 in every component.
    """
    wins: dict[str, int] = defaultdict(int)
    losses: dict[str, int] = defaultdict(int)
    opps: dict[str, list[str]] = defaultdict(list)
    for w, l in games:
        wins[w] += 1
        losses[l] += 1
        opps[w].append(l)
        opps[l].append(w)

    def wp_excluding(team: str, excluded: str) -> float:
        w = sum(1 for (a, b) in games if a == team and b != excluded)
        l = sum(1 for (a, b) in games if b == team and a != excluded)
        g = w + l
        return w / g if g > 0 else 0.0

    wp = {
        t: wins[t] / (wins[t] + losses[t]) if (wins[t] + losses[t]) else 0.0
        for t in teams
    }
    owp = {
        t: (sum(wp_excluding(o, t) for o in opps[t]) / len(opps[t])) if opps[t] else 0.0
        for t in teams
    }
    oowp = {
        t: (sum(owp[o] for o in opps[t]) / len(opps[t])) if opps[t] else 0.0
        for t in teams
    }

    return {
        t: {
            "wp": wp[t],
            "owp": owp[t],
            "oowp": oowp[t],
            "rpi": 0.25 * wp[t] + 0.50 * owp[t] + 0.25 * oowp[t],
        }
        for t in teams
    }
