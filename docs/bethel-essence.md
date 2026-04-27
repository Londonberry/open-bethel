# Bethel's Method — Essence for Implementation

Distilled reference for implementing the ranking method described in *A Solution To The Unequal Strength Of Schedule Problem* by Roy Bethel (MITRE Corporation, August 2005). Source paper archived at [`https://fliphtml5.com/sdyu/suvz/basic`](https://fliphtml5.com/sdyu/suvz/basic).

## Summary

Every team has a single positive number called **strength** (`s_t`). For any game between teams `t` and `t'`, the probability `t` wins is `s_t / (s_t + s_t')`.

The algorithm finds the set of strengths such that, for every team simultaneously, **the sum of their predicted win probabilities across their actual schedule equals their actual number of wins**. That constraint defines a unique solution (up to scale). Closed-form solving is impossible; a simple iteration converges in a few hundred iterations.

## The core model

For a game between teams `t` and `t'`:

```
p(t beats t') = s_t / (s_t + s_t')
```

This is the Bradley-Terry model (1952). Bethel cites it in §9 — his contribution is (a) deriving the model from a winning-percentage-compatibility argument rather than pairwise-preference theory, and (b) writing a more complete mathematical walkthrough than earlier sources. The underlying algorithm predates Bethel by ~50 years and is variously known as **Bradley-Terry**, **Bradley-Terry-Ford** (Ford, 1957, proved iteration convergence), or **Zermelo's method** (Zermelo, 1929, for chess). Naming the project `open-bethel` is stylistic — the mathematical pedigree is 70+ years old and rigorously studied.

## The iteration (the whole algorithm)

```python
import math

def bethel_strengths(teams, games, max_iter=500, tol=1e-10):
    """
    teams: iterable of team IDs (hashable)
    games: iterable of (winner_id, loser_id) pairs — ties excluded
    returns: dict {team_id: strength}
    """
    W = {t: 0 for t in teams}
    opps = {t: [] for t in teams}
    for winner, loser in games:
        W[winner] += 1
        opps[winner].append(loser)
        opps[loser].append(winner)

    s = {t: 1.0 for t in teams}

    for _ in range(max_iter):
        s_new = {}
        for t in teams:
            denom = sum(1.0 / (s[t] + s[o]) for o in opps[t])
            s_new[t] = W[t] / denom if denom > 0 else s[t]

        log_mean = sum(math.log(v) for v in s_new.values()) / len(teams)
        scale = math.exp(log_mean)
        s_new = {t: v / scale for t, v in s_new.items()}

        if max(abs(s_new[t] - s[t]) for t in teams) < tol:
            s = s_new
            break
        s = s_new

    return s
```

Bethel's Table 1 (1999 NFL example, 31 teams): converges to 8 decimal places in ~200 iterations.

### Two equivalent derivations

1. **Heuristic** (§4): "predicted wins must equal actual wins."
2. **Maximum likelihood** (§5): MLE of the Bradley-Terry probabilistic model.

Bethel proves in §5 that both yield identical solutions. This is intellectually satisfying but not operationally relevant — either derivation points to the same iteration above.

## Interpreting the output

Strengths are positive numbers; **only ratios matter**, not absolute values. Three ways to present results:

- **Raw strength `s_t`** — dimensionless, ratio-meaningful. Team at 2.0 is 2× as strong as team at 1.0.
- **`log₂(s_t)`** — easier to read. Team at +1.00 is 2× team at 0.00. Bethel's Table 2 displays this.
- **Projected winning percentage** over a hypothetical balanced schedule:

```
WP_t = (1 / (T-1)) * Σ_{t' ≠ t} s_t / (s_t + s_t')
```

This is the most coach-intelligible output — reads as a familiar win percentage. Equation (21) in the paper.

## What Bethel EXPLICITLY excludes — where commercial systems diverge

Bethel is emphatic about what the method does *not* incorporate. Each exclusion has a principled justification rooted in winning-percentage compatibility. Proprietary commercial implementations typically layer modifications on top of these exclusions.

| Factor | Bethel | Typical commercial implementation |
|---|---|---|
| Margin of victory | **Excluded**. Winning % doesn't know MoV. | Included, capped per sport |
| Home / away | **Excluded**. Assumes balanced H/A or cancels; bivariate extension proposed as future work (§8, eq. 24). | Included |
| Ties | **Excluded** (discarded games). "Degree of win" ∈ (0,1) proposed as future work. | Ad-hoc handling |
| Recency / time weighting | **Excluded**. All games count equally. | Weighted toward recent |
| Graph scope | League's own graph. | Broader cross-comparison |
| External factors (injury, weather, etc.) | **Excluded** as irrelevant for an "earned" method. | Unclear |

Each such modification is a tuning parameter. When applied without published weights or methodology, the ranking becomes unauditable. In `open-bethel`, each of these is instead an optional dial with documented defaults.

## Three edge cases that matter (Bethel flags them himself)

### 1. Undefeated teams → strength diverges (→ ∞)

A team that wins every game in its connected component forces `s_t → ∞`. Bethel acknowledges this in §8.

**Fix (Bethel's own suggestions):**
- **Degree of win** in (0, 1) instead of strict {0, 1} — e.g., Pythagorean adjustment or compressed MoV.
- **Bayesian prior** — add one fictitious win + one fictitious loss per team. Keeps probabilities in (0, 1).

**v1 decision:** ship the Bayesian prior. Simpler to explain, preserves algorithmic purity, reversible by configuration.

### 2. Winless teams → strength collapses (→ 0)

Symmetric to case 1. Same Bayesian prior fix resolves both.

### 3. Disconnected game graphs — Bethel's "major issue"

Quote (§8): *"The major issue for the presented and any earned method is connectivity."*

If two teams live in different graph components — no shared opponent, no opponent-of-opponent chain, etc. — their strengths cannot be meaningfully compared. Bethel **leaves this unsolved** and explicitly calls it future work (§8, last paragraph; citing [8] = Ford 1957).

This is the critical gap for high-school sports, where districts and small schools produce near-disconnected graphs routinely.

**v1 approach (a genuine differentiator from typical commercial rankings):**
- Compute pairwise level-of-indirection (0 = direct game, 1 = common opponent, 2 = opponent-of-opponent, ...)
- Flag pairs below a connectivity threshold as "not meaningfully comparable"
- Expose the connectivity diagnostic in the UI rather than hide it. Typical commercial systems dissolve disconnection into a broader graph; we surface it.

## Default parameter decisions for v1

Bethel's paper leaves several knobs unspecified. Defaults for `open-bethel` v1:

| Knob | Default | Rationale |
|---|---|---|
| Bayesian prior | 1 fictitious W + 1 fictitious L per team | Resolves undefeated/winless without breaking winning-percentage compatibility |
| Max iterations | 500 | ~2.5× Bethel's converged 200 for headroom |
| Convergence tolerance | `1e-10` on max strength delta | Bethel showed `1e-8` at iter 200 for NFL; `1e-10` gives margin |
| Scale normalization | `Σ log(s_t) = 0` | Bethel's Section 6 normalization |
| Tie handling | Exclude (Bethel's default). Opt-in "degree of win = 0.5" later. | Preserves theoretical guarantees |
| MoV / home-away / recency | **Off by default.** Exposed as optional dials later with published methodology. | Opacity transfers if we turn them on without disclosure |

## Validation / reproducibility gate

Bethel's Table 2 publishes the final strengths for all 31 NFL teams from the 1999 regular season, to 4 decimal places. This is a **perfect unit test**: run our implementation on the 1999 NFL schedule (available from pro-football-reference or nfl.com archives), compare each team's strength to Bethel's published value. If we match to 4 decimals, the core is correct. If we don't, we have a bug.

Table 1 additionally gives per-iteration RMS / max delta / log-likelihood values for the same data. Convergence-behavior tests can match those too.

## Author — context for outreach

- **Affiliation:** Roy Bethel was at **MITRE Corporation** (`rbethel@mitre.org`), the federally-funded R&D center that runs major DoD/intelligence research. Not a hobbyist. Likely in signal processing / decision theory / applied statistics given MITRE's typical work.
- **Paper hosting:** the PDF lived at `homepages.cae.wisc.edu/~dwilson/rsfc/rate/papers/BethelRank.pdf` — David Wilson's rec.sport.football.college rankings archive at UW-Madison. Wilson hosted; Bethel wrote at MITRE. (Many sources conflate these two affiliations.)
- **Companion document:** Reference [2] in the paper is `Bethel, R. E., "NFL Rankings Results"` with no URL — evidently a separate results document covering NFL seasons 2000-2004. Worth tracking down; would provide multi-season validation data.
- **Current status unknown.** LinkedIn / ORCID / MITRE publications page not yet checked. Outreach prerequisite.

## References (from Bethel 2005)

Most-load-bearing predecessors:

- Bradley, R. A. & Terry, M. E. (1952). *Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons.* Biometrika 39, 324-45. — The probability model.
- Ford, L. R. Jr. (1957). *Solution of a Ranking Problem from Binary Comparisons.* American Mathematical Monthly 64(8), 28-33. — Convergence proof for the iterative solution.
- Keener, J. P. (1993). *The Perron-Frobenius Theorem and the Ranking of Football Teams.* SIAM Review 35(1), 80-93. — Alternate (eigenvector) solution.
- Massey, K. *Massey Ratings Description.* mratings.com/theory/massey.htm. — Adjacent least-squares method; useful as a second independent rating in `open-bethel`.

Full reference list is on page 18 of the paper PDF.
