"""Command-line entry points installed by pyproject.toml."""
from __future__ import annotations

import sys
from pathlib import Path

from .bethel import bethel_strengths
from .connectivity import indirection
from .diagnostics import home_field_advantage
from .io import load_games
from .rpi import classical_rpi
from .validation import validate, validate_with_ci


def _fmt_focus_row(rank: int, team: str, w: int, l: int, s: float, r: float, wp_: float) -> str:
    return f"{rank:<5}{team:<40}{f'{w}-{l}':<8}{s:>10.4f}{r:>10.4f}{wp_:>8.3f}"


def main_rank(argv: list[str] | None = None) -> int:
    """Rank a games CSV and print the focus-team table and connectivity diagnostic."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: open-bethel-rank <games.csv> [focus-team ...]", file=sys.stderr)
        return 1
    csv_path = Path(args[0])
    focus_teams = args[1:] if len(args) > 1 else []

    teams, games = load_games(csv_path)
    print(f"Loaded {len(games)} games across {len(teams)} teams from {csv_path.name}\n")

    strengths, iters, converged = bethel_strengths(teams, games)
    rpi = classical_rpi(teams, games)

    team_set = set(teams)
    present = [t for t in focus_teams if t in team_set] if focus_teams else sorted(teams, key=lambda t: -strengths[t])[:10]
    if focus_teams and not present:
        print("None of the requested focus teams are in the dataset.", file=sys.stderr)
        return 2

    rows = []
    for t in present:
        w = sum(1 for (a, _) in games if a == t)
        l = sum(1 for (_, b) in games if b == t)
        rows.append((t, w, l, strengths[t], rpi[t]["rpi"], rpi[t]["wp"]))

    by_bethel = sorted(rows, key=lambda r: -r[3])
    status = f"converged in {iters} iterations" if converged else f"DID NOT CONVERGE — stopped at max_iter={iters}"
    print(f"Bethel strengths ({status})")
    print(f"{'rank':<5}{'team':<40}{'W-L':<8}{'strength':>10}{'rpi':>10}{'wp':>8}")
    for rank, row in enumerate(by_bethel, 1):
        print(_fmt_focus_row(rank, *row))

    if focus_teams:
        print("\nPairwise connectivity (0 = direct, 1 = common opp, ...)")
        for i, a in enumerate(present):
            for b in present[i + 1 :]:
                d = indirection(teams, games, a, b)
                mark = "DIRECT" if d == 0 else (f"indirect (+{d})" if d is not None else "DISCONNECTED")
                print(f"  {a:<40} vs {b:<40} {mark}")

    return 0


def main_validate(argv: list[str] | None = None) -> int:
    """Run the train/test validation harness at a given date cutoff."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print(
            "usage: open-bethel-validate <games.csv> <YYYY-MM-DD cutoff> [n_boot]",
            file=sys.stderr,
        )
        return 1
    csv_path, cutoff = args[0], args[1]
    n_boot = int(args[2]) if len(args) > 2 else 1000

    cis, pairwise = validate_with_ci(csv_path, cutoff, n_boot=n_boot)

    print(f"cutoff={cutoff}   bootstrap n={n_boot}   95% percentile CIs")
    print()
    print(f"{'method':<10}{'accuracy':>22}{'log-loss':>24}{'brier':>24}")
    print("-" * 80)
    for name, ci in cis.items():
        print(
            f"{name:<10}"
            f"  {ci.accuracy.point:.3f} [{ci.accuracy.low:.3f},{ci.accuracy.high:.3f}]"
            f"  {ci.log_loss.point:.4f} [{ci.log_loss.low:.4f},{ci.log_loss.high:.4f}]"
            f"  {ci.brier.point:.4f} [{ci.brier.low:.4f},{ci.brier.high:.4f}]"
        )

    if pairwise:
        print()
        print("Paired bootstrap vs Bethel (positive Δ = method has HIGHER log-loss, i.e. Bethel wins)")
        print(f"{'method':<10}  {'Δ log-loss (method − bethel) [95% CI]':<42}  {'P(Bethel ≥ method)':>18}")
        print("-" * 78)
        for m, diffs in pairwise.items():
            ll = diffs["log_loss"]
            cell = f"{ll.mean_diff:+.4f} [{ll.low:+.4f}, {ll.high:+.4f}]"
            print(f"{m:<10}  {cell:<42}  {ll.p_baseline_at_least_as_good:>18.3f}")
    return 0


def main_diagnose(argv: list[str] | None = None) -> int:
    """Run dataset-level diagnostics (currently: home-field advantage)."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: open-bethel-diagnose <games.csv>", file=sys.stderr)
        return 1
    csv_path = Path(args[0])
    report = home_field_advantage(csv_path)
    print(report)
    p = report.home_win_rate
    if p != p:  # NaN
        return 0
    if report.ci_low > 0.5:
        print(
            f"  → 95% CI entirely above 0.5: statistically significant home-field effect."
        )
        print(
            "    Bethel's model excludes home/away (§3, §8). On this dataset the"
            " exclusion biases every ranking."
        )
    elif report.ci_high < 0.5:
        print(
            f"  → 95% CI entirely below 0.5: statistically significant ROAD-field effect."
        )
    else:
        print(
            f"  → 95% CI contains 0.5: no statistically significant home-field effect"
            " at n={}.".format(report.decided_games)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main_rank())
