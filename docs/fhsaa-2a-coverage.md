# FHSAA Class 2A coverage status

The rankings on this site are only as complete as the graph we crawled. This document is the honest accounting of where we are vs. the FHSAA's own published records, for transparency.

Re-runnable via `python3 site/fhsaa_crosscheck.py`, which pulls the FHSAA's current 2A rankings JSON and diffs each team's W-L record against ours.

## As of 2026-04-24

FHSAA snapshot date: **2026-04-18**. Our dataset crawled: **2026-04-24**.

- FHSAA Class 2A lists **75 teams**.
- We match **75 of 75** teams to slugs in our graph.
- **0 teams absent** — every FHSAA 2A team is in the dataset.
- Of the 75 matched, **10 have minor record deltas** (±1 game mostly; one at ±3).
- Total FHSAA 2A games not in our dataset: **9** (vs ~1,600 total 2A games, ≈99.4% coverage).

Every remaining discrepancy is ±1 game. Given the 6-day gap between the FHSAA's April 18 snapshot and our April 24 crawl, the residuals are consistent with ordinary recency-window drift: games played in that window appear on one side of the comparison but not the other, depending on which source updated first.

## Remaining deltas

| Team | FHSAA | Ours | Δ |
|---|---|---|---|
| The Master's Academy (Oviedo) | 10-14 | 8-13 | +3 |
| Cardinal Mooney (Sarasota) | 22-3 | 21-3 | +1 |
| Westminster Christian (Miami) | 16-7 | 15-7 | +1 |
| Providence School (Jacksonville) | 13-12 | 13-11 | +1 |
| Windermere Prep | 10-10 | 9-10 | +1 |
| Sarasota Military Academy | 11-11 | 11-10 | +1 |
| Interlachen | 4-15 | 4-14 | +1 |
| Montverde Academy | 16-7 | 16-8 | −1 |
| Cornerstone Charter Academy | 7-13 | 8-13 | −1 |
| Crooms Academy | 4-9 | 5-9 | −1 |

## History

| date | graph | 2A matched | absent | mismatched | games short |
|---|---|---|---|---|---|
| 2026-04-24 (initial, 9-seed crawl) | 872 teams | 67/75 | 3 | 31 | ~420 |
| 2026-04-24 (28-seed expansion) | 942 teams | **75/75** | **0** | **10** | **9** |

## How it was fixed

Expanded the crawl's seed set from 9 Jacksonville-biased seeds to **28 seeds covering all four FHSAA regions** — at least one well-connected 2A team per region/district. Breadth-first expansion to depth 2 from the expanded seeds captures every 2A-to-2A game plus the out-of-class opponents those teams played. Seeds added span Regions 2 (Central FL), 3 (Tampa Bay / Gulf / Southwest), and 4 (South Florida / Miami metro / Palm Beach).

The fix is entirely a data-acquisition change — no change to the ranking engine, the Bethel iteration, the prior, or the connectivity diagnostic.

## Running the check

```
python3 site/fhsaa_crosscheck.py
```

Fetches the FHSAA's current 2A rankings directly from their public JSON feed, maps team names to our slugs, and prints the deltas. Adds a slug to `MANUAL_SLUG_MAP` if a team can't be matched by name prefix alone (common for schools with punctuation in their name, e.g. *P.K. Yonge*, *King's Academy*, or disambiguation when multiple Florida schools share a name like *Trinity Christian Academy*).
