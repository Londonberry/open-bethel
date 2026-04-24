"""
Predictive-accuracy validation harness.

Splits a games CSV at a date cutoff, trains each ranking method on games
strictly before the cutoff, and scores each method's probability
prediction against the actual outcomes of games from the cutoff onward.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from .bethel import bethel_strengths
from .rpi import classical_rpi


@dataclass(frozen=True)
class Scores:
    accuracy: float
    log_loss: float
    brier: float


def load_and_split(
    path: Path | str,
    cutoff: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str, int]], dict[str, dict[str, int]]]:
    """
    Partition a games CSV at `cutoff` (inclusive of cutoff = test set).

    Returns
    -------
    teams          — sorted list of every team in the file
    train_games    — list of (winner, loser) for games strictly before cutoff
    test_games     — list of (home, away, home_won) for games from cutoff on
    record_pre     — per-team wins/games on the train set, for the wp baseline
    """
    path = Path(path)
    train_games: list[tuple[str, str]] = []
    test_games: list[tuple[str, str, int]] = []
    teams: set[str] = set()
    record_pre: dict[str, dict[str, int]] = {}

    with path.open() as f:
        for row in csv.DictReader(f):
            home = row["home_team"].strip()
            away = row["away_team"].strip()
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            teams.update((home, away))
            if hs == as_:
                continue
            if row["date"] < cutoff:
                winner, loser = (home, away) if hs > as_ else (away, home)
                train_games.append((winner, loser))
                record_pre.setdefault(winner, {"w": 0, "g": 0})
                record_pre.setdefault(loser, {"w": 0, "g": 0})
                record_pre[winner]["w"] += 1
                record_pre[winner]["g"] += 1
                record_pre[loser]["g"] += 1
            else:
                test_games.append((home, away, 1 if hs > as_ else 0))

    return sorted(teams), train_games, test_games, record_pre


def predict_bethel(strengths: dict[str, float], home: str, away: str) -> float:
    s_h = strengths.get(home, 1.0)
    s_a = strengths.get(away, 1.0)
    return s_h / (s_h + s_a)


def predict_rpi(rpi_data: dict[str, dict[str, float]], home: str, away: str) -> float:
    r_h = rpi_data.get(home, {"rpi": 0.0})["rpi"]
    r_a = rpi_data.get(away, {"rpi": 0.0})["rpi"]
    total = r_h + r_a
    return r_h / total if total > 0 else 0.5


def predict_smoothed_wp(record: dict[str, dict[str, int]], home: str, away: str) -> float:
    """Laplace-smoothed winning percentage (+1 W, +1 L) Bradley-Terry proxy."""
    def smoothed(t: str) -> float:
        r = record.get(t, {"w": 0, "g": 0})
        return (r["w"] + 1) / (r["g"] + 2)

    h = smoothed(home)
    a = smoothed(away)
    return h / (h + a)


def score(preds: list[float], actuals: list[int]) -> Scores:
    n = len(preds)
    if n == 0:
        return Scores(float("nan"), float("nan"), float("nan"))
    correct = sum(1 for p, y in zip(preds, actuals) if (p >= 0.5) == (y == 1))
    eps = 1e-12
    log_loss = -sum(
        y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
        for p, y in zip(preds, actuals)
    ) / n
    brier = sum((p - y) ** 2 for p, y in zip(preds, actuals)) / n
    return Scores(correct / n, log_loss, brier)


def validate(path: Path | str, cutoff: str) -> dict[str, Scores]:
    """Run the full validation sweep and return scores keyed by method name."""
    teams, train, test, record_pre = load_and_split(path, cutoff)

    strengths, _ = bethel_strengths(teams, train)
    rpi_data = classical_rpi(teams, train)

    actuals = [y for _, _, y in test]
    preds = {
        "bethel": [predict_bethel(strengths, h, a) for h, a, _ in test],
        "rpi": [predict_rpi(rpi_data, h, a) for h, a, _ in test],
        "wp": [predict_smoothed_wp(record_pre, h, a) for h, a, _ in test],
        "coin": [0.5 for _ in test],
    }
    return {name: score(p, actuals) for name, p in preds.items()}
