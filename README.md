# open-bethel

**An open, auditable ranking engine for high school sports.**

When a ranking decides who makes the playoffs, who earns a seed, or who gets left off an at-large list, that ranking should be something any interested party can reproduce. Today it often isn't. The ranking systems that state athletic associations increasingly rely on are proprietary: the formulas are not published, the inputs are not released in full, and even administrators deferring to the numbers cannot always show their work.

open-bethel is an effort to change that — by specifying the ranking math in the open, implementing it in the open, and publishing the inputs, the code, and the outputs together so that the result is not a black box but a calculation anyone can re-run.

## What "transparent" means here

- **Explainable down to the individual game.** A team's rating is the product of its games; every game's contribution is recoverable and displayable.
- **Pairwise on demand.** Any two teams can be compared with the math that separates them, not a number-on-a-screen.
- **Full inputs, full code, full outputs.** Nothing is hidden behind "proprietary methodology."
- **Reproducible by third parties.** An athletic director, a reporter, a parent, or a rival ranking maintainer can download the data and the code and produce the same numbers.

## The method

The ranking engine is built on Roy Bethel's 2005 paper *An Optimal Value for the Bradley-Terry Model for Estimating Strength-of-Schedule*, which derives a maximum-likelihood strength rating via iterative updates over head-to-head results. It is the academic foundation that a family of modern commercial ranking systems trace back to — but unlike those systems, Bethel's method is published, peer-reviewed, and free for anyone to implement.

For the algorithmic core we're implementing, see [`docs/bethel-essence.md`](docs/bethel-essence.md).

## Status

Early. A working reference implementation lives in [`phase0/`](phase0/) — 122 games of real 2026 FHSAA Class 2A Region 1 District 3 baseball data, classical RPI and Bethel-method rankings, and a pairwise connectivity diagnostic, in ~200 lines of dependency-free Python you can run with `python3 phase0/phase0.py`.

The v1 target is Florida high school baseball across all eight FHSAA classifications: classical RPI, an open Bradley-Terry-Ford implementation of Bethel's method, and one independent predictive rating running side by side on the same input data, with per-game contributions and pairwise comparisons exposed in a public website and a pip-installable Python package.

## Data model

open-bethel is data-source-agnostic. The engine consumes a generic game list (CSV today, pluggable database adapters later) with one row per game: date, home team, away team, home score, away score. How that data gets collected — state-association exports, league scoring apps, hand entry, a user's own scraper — is the user's problem. Keeping ingest out of the core is what lets the project stay legally clean, adoptable across states and sports, and useful to anyone who already has game data in any format.

## Why the name

Roy Bethel (MITRE Corporation, 2005) published the paper that underlies the method. Naming the project after him is a statement of what it is: a published, auditable algorithm, implemented openly.

## License

MIT. See [`LICENSE`](LICENSE).
