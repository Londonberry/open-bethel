"""
Per-game contribution demo.

For each of a focus team's games, computes how much including that game
in the graph changed the team's Bethel strength. Output is sorted most-
positive (the game that helped the most) to most-negative (the game that
hurt the most), so a user asking "which win mattered the most?" or
"which loss hurt the most?" gets a principled answer.

This is the feature described in the brief as
  "You can see how each game helped or hurt your rankings."
"""
from __future__ import annotations

import sys
from pathlib import Path

from open_bethel import bethel_strengths, load_games, loo_contributions

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "phase0" / "games-fhsaa-fl-2026.csv"
DEFAULT_TEAM = "episcopal-eagles"


def main(argv: list[str]) -> int:
    csv_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSV
    target = argv[2] if len(argv) > 2 else DEFAULT_TEAM

    teams, games = load_games(csv_path)
    if target not in teams:
        print(f"'{target}' is not in {csv_path.name}", file=sys.stderr)
        return 1

    print(f"Target: {target}")
    print(f"Dataset: {csv_path.name}  ({len(games)} games, {len(teams)} teams)")
    print("Computing baseline strengths …", flush=True)
    baseline, iters, converged = bethel_strengths(teams, games)
    status = f"converged in {iters} iterations" if converged else f"DID NOT CONVERGE — stopped at max_iter={iters}"
    print(f"  {status}")
    print("Computing leave-one-out contributions …", flush=True)
    contribs = loo_contributions(teams, games, target, baseline_strengths=baseline)

    contribs_sorted = sorted(contribs, key=lambda c: -c.delta)

    s = baseline[target]
    print(f"\nBaseline strength for {target}: {s:.4f}\n")

    print(f"{'Δ strength':>12}  {'result':>6}  {'opponent':<40}")
    print("-" * 64)
    for c in contribs_sorted:
        result = "W" if c.winner == target else "L"
        opp = c.loser if c.winner == target else c.winner
        print(f"{c.delta:+12.5f}  {result:>6}  {opp:<40}")

    total_delta = sum(c.delta for c in contribs)
    print("-" * 64)
    print(f"{'sum':>12}   {total_delta:+.5f}")
    print()
    print("A positive delta means including the game raised the team's strength.")
    print("Wins typically contribute positively, losses negatively — but the")
    print("magnitude depends on the opponent's strength. Beating a strong")
    print("opponent contributes more than beating a weak one; losing to a")
    print("weak opponent hurts more than losing to a strong one.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
