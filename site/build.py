"""
Build the static JSON dataset consumed by site/public/index.html.

Produces a single site/public/data.json containing:
  - rankings: every team, sorted by Bethel strength, with all metrics
  - games:    per-team chronological game list
  - contributions: per-team per-game LOO contribution deltas, computed for
                   a curated subset (see FOCUS_SET below) to keep build
                   time reasonable
  - connectivity_pairs: pairwise indirection for a small set of focus pairs
  - meta:     dataset filename, row counts, convergence info, build time

No external dependencies. Re-run whenever games-fhsaa-fl-2026.csv changes.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from open_bethel.bethel import bethel_strengths
from open_bethel.connectivity import indirection
from open_bethel.contributions import loo_contributions
from open_bethel.rpi import classical_rpi

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "phase0" / "games-fhsaa-fl-2026.csv"
OUT_PATH = Path(__file__).resolve().parent / "public" / "data.json"

# FHSAA Class 2A team slugs (source-site naming conventions). Contributions are
# computed for this set so the primary audience — 2A coaches, ADs, stats
# folks — sees a real per-game breakdown for their own team.
FHSAA_2A = frozenset([
    "bishop-snyder-cardinals", "bolles-bulldogs", "episcopal-eagles",
    "providence-school-stallions", "trinity-christian-academy-conquerors",
    "florida-state-university-high-school-seminoles", "maclay-marauders",
    "bozeman-bucks", "pensacola-catholic-crusaders", "keystone-heights-indians",
    "father-lopez-green-wave", "interlachen-rams", "pk-yonge-blue-wave",
    "trinity-catholic-celtics", "circle-christian-centurions",
    "crooms-academy-panthers", "lake-highland-prep-highlanders",
    "masters-academy-patriots", "trinity-prep-saints",
    "cornerstone-charter-academy-ducks", "first-academy-eagles",
    "foundation-academy-lions", "montverde-academy-eagles",
    "windermere-prep-lakers", "bell-creek-academy-panthers",
    "discovery-spartans", "lakeland-christian-vikings",
    "santa-fe-catholic-hawks", "cocoa-beach-minutemen",
    "holy-trinity-episcopal-academy-tigers", "john-carroll-catholic",
    "melbourne-central-catholic-hustlers", "somerset-academy-canyons-cougars",
    "berkeley-prep-buccaneers", "bishop-mclaughlin-catholic-hurricanes",
    "brooks-debartolo-collegiate-phoenix", "carrollwood-day-patriots",
    "tampa-catholic-crusaders", "tampa-prep-terrapins",
    "clearwater-central-catholic-marauders", "northside-christian-mustangs",
    "shorecrest-preparatory-chargers", "st-petersburg-catholic-barons",
    "bradenton-christian-panthers", "cardinal-mooney-cougars",
    "imagine-north-port-sharks", "out-of-door-academy-thunder",
    "sarasota-military-academy-eagles", "evangelical-christian-sentinels",
    "first-baptist-academy-lions", "gateway-charter-eagles",
    "marco-island-academy-manta-rays", "oasis-sharks", "benjamin-buccaneers",
    "cardinal-newman-crusaders", "kings-academy-lions",
    "oxbridge-academy-thunderwolves", "st-andrews-scots",
    "st-john-paul-ii-academy-eagles", "chaminade-madonna-college-prep-lions",
    "florida-christian-patriots", "hialeah-educational-academy-bulldogs",
    "nsu-university-school-sharks", "westminster-academy-lions",
    "palmer-trinity-falcons", "ransom-everglades-raiders",
    "riviera-preparatory-school-bulldogs", "westminster-christian-warriors",
    "archbishop-carroll-bulldogs", "coral-shores-hurricanes",
    "keys-gate-charter-knights", "mater-academy-lions",
])


def load_games_full(path: Path):
    """Read CSV and return (teams, games_tuples, rows_with_metadata)."""
    teams: set[str] = set()
    games: list[tuple[str, str]] = []
    rows: list[dict] = []
    with path.open() as f:
        for r in csv.DictReader(f):
            home = r["home_team"].strip()
            away = r["away_team"].strip()
            hs = int(r["home_score"])
            as_ = int(r["away_score"])
            teams.update((home, away))
            if hs == as_:
                continue
            winner, loser = (home, away) if hs > as_ else (away, home)
            games.append((winner, loser))
            rows.append({
                "date": r["date"],
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "game_type": r.get("game_type", "regular"),
                "winner": winner,
                "loser": loser,
            })
    return sorted(teams), games, rows


def build_team_games(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        for team, is_home in ((r["home_team"], True), (r["away_team"], False)):
            opp = r["away_team"] if is_home else r["home_team"]
            us = r["home_score"] if is_home else r["away_score"]
            them = r["away_score"] if is_home else r["home_score"]
            out[team].append({
                "date": r["date"],
                "opponent": opp,
                "home": is_home,
                "team_score": us,
                "opp_score": them,
                "result": "W" if us > them else "L",
                "game_type": r["game_type"],
            })
    for t in out:
        out[t].sort(key=lambda g: g["date"])
    return out


def main() -> None:
    t0 = time.time()
    print(f"Reading {CSV_PATH.name} …", flush=True)
    teams, games, rows = load_games_full(CSV_PATH)
    print(f"  {len(games)} games, {len(teams)} teams")

    print("Computing Bethel strengths …", flush=True)
    strengths, iters = bethel_strengths(teams, games)
    print(f"  converged in {iters} iterations")

    print("Computing classical RPI …", flush=True)
    rpi = classical_rpi(teams, games)

    team_games = build_team_games(rows)

    wins = defaultdict(int)
    losses = defaultdict(int)
    for w, l in games:
        wins[w] += 1
        losses[l] += 1

    rankings = sorted(
        [
            {
                "team": t,
                "wins": wins[t],
                "losses": losses[t],
                "games": wins[t] + losses[t],
                "bethel": round(strengths[t], 4),
                "rpi": round(rpi[t]["rpi"], 4),
                "wp": round(rpi[t]["wp"], 4),
                "owp": round(rpi[t]["owp"], 4),
                "oowp": round(rpi[t]["oowp"], 4),
            }
            for t in teams
        ],
        key=lambda r: -r["bethel"],
    )
    for i, r in enumerate(rankings, 1):
        r["rank"] = i

    # Contributions: expensive. Compute for FHSAA 2A teams (priority audience)
    # plus the top 20 by Bethel strength (likely state-level prominent teams).
    top20 = {r["team"] for r in rankings[:20]}
    focus_set = (FHSAA_2A | top20) & set(teams)
    print(f"Computing per-game contributions for {len(focus_set)} teams …", flush=True)

    contributions: dict[str, list[dict]] = {}
    for i, t in enumerate(sorted(focus_set), 1):
        contribs = loo_contributions(teams, games, t, baseline_strengths=strengths)
        contributions[t] = [
            {
                "game_index": c.game_index,
                "winner": c.winner,
                "loser": c.loser,
                "delta": round(c.delta, 5),
            }
            for c in contribs
        ]
        if i % 10 == 0:
            print(f"  {i}/{len(focus_set)}", flush=True)

    # Connectivity pairs within FHSAA 2A — useful for the UI's "why can't we
    # compare these two teams directly?" affordance.
    print("Computing connectivity for 2A pairs …", flush=True)
    focus_list = sorted(t for t in FHSAA_2A if t in set(teams))
    pairs = []
    for i, a in enumerate(focus_list):
        for b in focus_list[i + 1 :]:
            d = indirection(teams, games, a, b)
            pairs.append({"a": a, "b": b, "hops": d})

    data = {
        "meta": {
            "dataset": CSV_PATH.name,
            "games_count": len(games),
            "teams_count": len(teams),
            "convergence_iterations": iters,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contributions_computed_for": sorted(focus_set),
        },
        "rankings": rankings,
        "team_games": team_games,
        "contributions": contributions,
        "connectivity_pairs": pairs,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUT_PATH} ({size_kb:.0f} KB) in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
