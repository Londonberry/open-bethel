"""
Sensitivity of Bethel rankings to the Bayesian prior strength.

Bethel's paper (§8) describes the prior qualitatively but does not
prescribe a specific value. open-bethel defaults to `prior_games=1`
(one fictitious W + one fictitious L per team vs a strength-1 anchor).
This script sweeps that parameter and reports how the ranking reshuffles.

Outputs, relative to the reference ranking (prior_games=1):
  - rho    : Spearman rank correlation over all ranked teams
  - top10  : number of teams in the top-10 that remain in the top-10
  - top25  : same, top-25
  - ΔlogS  : max |Δ log-strength| over all teams
  - iters  : iterations to converge at tol=1e-10

Usage:
  python scripts/prior_sensitivity.py phase0/games-fhsaa-fl-2026.csv
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from open_bethel.bethel import bethel_strengths  # noqa: E402
from open_bethel.io import load_games  # noqa: E402


# prior_games=0 is pure MLE. On graphs with winless teams or disconnected
# components (typical for HS sports), strengths collapse to 0 and the method
# fails — Bethel flags this in §8 and recommends the prior as the fix.
# Include 0 only on graphs known to be well-conditioned (e.g. the 1999 NFL).
PRIOR_VALUES = [0.25, 0.5, 1.0, 2.0, 4.0]
REFERENCE = 1.0


def spearman_rho(
    a: dict[str, float],
    b: dict[str, float],
) -> float:
    """Spearman rank correlation over teams present in both dicts."""
    common = [t for t in a if t in b]
    rank_a = _ranks([a[t] for t in common])
    rank_b = _ranks([b[t] for t in common])
    n = len(common)
    if n < 2:
        return float("nan")
    mean_a = sum(rank_a) / n
    mean_b = sum(rank_b) / n
    num = sum((ra - mean_a) * (rb - mean_b) for ra, rb in zip(rank_a, rank_b))
    var_a = math.sqrt(sum((ra - mean_a) ** 2 for ra in rank_a))
    var_b = math.sqrt(sum((rb - mean_b) ** 2 for rb in rank_b))
    return num / (var_a * var_b) if var_a > 0 and var_b > 0 else float("nan")


def _ranks(values: list[float]) -> list[float]:
    """Average-rank assignment (handles ties)."""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: -values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg
        i = j + 1
    return ranks


def top_n_overlap(a: dict[str, float], b: dict[str, float], n: int) -> int:
    top_a = set(sorted(a, key=lambda t: -a[t])[:n])
    top_b = set(sorted(b, key=lambda t: -b[t])[:n])
    return len(top_a & top_b)


def main(csv_path: Path) -> None:
    teams, games = load_games(csv_path)
    print(f"Dataset: {csv_path.name}  ({len(games)} games, {len(teams)} teams)")
    print()

    rankings: dict[float, dict[str, float]] = {}
    iters_by_prior: dict[float, int] = {}
    for pg in PRIOR_VALUES:
        s, iters, converged = bethel_strengths(
            teams, games, prior_games=pg, max_iter=5000, tol=1e-10
        )
        if not converged:
            print(f"  WARNING: prior_games={pg} did not converge in {iters} iters.")
        rankings[pg] = s
        iters_by_prior[pg] = iters

    ref = rankings[REFERENCE]
    print(f"Reference: prior_games={REFERENCE} (converged in {iters_by_prior[REFERENCE]} iters)")
    print()
    print(f"{'prior':>8}{'iters':>8}{'rho':>10}{'top10':>8}{'top25':>8}{'maxΔlogS':>12}")
    print("-" * 54)
    for pg in PRIOR_VALUES:
        s = rankings[pg]
        rho = spearman_rho(ref, s)
        t10 = top_n_overlap(ref, s, 10)
        t25 = top_n_overlap(ref, s, 25)
        max_dlog = max(abs(math.log(s[t]) - math.log(ref[t])) for t in teams)
        print(f"{pg:>8.2f}{iters_by_prior[pg]:>8}{rho:>10.4f}{t10:>8}/10{t25:>8}/25{max_dlog:>12.4f}")

    # Top-10 table under reference + what each alt prior puts in those positions.
    print()
    print("Top 10 under each prior:")
    for pg in PRIOR_VALUES:
        top10 = sorted(rankings[pg], key=lambda t: -rankings[pg][t])[:10]
        label = f"  prior={pg:.2f}:"
        print(label, ", ".join(top10[:5]))
        print(" " * len(label), ", ".join(top10[5:]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/prior_sensitivity.py <games.csv>", file=sys.stderr)
        sys.exit(1)
    main(Path(sys.argv[1]))
