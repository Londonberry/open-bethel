"""
Phase 0 validation harness.

Splits the game list at a date cutoff. Trains each ranking method on games
before the cutoff, then scores each method's predicted win probabilities
against the actual outcomes of games from the cutoff onward.

Metrics reported for every method:
  accuracy:  fraction of test games where the favored team won
  log-loss:  binary cross-entropy on P(home wins)
  brier:     mean squared error on P(home wins)

Methods compared:
  bethel:    Bradley-Terry-Ford — P(A beats B) = s_A / (s_A + s_B)
  rpi:       classical RPI proxy — P(A beats B) = rpi_A / (rpi_A + rpi_B)
  wp:        Laplace-smoothed win-percentage Bradley-Terry proxy
  coin:      flat P = 0.5

No method uses home-field information; the comparison is method-vs-method
with the home/away channel deliberately excluded (Bethel-paper §8 notes
home/away as future work).

With a small held-out set, differences under ~0.02 are not statistically
meaningful — this harness is a scaffolding for the real experiment, not a
real experiment yet.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from phase0 import bethel_strengths, classical_rpi  # noqa: E402

DEFAULT_CSV = Path(__file__).parent / "games-district-3-2a-2026.csv"
DEFAULT_CUTOFF = "2026-04-01"


# ---------------------------------------------------------------------------
# Data split
# ---------------------------------------------------------------------------

def load_and_split(
    path: Path,
    cutoff: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str, int]], dict[str, dict[str, int]]]:
    """
    Returns:
      teams         — sorted list of every team seen in the file
      train_games   — list of (winner, loser) for games strictly before cutoff
      test_games    — list of (home, away, home_won) for games from cutoff onward
      record_pre    — per-team wins/games on the train set, for the wp baseline
    """
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


# ---------------------------------------------------------------------------
# Predictors
# ---------------------------------------------------------------------------

def predict_bethel(strengths: dict[str, float], home: str, away: str) -> float:
    s_h = strengths.get(home, 1.0)
    s_a = strengths.get(away, 1.0)
    return s_h / (s_h + s_a)


def predict_rpi(rpi_data: dict[str, dict[str, float]], home: str, away: str) -> float:
    r_h = rpi_data.get(home, {"rpi": 0.0})["rpi"]
    r_a = rpi_data.get(away, {"rpi": 0.0})["rpi"]
    total = r_h + r_a
    return r_h / total if total > 0 else 0.5


def predict_wp(record: dict[str, dict[str, int]], home: str, away: str) -> float:
    """Laplace-smoothed winning % (+1 W, +1 L) to avoid 0/0 blow-ups."""
    def smoothed(t: str) -> float:
        r = record.get(t, {"w": 0, "g": 0})
        return (r["w"] + 1) / (r["g"] + 2)
    h = smoothed(home)
    a = smoothed(away)
    return h / (h + a)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score(preds: list[float], actuals: list[int]) -> tuple[float, float, float]:
    n = len(preds)
    if n == 0:
        return (float("nan"),) * 3  # type: ignore[return-value]
    correct = sum(1 for p, y in zip(preds, actuals) if (p >= 0.5) == (y == 1))
    eps = 1e-12
    log_loss = -sum(
        y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
        for p, y in zip(preds, actuals)
    ) / n
    brier = sum((p - y) ** 2 for p, y in zip(preds, actuals)) / n
    return correct / n, log_loss, brier


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(csv_path: Path, cutoff: str) -> None:
    teams, train, test, record_pre = load_and_split(csv_path, cutoff)
    print(f"Train: {len(train)} games strictly before {cutoff}")
    print(f"Test:  {len(test)} games from {cutoff} onward")
    print(f"Teams: {len(teams)} in the combined graph")
    print()

    strengths, iters = bethel_strengths(teams, train)
    rpi_data = classical_rpi(teams, train)

    preds = {
        "bethel": [predict_bethel(strengths, h, a) for h, a, _ in test],
        "rpi":    [predict_rpi(rpi_data, h, a) for h, a, _ in test],
        "wp":     [predict_wp(record_pre, h, a) for h, a, _ in test],
        "coin":   [0.5 for _ in test],
    }
    actuals = [y for _, _, y in test]

    print("=" * 56)
    print(f"{'method':<20}{'accuracy':>10}{'log-loss':>12}{'brier':>10}")
    print("-" * 56)
    for name, p in preds.items():
        acc, ll, br = score(p, actuals)
        print(f"{name:<20}{acc:>10.3f}{ll:>12.4f}{br:>10.4f}")
    print("=" * 56)

    baseline_ll = score(preds["coin"], actuals)[1]
    print()
    print("Improvement over 50/50 coin baseline (log-loss reduction):")
    for name in ("bethel", "rpi", "wp"):
        _, ll, _ = score(preds[name], actuals)
        delta = baseline_ll - ll
        pct = (delta / baseline_ll) * 100 if baseline_ll > 0 else 0
        print(f"  {name:<12} {delta:+.4f}  ({pct:+.1f}%)")

    n_test = len(test)
    if n_test < 50:
        print()
        print(f"Note: only {n_test} held-out games — differences under ~0.02 are noise.")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    cutoff = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CUTOFF
    main(path, cutoff)
