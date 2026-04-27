"""
Predictive-accuracy validation harness.

Splits a games CSV at a date cutoff, trains each ranking method on games
strictly before the cutoff, and scores each method's probability
prediction against the actual outcomes of games from the cutoff onward.
"""
from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from .bethel import bethel_strengths
from .calibration import LogisticFit, fit_logistic
from .rpi import classical_rpi


@dataclass(frozen=True)
class Scores:
    accuracy: float
    log_loss: float
    brier: float


@dataclass(frozen=True)
class Interval:
    """A point estimate with a 2-sided percentile CI."""
    point: float
    low: float
    high: float

    def __str__(self) -> str:
        return f"{self.point:.4f} [{self.low:.4f}, {self.high:.4f}]"


@dataclass(frozen=True)
class ScoresCI:
    accuracy: Interval
    log_loss: Interval
    brier: Interval


@dataclass(frozen=True)
class PairwiseDiff:
    """
    Bootstrap paired comparison: method vs a baseline, on a loss metric.

    diff = loss(method) − loss(baseline). For log-loss and Brier score,
    **positive diff means the method is WORSE** (higher loss) than the
    baseline. Negative diff means the method beats the baseline.

    `p_baseline_at_least_as_good` is the fraction of bootstrap resamples
    where diff ≥ 0 — i.e. the baseline was at least as good as the
    method. When the baseline is the proposed winner (e.g. Bethel), a
    value near 1.0 is evidence that Bethel reliably matches or beats
    the method.
    """
    mean_diff: float
    low: float
    high: float
    p_baseline_at_least_as_good: float


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


def _rpi_or_none(rpi_data: dict[str, dict[str, float]], team: str) -> float | None:
    """RPI for a team, or None if the team has no training data."""
    r = rpi_data.get(team, {"rpi": 0.0})["rpi"]
    return r if r > 0 else None


def predict_rpi(rpi_data: dict[str, dict[str, float]], home: str, away: str) -> float:
    """Raw, uncalibrated RPI probability — kept for contrast only."""
    r_h = _rpi_or_none(rpi_data, home)
    r_a = _rpi_or_none(rpi_data, away)
    if r_h is None or r_a is None:
        return 0.5
    return r_h / (r_h + r_a)


def _rpi_log_ratio(rpi_data: dict[str, dict[str, float]], home: str, away: str) -> float:
    """Log-odds feature for logistic calibration: log(rpi_home / rpi_away)."""
    eps = 1e-6
    r_h = max(rpi_data.get(home, {"rpi": 0.0})["rpi"], eps)
    r_a = max(rpi_data.get(away, {"rpi": 0.0})["rpi"], eps)
    return math.log(r_h / r_a)


def fit_rpi_calibration(
    rpi_data: dict[str, dict[str, float]],
    train_games: list[tuple[str, str]],
) -> LogisticFit:
    """
    Fit a 2-parameter logistic mapping log(rpi_winner / rpi_loser) → P(winner wins).

    Training uses the train games themselves: feature is the log-ratio of
    each game's (home, away) RPI values, label is 1 if home won.
    Since train_games are (winner, loser) tuples, we synthesize both
    directions — (w, l) as label=1 and (l, w) as label=0 — to avoid an
    all-ones training set that would blow up β.
    """
    xs: list[float] = []
    ys: list[int] = []
    for w, l in train_games:
        xs.append(_rpi_log_ratio(rpi_data, w, l))
        ys.append(1)
        xs.append(_rpi_log_ratio(rpi_data, l, w))
        ys.append(0)
    return fit_logistic(xs, ys)


def predict_rpi_calibrated(
    rpi_data: dict[str, dict[str, float]],
    calibration: LogisticFit,
    home: str,
    away: str,
) -> float:
    # If either team has no training data, neither the raw ratio nor the
    # calibrated map is meaningful — fall back to the no-information prior.
    if _rpi_or_none(rpi_data, home) is None or _rpi_or_none(rpi_data, away) is None:
        return 0.5
    return calibration.predict(_rpi_log_ratio(rpi_data, home, away))


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


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interp percentile. q ∈ [0, 1]."""
    n = len(sorted_values)
    if n == 0:
        return float("nan")
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    w = pos - lo
    return sorted_values[lo] * (1 - w) + sorted_values[hi] * w


def bootstrap_scores(
    preds_by_method: dict[str, list[float]],
    actuals: list[int],
    *,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
    baseline: str | None = "bethel",
) -> tuple[dict[str, ScoresCI], dict[str, dict[str, PairwiseDiff]]]:
    """
    Paired bootstrap over test games. For each of `n_boot` resamples, we
    draw the SAME indices for every method so paired comparisons are valid.

    Returns
    -------
    score_cis : per-method Scores with (point, low, high) for each metric.
    pairwise  : {method: {metric: PairwiseDiff}} comparing each method
                against `baseline` on log-loss and brier. Positive
                mean_diff means `method` has lower loss than baseline
                (i.e. method is better). `p_gte_zero` is the one-sided
                bootstrap probability that baseline ≥ method on this
                metric; small values mean the method outperforms baseline.
                Empty when baseline is None.
    """
    n = len(actuals)
    if n == 0:
        raise ValueError("empty test set")

    rng = random.Random(seed)

    # Point estimates on the full test set.
    points = {m: score(p, actuals) for m, p in preds_by_method.items()}

    acc_samples: dict[str, list[float]] = {m: [] for m in preds_by_method}
    ll_samples: dict[str, list[float]] = {m: [] for m in preds_by_method}
    br_samples: dict[str, list[float]] = {m: [] for m in preds_by_method}

    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        ya = [actuals[i] for i in idx]
        for m, p in preds_by_method.items():
            pa = [p[i] for i in idx]
            s = score(pa, ya)
            acc_samples[m].append(s.accuracy)
            ll_samples[m].append(s.log_loss)
            br_samples[m].append(s.brier)

    q_lo, q_hi = alpha / 2, 1 - alpha / 2
    cis: dict[str, ScoresCI] = {}
    for m in preds_by_method:
        accs = sorted(acc_samples[m])
        lls = sorted(ll_samples[m])
        brs = sorted(br_samples[m])
        cis[m] = ScoresCI(
            accuracy=Interval(points[m].accuracy, _percentile(accs, q_lo), _percentile(accs, q_hi)),
            log_loss=Interval(points[m].log_loss, _percentile(lls, q_lo), _percentile(lls, q_hi)),
            brier=Interval(points[m].brier, _percentile(brs, q_lo), _percentile(brs, q_hi)),
        )

    pairwise: dict[str, dict[str, PairwiseDiff]] = {}
    if baseline is not None and baseline in preds_by_method:
        for m in preds_by_method:
            if m == baseline:
                continue
            diff_ll = [ll_samples[m][i] - ll_samples[baseline][i] for i in range(n_boot)]
            diff_br = [br_samples[m][i] - br_samples[baseline][i] for i in range(n_boot)]
            sorted_ll = sorted(diff_ll)
            sorted_br = sorted(diff_br)
            pairwise[m] = {
                "log_loss": PairwiseDiff(
                    mean_diff=sum(diff_ll) / n_boot,
                    low=_percentile(sorted_ll, q_lo),
                    high=_percentile(sorted_ll, q_hi),
                    p_baseline_at_least_as_good=sum(1 for d in diff_ll if d >= 0) / n_boot,
                ),
                "brier": PairwiseDiff(
                    mean_diff=sum(diff_br) / n_boot,
                    low=_percentile(sorted_br, q_lo),
                    high=_percentile(sorted_br, q_hi),
                    p_baseline_at_least_as_good=sum(1 for d in diff_br if d >= 0) / n_boot,
                ),
            }

    return cis, pairwise


def validate(path: Path | str, cutoff: str) -> dict[str, Scores]:
    """Run the full validation sweep and return scores keyed by method name."""
    teams, train, test, record_pre = load_and_split(path, cutoff)

    strengths, _, _ = bethel_strengths(teams, train)
    rpi_data = classical_rpi(teams, train)
    rpi_cal = fit_rpi_calibration(rpi_data, train)

    actuals = [y for _, _, y in test]
    preds = {
        "bethel": [predict_bethel(strengths, h, a) for h, a, _ in test],
        "rpi_raw": [predict_rpi(rpi_data, h, a) for h, a, _ in test],
        "rpi_cal": [predict_rpi_calibrated(rpi_data, rpi_cal, h, a) for h, a, _ in test],
        "wp": [predict_smoothed_wp(record_pre, h, a) for h, a, _ in test],
        "coin": [0.5 for _ in test],
    }
    return {name: score(p, actuals) for name, p in preds.items()}


def validate_with_ci(
    path: Path | str,
    cutoff: str,
    *,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[dict[str, ScoresCI], dict[str, dict[str, PairwiseDiff]]]:
    """Run validation and report bootstrap CIs + paired comparisons vs Bethel."""
    teams, train, test, record_pre = load_and_split(path, cutoff)
    strengths, _, _ = bethel_strengths(teams, train)
    rpi_data = classical_rpi(teams, train)
    rpi_cal = fit_rpi_calibration(rpi_data, train)
    actuals = [y for _, _, y in test]
    preds = {
        "bethel": [predict_bethel(strengths, h, a) for h, a, _ in test],
        "rpi_raw": [predict_rpi(rpi_data, h, a) for h, a, _ in test],
        "rpi_cal": [predict_rpi_calibrated(rpi_data, rpi_cal, h, a) for h, a, _ in test],
        "wp": [predict_smoothed_wp(record_pre, h, a) for h, a, _ in test],
        "coin": [0.5 for _ in test],
    }
    return bootstrap_scores(
        preds, actuals, n_boot=n_boot, alpha=alpha, seed=seed, baseline="bethel"
    )
