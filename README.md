# open-bethel

**A transparent, auditable ranking engine for sports teams.**

`open-bethel` computes strength ratings, strength-of-schedule, and per-game contributions from a list of head-to-head game results. The math is Roy Bethel's Bradley-Terry-Ford method (MITRE Corporation, 2005), classical RPI, and leave-one-out attribution — published, peer-reviewed, and reimplementable from the paper. The package is dependency-free Python; the source is short enough to read in an afternoon.

## What it produces

- **Strength ratings.** Each team gets a single number reflecting how strong its results show it to be, accounting for opponent quality. Ratings are derived by maximum likelihood under the Bradley-Terry model with a Bayesian prior to keep low-data and disconnected graphs well-behaved.
- **Classical RPI.** A 25/50/25 weighted blend of win percentage, opponents' win percentage, and opponents' opponents' win percentage. Provided alongside the strength rating for direct comparison with traditional formulas.
- **Per-game contributions.** For any team, a leave-one-out decomposition of which games raised the rating and which lowered it, sorted by impact. Lets a team or a journalist answer "which win mattered most?" with arithmetic, not narrative.
- **Pairwise diagnostics.** For any two teams, the level of indirection between them in the head-to-head graph and the chains of opponents that connect them. Surfaces when a comparison is well-grounded vs. when it relies on long inferential paths.

## Why it exists

When a ranking decides who makes the playoffs, who earns a seed, or who is left out, that ranking should be something the parties affected can reproduce. The systems many state athletic associations now defer to are proprietary: the formulas are not published, the inputs are not released in full, and even administrators applying the numbers cannot always show their work. `open-bethel` is the alternative — specified in the open, implemented in the open, and free for any state association, conference, or tournament director to adopt.

## Install

```
pip install open-bethel
```

## Use

```python
from open_bethel import bethel_strengths, classical_rpi, load_games

teams, games = load_games("games.csv")
strengths, iters, converged = bethel_strengths(teams, games)
```

Or from the command line:

```
open-bethel-rank      games.csv  team-a  team-b
open-bethel-validate  games.csv  2026-04-01
open-bethel-diagnose  games.csv
```

The CSV expects one row per game with columns `date, home_team, away_team, home_score, away_score`. Team identifiers are free-form. Tied games are dropped (the model is undefined for ties).

## Method

The core method is the iterative Bradley-Terry-Ford strength rating with a Bayesian prior, derived in [*An Optimal Value for the Bradley-Terry Model for Estimating Strength-of-Schedule*](https://fliphtml5.com/sdyu/suvz/basic) (Bethel, MITRE Corporation, 2005). For the algorithmic core, see [`docs/bethel-essence.md`](docs/bethel-essence.md).

## Validation

The test suite reproduces Bethel's worked example — the converged Bradley-Terry-Ford strengths for all 31 NFL teams after the 1999 regular season (Table 2 of the paper) — to four decimal places given the same 248-game schedule. This is a direct check against published ground truth, not just internal self-consistency.

```
$ python -m pytest tests/ -v
tests/test_bethel_nfl_1999.py::test_reproduces_bethel_1999_nfl_table_2 PASSED
tests/test_bethel_nfl_1999.py::test_1999_nfl_rank_order_matches_bethel  PASSED
tests/test_bethel_nfl_1999.py::test_1999_nfl_log_strengths_sum_to_zero  PASSED
tests/test_smoke.py ............................................        PASSED
12 passed in 0.05s
```

The top of the published Table 2 versus what `open-bethel` produces from the same fixture:

| Team | Bethel (2005) | open-bethel | Δ |
|------|--------------:|------------:|---:|
| IND  | 6.9927        | 6.9927      | 0.0000 |
| JAX  | 5.0117        | 5.0117      | 0.0000 |
| BUF  | 3.8538        | 3.8538      | 0.0000 |
| TEN  | 3.7348        | 3.7348      | 0.0000 |
| MIA  | 2.5624        | 2.5624      | 0.0000 |

Full table and fixture in [`tests/test_bethel_nfl_1999.py`](tests/test_bethel_nfl_1999.py) and [`tests/fixtures/nfl_1999.csv`](tests/fixtures/nfl_1999.csv).

## Why the name

Roy Bethel published the paper that underlies the method. Naming the project after him is a statement of what it is: a published, auditable algorithm, implemented openly.

## License

MIT. See [`LICENSE`](LICENSE).
