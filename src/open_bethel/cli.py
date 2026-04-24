"""Command-line entry points installed by pyproject.toml."""
from __future__ import annotations

import sys
from pathlib import Path

from .bethel import bethel_strengths
from .connectivity import indirection
from .io import load_games
from .rpi import classical_rpi
from .validation import validate


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

    strengths, iters = bethel_strengths(teams, games)
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
    print(f"Bethel strengths (converged in {iters} iterations)")
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
        print("usage: open-bethel-validate <games.csv> <YYYY-MM-DD cutoff>", file=sys.stderr)
        return 1
    csv_path, cutoff = args[0], args[1]
    scores = validate(csv_path, cutoff)

    print(f"cutoff={cutoff}")
    print(f"{'method':<12}{'accuracy':>10}{'log-loss':>12}{'brier':>10}")
    for name, s in scores.items():
        print(f"{name:<12}{s.accuracy:>10.3f}{s.log_loss:>12.4f}{s.brier:>10.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main_rank())
