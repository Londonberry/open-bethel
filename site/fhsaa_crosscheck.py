"""
Cross-check our dataset against the FHSAA's published rankings.

The FHSAA rankings page at fhsaa.com loads its data from two JSON endpoints
(discovered by inspecting the page). This script pulls the Class 2A division
from that feed and compares every team's record against ours, identifying
(a) teams whose records don't match — which implies we're missing games for
that team — and (b) teams the FHSAA lists whose slugs we can't map.

The 8 "unmatched" teams below have FHSAA names that don't cleanly
fuzzy-match against our slugs (usually punctuation or common-word issues
like "King's Academy" or "P.K. Yonge"); the MANUAL_SLUG_MAP fills those in.

Run:
    python3 site/fhsaa_crosscheck.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

FHSAA_RANKINGS_URL = (
    "https://fhsaa_ftp.sidearmsports.com/custompages/rankings/baseball_rankings.json"
)
DATA_JSON = Path(__file__).resolve().parent / "public" / "data.json"

# Hand-curated mapping for FHSAA school names whose canonical slug isn't
# derivable from a straightforward prefix-match. Grows as needed.
MANUAL_SLUG_MAP = {
    "Episcopal School of Jacksonville (Jacksonville, FL)": "episcopal-eagles",
    "King's Academy (West Palm Beach, FL)": "kings-academy-lions",
    "Saint Andrew's (Boca Raton, FL)": "saint-andrews-scots",
    "The Master's Academy (Oviedo, FL)": "masters-academy-patriots",
    "P.K. Yonge (Gainesville, FL)": "pk-yonge-blue-wave",
    # Disambiguate same-named teams (e.g. two "Trinity Christian Academy"s in FL).
    "Trinity Christian Academy (Jacksonville, FL)": "trinity-christian-academy-conquerors",
    # Disambiguate Somerset branches — FHSAA means the Homestead campus.
    "Somerset Academy South Homestead (Homestead, FL)": "somerset-academy-south-homestead-hurricanes",
    "Ransom Everglades (Miami, FL)": "ransom-everglades-raiders",
    "Riviera Prep (Miami, FL)": "riviera-prep-bulldogs",
    "John Carroll Catholic (Fort Pierce, FL)": "john-carroll-catholic-golden-rams",
    # Disambiguate Jesuit Tampa (4A) — there's a shorter `jesuit` alias slug
    # in our data that the prefix-match accidentally prefers.
    "Jesuit (Tampa, FL)": "jesuit-tigers",
}


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fetch_fhsaa_2a() -> list[dict]:
    # The FHSAA feed lives at a host with an underscore; Python's urllib
    # treats that as an SSL hostname mismatch. Curl handles it fine.
    result = subprocess.run(
        ["curl", "-sS", "-A", "Mozilla/5.0", FHSAA_RANKINGS_URL],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    div_2a = next(d for d in data["Divisions"] if d["Name"] == "Division 2A")
    return div_2a["Teams"], data["Meta"]


def match_slug(name: str, our_slugs: set[str]) -> str | None | object:
    """Return slug, or None if our dataset doesn't have the team.

    Manually-mapped-but-absent entries return a special MISSING_SENTINEL so
    we can distinguish 'couldn't figure out which slug' from 'we know for
    sure this team isn't in the dataset because BFS didn't reach them'.
    """
    if name in MANUAL_SLUG_MAP:
        slug = MANUAL_SLUG_MAP[name]
        if slug is None:
            return MISSING_SENTINEL
        return slug if slug in our_slugs else None
    m = re.match(r"^(.+?)\s*\([^,]+,\s*FL\)\s*$", name)
    if not m:
        return None
    team_name = m.group(1).strip()
    name_slug = slugify(team_name)
    candidates = [s for s in our_slugs if s == name_slug or s.startswith(name_slug + "-")]
    if not candidates:
        return None
    candidates.sort(key=len)
    return candidates[0]


MISSING_SENTINEL = object()


def main() -> int:
    if not DATA_JSON.exists():
        print(f"Not found: {DATA_JSON}", file=sys.stderr)
        return 1
    ours = json.load(DATA_JSON.open())
    our_by_slug = {r["team"]: r for r in ours["rankings"]}
    our_slugs = set(our_by_slug)

    try:
        fhsaa_teams, meta = fetch_fhsaa_2a()
    except Exception as e:
        print(f"Could not fetch FHSAA feed: {e}", file=sys.stderr)
        return 1

    print(f"FHSAA snapshot: {meta['RankingsDate']}  |  {len(fhsaa_teams)} teams in Class 2A")
    print(f"Our dataset:   {ours['meta']['generated_at']}  |  {ours['meta']['teams_count']} teams total")
    print()

    matched: list[tuple[dict, dict]] = []
    unmatched: list[str] = []
    absent: list[dict] = []
    for team in fhsaa_teams:
        slug = match_slug(team["SchoolName"], our_slugs)
        if slug is MISSING_SENTINEL:
            rec = team["Record"].split("-")
            absent.append({
                "name": team["SchoolName"],
                "fhsaa_record": team["Record"],
                "fhsaa_games": int(rec[0]) + int(rec[1]),
            })
            continue
        if not slug:
            unmatched.append(team["SchoolName"])
            continue
        matched.append((team, our_by_slug[slug]))

    mismatches = []
    for fhsaa_team, ours in matched:
        rec = fhsaa_team["Record"].split("-")
        fw, fl = int(rec[0]), int(rec[1])
        ft = int(rec[2]) if len(rec) > 2 else 0
        if fw != ours["wins"] or fl != ours["losses"]:
            mismatches.append({
                "name": fhsaa_team["SchoolName"],
                "slug": ours["team"],
                "fhsaa_record": fhsaa_team["Record"],
                "our_record": f"{ours['wins']}-{ours['losses']}",
                "games_missing": (fw + fl) - (ours["wins"] + ours["losses"]),
            })

    print(f"Matched {len(matched)} of {len(fhsaa_teams)} FHSAA 2A teams against our slugs")
    if absent:
        print(f"\nAbsent from our dataset ({len(absent)} — BFS did not reach them):")
        for a in absent:
            print(f"   {a['name']:<50} FHSAA record {a['fhsaa_record']}")
    if unmatched:
        print(f"\nUnmatched ({len(unmatched)} — need a MANUAL_SLUG_MAP entry):")
        for u in unmatched:
            print(f"   {u}")
    print()
    print(f"Record mismatches ({len(mismatches)} of {len(matched)}):")
    mismatches.sort(key=lambda m: -m["games_missing"])
    print(f"  {'school':<45} {'FHSAA':<12} {'OURS':<8} missing")
    for m in mismatches:
        print(f"  {m['name'][:43]:<45} {m['fhsaa_record']:<12} {m['our_record']:<8} {m['games_missing']:+d}g")

    mismatched_missing = sum(m["games_missing"] for m in mismatches if m["games_missing"] > 0)
    absent_missing = sum(a["fhsaa_games"] for a in absent)
    print()
    print(f"Games missing in matched-but-incomplete teams: {mismatched_missing}")
    print(f"Games missing because teams are absent entirely: {absent_missing}")
    print(f"Total FHSAA 2A games not in our dataset: {mismatched_missing + absent_missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
