# FHSAA Class 2A coverage status

The rankings on this site are only as complete as the graph we crawled. This document is the honest accounting of where we are vs. the FHSAA's own published records, for transparency.

Re-runnable via `python3 site/fhsaa_crosscheck.py`, which pulls the FHSAA's current 2A rankings JSON and diffs each team's W-L record against ours.

## As of 2026-04-24

FHSAA snapshot date: **2026-04-18**. Our dataset crawled: **2026-04-24**.

- FHSAA Class 2A lists **75 teams**.
- We matched **72** of them to slugs in our graph.
- **3 teams are entirely absent** from our graph — breadth-first expansion from our current seed set did not reach them.
- Of the 72 matched, **31 have record mismatches** — our graph has fewer games than the FHSAA has recorded.
- Total FHSAA 2A games not in our dataset: **~420** (out of approximately 1,600 total 2A games).

## Why

The crawler BFS-expands from a seed list of 9 FHSAA 2A teams, most of them clustered in FHSAA Region 1 (North Florida / Jacksonville metro). At depth 2, BFS captures those seeds' opponents and opponents-of-opponents — which reliably covers North Florida but doesn't reach deep into South Florida (Miami metro) or Central Florida (Tampa/Sarasota). Teams like Palmer Trinity (Miami) are captured with only 5 of 26 games because only the handful of their opponents who also played a North Florida team appear in the graph.

This is a crawl-scope issue, not an algorithm issue. The math on the subset we do have is correct. The ordering within the well-covered North Florida subset is trustworthy. Cross-region strength comparisons are less trustworthy because the connecting graph is sparse.

## How to close the gap

Expand the seed list in the crawler to include at least one well-connected team per FHSAA 2A region/district that BFS isn't already reaching — realistically a set of 10-15 additional URLs covering Regions 3 and 4 in particular. Re-running the crawler at depth 2 from an expanded seed set would capture nearly all 2A-to-2A games and close the gap with FHSAA's records.

## Teams currently absent

- Ransom Everglades (Miami, FL)
- Riviera Prep (Miami, FL)
- Somerset Academy South Homestead (Homestead, FL)

## Teams currently undercounted

Top of the list by games-missing:

| team | FHSAA record | our record | games missing |
|---|---|---|---|
| Keys Gate (Homestead) | 10-15-0 | 1-2 | 22 |
| Mater Bay Academy (Cutler Bay) | 11-12-1 | 0-1 | 22 |
| Palmer Trinity (Miami) | 21-5-0 | 3-2 | 21 |
| Discovery (Lake Alfred) | 11-12-0 | 1-1 | 21 |
| Archbishop Carroll (Miami) | 15-8-0 | 3-2 | 18 |
| John Carroll Catholic (Fort Pierce) | 7-12-0 | 0-1 | 18 |
| Sarasota Military Academy | 11-11-0 | 2-2 | 18 |
| Bishop McLaughlin Catholic (Spring Hill) | 12-13-0 | 2-6 | 17 |
| Clearwater Central Catholic | 16-8-0 | 4-4 | 16 |
| Santa Fe Catholic (Lakeland) | 14-10-0 | 1-7 | 16 |

(Full list and totals from the `fhsaa_crosscheck.py` output.)

## Teams that match

In the well-covered subset, records align. Examples:

| team | FHSAA | ours |
|---|---|---|
| Venice | 26-1-0 | 26-1 |
| Creekside | 23-4-0 | 23-4 |
| Trinity Christian Academy (Jacksonville) | 20-7-0 | 20-7 |
| Bishop Snyder | 19-6-0 | 19-6 |
| Episcopal School of Jacksonville | 17-10-0 | 17-10 |
| Bolles | 18-8-0 | 18-8 |

## What this means for the rankings

The top of the 2A rankings shown on the site — dominated by North Florida teams — is defensible. Mid-table rankings that mix well-covered North Florida teams with undercovered South Florida teams are less so: a team with 5 of 26 real games in the graph will have a strength estimate driven mostly by the Bayesian prior, not by their actual performance.

The `min. games played` filter on the rankings index page is the workaround until the seed set is expanded. For users who want a clean picture of the covered subset, setting that to 10 or higher gives a view that excludes the sparsely-captured teams.
