# Phase 0

A single-file reference implementation of the two ranking methods at the core of open-bethel, run against a real season of FHSAA Class 2A Region 1 District 3 baseball (2026). The point is to prove the math works end-to-end, expose the edge cases early, and produce something any reader can inspect, modify, and re-run in under a minute.

## Run it

```
# District-only sample (122 games, 69 teams):
python3 phase0/phase0.py
python3 phase0/validate.py

# Full FL graph (4,395 games, 821 teams):
python3 phase0/phase0.py  phase0/games-fhsaa-fl-2026.csv
python3 phase0/validate.py phase0/games-fhsaa-fl-2026.csv
```

No dependencies beyond the Python standard library. Tested on Python 3.10+.

## What it computes

1. **Bethel strengths** — iterative MLE of the Bradley-Terry-Ford model, with a Bayesian prior (one fictional win + one fictional loss per team against an anchor of strength 1) to prevent divergence for undefeated or winless teams. Converges on the included dataset in ~130 iterations to a 1e-10 tolerance.
2. **Classical RPI** — the 0.25·WP + 0.50·OWP + 0.25·OOWP composite, with opponents' WP computed exclusive of head-to-head games (the standard NCAA definition).
3. **Pairwise connectivity** — shortest-path indirection between the five district teams in the opponent graph. Flags team pairs that never played each other directly, which is exactly the case Bethel calls out as unsolved in §8 of the paper.

## Data

Two datasets ship in this directory:

- **`games-district-3-2a-2026.csv`** — 122 deduped games across 69 teams. Full 2026 season of five FHSAA Class 2A Region 1 District 3 teams plus every non-district opponent they played. Compiled from public schedule pages, with provenance in `scripts/build_district_3_2a_csv.py`.
- **`games-fhsaa-fl-2026.csv`** — 4,395 deduped games across 821 teams. Breadth-first expansion from the five District 3-2A seeds to two opponent-hops out, capturing most FHSAA Class 2A teams and a long tail of their opponents. Produced by a private crawler (not checked in) that emits this generic schema; the CSV is the only artifact that crosses into this repo.

Team pages were compiled from public sources on 2026-04-24:
- [Jacksonville High School Baseball Network — 2A District 3](https://jacksonvillehighschoolbaseball.com/division/2a-district-3/)
- Individual team pages on the same site
- [Episcopal School of Jacksonville athletics](https://esj.org/esj-athletics/baseball-varsity-boys/)
- [FHSAA Baseball](https://fhsaa.com/sports/baseball)

`scripts/build_district_3_2a_csv.py` is the provenance record: re-running it regenerates the CSV from the transcribed schedules, and anyone can audit or correct a specific game by editing the inline data.

## On data sourcing

**open-bethel itself is data-source-agnostic.** The library reads a CSV with one row per game — nothing more. How that CSV gets populated (scrapers, state-association exports, hand entry, a league's own scoring system) is a problem for the data producer, not for the ranking engine. The dataset in this directory is a sample fixture, not a blessed ingest path.

## Expected output shape

```
Bethel strengths
  rank  team                W-L     strength   rpi     wp
  1     trinity-christian   20-7    ...
  ...

Classical RPI
  ...

Pairwise connectivity
  bishop-snyder vs bolles      DIRECT
  bishop-snyder vs episcopal   indirect (+1)
  ...
```

## Validation harness

`validate.py` splits the CSV at a date cutoff, trains each ranking method on games before the cutoff, and scores each method's predicted win probability against the actual outcomes of games from the cutoff onward. Metrics: accuracy, log-loss, and Brier score, against three baselines (Bethel, classical RPI, Laplace-smoothed win-percentage Bradley-Terry, and a 50/50 coin). Usage: `python3 phase0/validate.py [csv] [YYYY-MM-DD cutoff]`.

Results on the statewide graph (n = 938 held-out games, cutoff 2026-04-01):

| method | accuracy | log-loss | Brier |
|---|---|---|---|
| Bethel | **0.757** | **0.494** | **0.163** |
| Classical RPI | 0.744 | 1.030 | 0.222 |
| Laplace-smoothed W% | 0.683 | 0.600 | 0.206 |
| 50/50 coin | 0.663 | 0.693 | 0.250 |

The pattern holds across cutoffs at 3/15, 3/20, 4/01, and 4/10: Bethel beats the naive win-percentage baseline on accuracy by 5–9 points, and has the best log-loss of any method at every cutoff. On the district-only dataset (122 games), Bethel could not distinguish itself from the naive baseline. The result moving from 122 games to 4,395 games is a direct confirmation that the method needs graph density, not more clever math, to produce defensible predictions.

(Classical RPI's log-loss is poor because "rating divided by sum of ratings" is not a calibrated probability — a production RPI implementation would fit a logistic calibrator on top. Accuracy numbers are not affected.)

## What this phase does NOT do

- No public website, no UI — that's Phase 2+.
- No side-by-side comparison with a state-published ranking — that requires scraping the published feed, which is a separate problem (and, for the FHSAA feed, one that is deliberately not solved inside this project).
- No per-game contribution export or pairwise-explanation UI — those are downstream features that sit on top of the core math proven out here.
- No home/away adjustment — the paper flags it as future work (§8); all methods here predict neutral-site.
