# Phase 1

The package-structured implementation of open-bethel, plus the first feature that goes beyond ranking — per-game contribution analysis.

## Per-game contributions

For any team, `loo_contributions` computes the change in that team's Bethel strength from including each of its games in the graph, versus excluding that single game. The result answers the question the brief commits to: *"You can see how each game helped or hurt your rankings."*

The behavior is principled, not arbitrary:

- Beating a *strong* opponent contributes more positive strength than beating a weak one — because a strong opponent's strength estimate is itself higher, and winning against them moves more probability mass.
- Losing to a *weak* opponent hurts more than losing to a strong one — for the mirror reason.
- A game's contribution depends on the rest of the graph, not just the two teams involved. When a team's opponents have rich game histories themselves, the ranking signal per game is sharper.

## Run the demo

```
python3 phase1/contributions_demo.py                                          # default focus
python3 phase1/contributions_demo.py phase0/games-fhsaa-fl-2026.csv <team>    # any team
```

The script runs leave-one-out recomputation with warm-starts from the full-graph solution, so each LOO iteration converges in a handful of steps rather than re-running the algorithm from scratch.

## Method

For a target team, we:

1. Compute Bethel strengths on the full graph once. This is the baseline.
2. For each of the target team's games, rebuild the graph without that game, re-run Bethel from the full-graph solution (warm start), and read off the target team's new strength.
3. Report `strength_with − strength_without` for every game.

Leave-one-out sensitivity is not additive — the contributions don't sum to the team's strength minus the prior — but it gives each game a well-defined, explainable number. That's the UI-facing primitive.

## Complexity

Each LOO recomputation warm-starts from the converged full-graph solution and typically needs 20–50 additional iterations to re-converge on the modified graph. For a 5,000-game graph and a target team with 25 games played, a full contribution sweep runs in under 10 seconds on modest hardware. No external dependencies.
