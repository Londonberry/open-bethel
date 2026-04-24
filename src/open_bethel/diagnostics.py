"""
Dataset-level diagnostics that don't compute rankings but do surface
assumptions the ranking engine relies on.

Current diagnostics:
  - Home-field advantage: fraction of non-tie games won by the home team,
    with a Wilson-score 95% confidence interval. Bethel excludes home/away
    from the model (§3, §8); this diagnostic lets you verify whether that
    exclusion is defensible on your dataset or whether a systematic
    home-field effect is being ignored.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HomeFieldReport:
    total_games: int
    ties: int
    decided_games: int
    home_wins: int
    home_win_rate: float
    ci_low: float
    ci_high: float

    def __str__(self) -> str:
        return (
            f"Home-field advantage: {self.home_wins}/{self.decided_games} = "
            f"{self.home_win_rate:.4f}  95% CI [{self.ci_low:.4f}, {self.ci_high:.4f}]"
            f"  (ties excluded: {self.ties}, total games: {self.total_games})"
        )


def _wilson_ci(wins: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """
    Wilson score interval for a binomial proportion. More reliable than
    the normal approximation when p̂ is close to 0 or 1, and correct for
    small n. z=1.96 gives a 95% CI.
    """
    if n == 0:
        return (float("nan"), float("nan"))
    p = wins / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def home_field_advantage(path: Path | str) -> HomeFieldReport:
    """
    Measure the raw home-win rate on a games CSV.

    Input contract: CSV with columns date, home_team, away_team,
    home_score, away_score. Ties (equal scores) are counted but excluded
    from the rate calculation.
    """
    path = Path(path)
    total = 0
    ties = 0
    home_wins = 0
    decided = 0
    with path.open() as f:
        for row in csv.DictReader(f):
            total += 1
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            if hs == as_:
                ties += 1
                continue
            decided += 1
            if hs > as_:
                home_wins += 1

    rate = home_wins / decided if decided > 0 else float("nan")
    low, high = _wilson_ci(home_wins, decided)
    return HomeFieldReport(
        total_games=total,
        ties=ties,
        decided_games=decided,
        home_wins=home_wins,
        home_win_rate=rate,
        ci_low=low,
        ci_high=high,
    )
