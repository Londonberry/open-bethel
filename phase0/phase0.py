"""
Phase 0 runner.

Reads a games CSV and produces:
  1. Bethel (Bradley-Terry-Ford) strengths with a Bayesian prior
  2. Classical RPI (0.25 * WP + 0.50 * OWP + 0.25 * OOWP)
  3. Pairwise connectivity diagnostic (level of indirection)
     among a set of focus teams

CSV input contract
------------------
Column names required: date, home_team, away_team, home_score, away_score
Optional: game_type
Team identifiers are free-form strings; the engine is identifier-agnostic.
Tied games are ignored (Bethel's model is undefined for ties).

This script is the v0 reference implementation. It is deliberately small
(< 200 lines, no external dependencies) so every line of the algorithm is
auditable on one screen. Future refactors will split this into a package.
"""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

DEFAULT_CSV = Path(__file__).parent / "games-district-3-2a-2026.csv"
FOCUS_TEAMS = (
    "bishop-snyder",
    "bolles",
    "episcopal",
    "providence",
    "trinity-christian",
)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_games(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (sorted team list, list of (winner, loser) tuples). Ties dropped."""
    games: list[tuple[str, str]] = []
    teams: set[str] = set()
    with path.open() as f:
        for row in csv.DictReader(f):
            home = row["home_team"].strip()
            away = row["away_team"].strip()
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            teams.update((home, away))
            if hs == as_:
                continue
            winner, loser = (home, away) if hs > as_ else (away, home)
            games.append((winner, loser))
    return sorted(teams), games


# ---------------------------------------------------------------------------
# Bethel / Bradley-Terry-Ford iteration
# ---------------------------------------------------------------------------

def bethel_strengths(
    teams: list[str],
    games: list[tuple[str, str]],
    prior_games: int = 1,
    max_iter: int = 500,
    tol: float = 1e-10,
) -> tuple[dict[str, float], int]:
    """
    Iterative MLE for Bradley-Terry-Ford strengths.

    Probability team t beats t' = s_t / (s_t + s_t').

    Bayesian prior: each team plays `prior_games` fictional wins and
    `prior_games` fictional losses against an anchor team of strength 1.
    This keeps undefeated teams from diverging to infinity and winless
    teams from collapsing to zero, as Bethel discusses in §8.

    Real-team strengths are normalized so the geometric mean = 1.
    """
    anchor = "__anchor__"
    wins: dict[str, float] = defaultdict(float)
    opps: dict[str, list[str]] = defaultdict(list)

    for w, l in games:
        wins[w] += 1
        opps[w].append(l)
        opps[l].append(w)

    for t in teams:
        wins[t] += prior_games
        opps[t].extend([anchor] * (2 * prior_games))

    s_anchor = 1.0
    s: dict[str, float] = {t: 1.0 for t in teams}

    for iteration in range(1, max_iter + 1):
        s_new: dict[str, float] = {}
        for t in teams:
            denom = 0.0
            for o in opps[t]:
                s_o = s_anchor if o == anchor else s[o]
                denom += 1.0 / (s[t] + s_o)
            s_new[t] = wins[t] / denom if denom > 0 else s[t]

        log_mean = sum(math.log(v) for v in s_new.values()) / len(teams)
        scale = math.exp(log_mean)
        s_new = {t: v / scale for t, v in s_new.items()}

        if max(abs(s_new[t] - s[t]) for t in teams) < tol:
            return s_new, iteration
        s = s_new

    return s, max_iter


# ---------------------------------------------------------------------------
# Classical RPI
# ---------------------------------------------------------------------------

def classical_rpi(
    teams: list[str],
    games: list[tuple[str, str]],
) -> dict[str, dict[str, float]]:
    """
    RPI = 0.25 * WP + 0.50 * OWP + 0.25 * OOWP

    OWP(t):  average of opp.WP computed with games vs t removed.
    OOWP(t): average of opp.OWP.
    Teams with zero games get RPI = 0 (no information).
    """
    wins = defaultdict(int)
    losses = defaultdict(int)
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

    wp = {t: wins[t] / (wins[t] + losses[t]) if wins[t] + losses[t] else 0.0 for t in teams}
    owp = {t: (sum(wp_excluding(o, t) for o in opps[t]) / len(opps[t])) if opps[t] else 0.0 for t in teams}
    oowp = {t: (sum(owp[o] for o in opps[t]) / len(opps[t])) if opps[t] else 0.0 for t in teams}

    return {
        t: {
            "wp": wp[t],
            "owp": owp[t],
            "oowp": oowp[t],
            "rpi": 0.25 * wp[t] + 0.50 * owp[t] + 0.25 * oowp[t],
        }
        for t in teams
    }


# ---------------------------------------------------------------------------
# Connectivity diagnostic
# ---------------------------------------------------------------------------

def indirection(
    teams: list[str],
    games: list[tuple[str, str]],
    a: str,
    b: str,
) -> int | None:
    """
    Shortest path length in the opponent graph between a and b, where
    an edge exists between any two teams that played at least one game.

    0  = direct game played
    1  = share a common opponent
    2+ = opponent-of-opponent-of-... chain
    None = no chain exists (teams live in disconnected graph components)
    """
    if a == b:
        return 0
    adj: dict[str, set[str]] = defaultdict(set)
    for w, l in games:
        adj[w].add(l)
        adj[l].add(w)
    if b in adj[a]:
        return 0
    visited = {a}
    frontier = deque([(a, 0)])
    while frontier:
        node, depth = frontier.popleft()
        for nxt in adj[node]:
            if nxt == b:
                return depth
            if nxt not in visited:
                visited.add(nxt)
                frontier.append((nxt, depth + 1))
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(csv_path: Path) -> None:
    teams, games = load_games(csv_path)
    print(f"Loaded {len(games)} games across {len(teams)} teams from {csv_path.name}\n")

    strengths, iters = bethel_strengths(teams, games)
    rpi = classical_rpi(teams, games)

    focus_rows = []
    for t in FOCUS_TEAMS:
        w = sum(1 for (a, _) in games if a == t)
        l = sum(1 for (_, b) in games if b == t)
        focus_rows.append((t, w, l, strengths.get(t, float("nan")), rpi[t]["rpi"], rpi[t]["wp"]))

    by_bethel = sorted(focus_rows, key=lambda r: -r[3])
    print("=" * 70)
    print(f"Bethel strengths  (converged in {iters} iterations)")
    print("=" * 70)
    print(f"{'rank':<5}{'team':<22}{'W-L':<8}{'strength':>10}{'rpi':>10}{'wp':>8}")
    for rank, (t, w, l, s, r, wp_) in enumerate(by_bethel, 1):
        print(f"{rank:<5}{t:<22}{f'{w}-{l}':<8}{s:>10.4f}{r:>10.4f}{wp_:>8.3f}")

    by_rpi = sorted(focus_rows, key=lambda r: -r[4])
    print()
    print("=" * 70)
    print("Classical RPI  (0.25·WP + 0.50·OWP + 0.25·OOWP)")
    print("=" * 70)
    print(f"{'rank':<5}{'team':<22}{'W-L':<8}{'rpi':>10}{'strength':>10}")
    for rank, (t, w, l, s, r, _) in enumerate(by_rpi, 1):
        print(f"{rank:<5}{t:<22}{f'{w}-{l}':<8}{r:>10.4f}{s:>10.4f}")

    print()
    print("=" * 70)
    print("Pairwise connectivity  (0 = played direct, 1 = common opp, ...)")
    print("=" * 70)
    for i, a in enumerate(FOCUS_TEAMS):
        for b in FOCUS_TEAMS[i + 1:]:
            d = indirection(teams, games, a, b)
            mark = "DIRECT" if d == 0 else (f"indirect (+{d})" if d is not None else "DISCONNECTED")
            print(f"  {a:<22} vs {b:<22} {mark}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    main(path)
