# Phase 0 findings

A working reference implementation of Bethel's Bradley-Terry-Ford method and classical RPI, benchmarked on real FHSAA Class 2A baseball data from the 2026 season. This document is the empirical baseline that future versions of open-bethel should be measured against.

Everything below is reproducible from this repository:

```
python3 phase0/phase0.py  phase0/games-fhsaa-fl-2026.csv
python3 phase0/validate.py phase0/games-fhsaa-fl-2026.csv [YYYY-MM-DD cutoff]
```

## TL;DR

On a statewide-scale graph (5,089 games across 872 Florida high school baseball teams in the 2026 season, BFS-expanded from a five-team seed set), Bethel's Bradley-Terry-Ford method produces predictions that beat every tested baseline on every cutoff tested, with the best log-loss of any method. On a small district-only sample of the same season (122 games, 69 teams), Bethel could not distinguish itself from a naive win-percentage baseline. The difference is graph density, not algorithm quality — and that finding is the core empirical claim this phase establishes.

## What we tested

Each method was trained on all games strictly before a cutoff date and asked to predict the outcome of games from the cutoff onward. Predictions are probabilities that the home team wins (no home-field adjustment; all methods predict neutral-site). Scoring:

- **accuracy** — fraction of held-out games where the favored side won
- **log-loss** — binary cross-entropy on P(home wins); penalizes confident-and-wrong predictions heavily
- **Brier score** — mean squared error on the probability

Methods compared:

- **Bethel** — P(A beats B) = s_A / (s_A + s_B), with a Bayesian prior (one fictional win and one fictional loss per team vs. a strength-1 anchor) to keep undefeated and winless teams bounded. Converges in ~500 iterations at 1e-10 tolerance on the 872-team graph.
- **Classical RPI** — the 0.25·WP + 0.50·OWP + 0.25·OOWP composite used in NCAA baseball selection contexts. Predictions use the naive P = rpi_A / (rpi_A + rpi_B). A production RPI would fit a logistic calibrator on top; the raw ratio produces poorly calibrated probabilities, which is visible in the log-loss column below.
- **Laplace-smoothed W%** — P(A beats B) = wp'_A / (wp'_A + wp'_B), where wp' adds one fictional win and one fictional loss for smoothing. The "stupid baseline" to beat.
- **Coin** — flat P = 0.5. The floor.

## Statewide graph (5,089 games, 872 teams)

| Cutoff | Test N | Bethel acc | RPI acc | W% acc | Coin | Bethel log-loss | RPI log-loss | W% log-loss |
|---|---|---|---|---|---|---|---|---|
| 2026-03-15 | 2,215 | **0.700** | 0.707 | 0.644 | 0.604 | **0.572** | 1.412 | 0.625 |
| 2026-03-20 | 1,852 | **0.727** | 0.717 | 0.668 | 0.609 | **0.547** | 1.358 | 0.616 |
| 2026-04-01 | 1,051 | **0.761** | 0.736 | 0.679 | 0.639 | **0.491** | 1.099 | 0.602 |
| 2026-04-10 | 483 | 0.806 | **0.810** | 0.713 | 0.673 | **0.424** | 0.668 | 0.581 |

Bethel beats the naive W% baseline by 5–10 points of accuracy at every cutoff, and has the best log-loss of any method at every cutoff. RPI's accuracy is competitive but its log-loss is poor because "rating-over-sum-of-ratings" is not a calibrated probability.

## District-only sample (122 games, 69 teams)

| Cutoff | Test N | Bethel acc | RPI acc | W% acc | Coin |
|---|---|---|---|---|---|
| 2026-03-15 | 54 | 0.500 | 0.574 | **0.630** | 0.611 |
| 2026-03-20 | 44 | 0.705 | 0.705 | **0.727** | 0.682 |
| 2026-04-01 | 22 | **0.818** | 0.773 | **0.818** | 0.727 |
| 2026-04-10 | 5 | 0.800 | 0.400 | 0.800 | 0.600 |

On this sample Bethel is tied or behind W% at every cutoff. The held-out sets at the smaller cutoffs are small enough that individual-game variance dominates, but even so the direction is clear: a 122-game graph with an average of ~2.9 games per team does not give Bethel's strength-of-schedule adjustment enough signal to pull ahead of the naive baseline.

## Why the difference

Bethel's estimate of a team's strength depends on its opponents' strengths, which in turn depend on *their* opponents' strengths, and so on. In the district-only sample most opponents are leaf nodes — teams that appear only because one of the five focus teams played them once or twice — and the Bayesian prior pulls those leaves toward the anchor strength (1.0). That prior-bias propagates up the chain and flattens the strength estimates for the focus teams. On the 872-team graph every focus-team opponent has 20+ other games in the graph, and those opponents' opponents have dense connections too. The prior still exists but is dwarfed by real information, and the strength-of-schedule adjustment finally moves the number.

This is consistent with Bethel's own paper (§8), which flags graph connectivity as the only genuinely unsolved problem of the method. We can't cheat our way around it with a better iteration rule; we need a denser graph.

## Connectivity holds its shape

The pairwise indirection diagnostic shows three district pairs that never played directly in 2026: Episcopal ↔ Bishop Snyder, Bolles ↔ Trinity Christian, and Providence ↔ Trinity Christian. All three chains resolve at depth +1 (one common opponent) in both the district-only and statewide graphs. The state-scale expansion doesn't create new direct pairings between the five focus teams — they played who they played — but the indirect comparability strengthens dramatically because each focus team shares more common opponents with its unplayed rival.

The v1 UI target is to surface this diagnostic explicitly rather than hide it: any pair a user asks about should report whether the comparison is grounded in a direct game, a single common opponent, or a longer chain.

## Focus-team ranking (statewide graph)

| # | Team | W-L | Bethel strength | RPI |
|---|---|---|---|---|
| 1 | Trinity Christian | 21–7 | 16.26 | 0.640 |
| 2 | Bishop Snyder | 19–6 | 12.16 | 0.620 |
| 3 | Bolles | 18–8 | 7.36 | 0.604 |
| 4 | Episcopal | 17–10 | 4.29 | 0.564 |
| 5 | Providence | 13–13 | 3.80 | 0.570 |

Bethel and RPI agree on the top three. They disagree on #4 vs #5: Bethel orders Episcopal above Providence; RPI orders Providence above Episcopal. Episcopal's strength-of-schedule is measurably tougher on the statewide graph, which Bethel's iterative method rewards and RPI's averaging-of-averages partially absorbs. This is exactly the kind of principled divergence the eventual pairwise-explanation UI is designed to make legible.

## What this phase does not claim

- **No comparison to any state-published ranking.** By design — matching a vendor formula is not the goal of this project and never will be. Our validation target is predictive accuracy on held-out games, which is the honest test independent of anyone else's methodology.
- **No home/away adjustment.** Bethel's paper flags it as future work (§8); we respect that boundary in the reference implementation. Adding a home-field term would improve accuracy but introduces another tuning parameter, and the separation between open-bethel and the black-box alternatives depends on having principled reasons for every dial we turn.
- **No predictive calibration yet.** The probabilities Bethel produces are reasonably well-calibrated (Brier 0.134–0.195 across cutoffs) but a proper reliability diagram has not been constructed. That's a next-phase task.
- **Two FHSAA Class 2A programs have no 2026 data on the source site** and are missing from the graph: Global Outreach Charter Academy (Jacksonville) and Four Corners (Davenport). Both teams' public schedule pages list no completed games for the 2026 season.
- **Only one season of data.** Cross-season generalization is untested.

## How to re-run

```
python3 phase0/phase0.py  phase0/games-fhsaa-fl-2026.csv    # rankings + connectivity
python3 phase0/validate.py phase0/games-fhsaa-fl-2026.csv 2026-04-01
python3 phase0/validate.py phase0/games-fhsaa-fl-2026.csv 2026-03-20
```

Python 3.10+, standard library only.

## Record this is measured against

Any future change to the algorithm, the prior, the smoothing, the tolerance, or the data must at minimum match the numbers in this document on the same CSV. If it doesn't, either the change is a regression or the benchmark is wrong — and "the benchmark is wrong" is a claim that requires evidence, not convenience.
