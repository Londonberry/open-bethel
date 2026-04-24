"""
Build phase0/games-district-3-2a-2026.csv from public Jacksonville-area
high school baseball schedules (fhsaa.com, jacksonvillehighschoolbaseball.com,
esj.org).

Reproducibility: re-running this script regenerates the CSV. The raw schedule
entries below were compiled by fetching each team's public varsity-schedule
page on 2026-04-24; sources cited in phase0/README.md.

The five teams of interest are FHSAA Class 2A Region 1 District 3 (2026):
Bishop Snyder, Bolles, Episcopal School of Jacksonville, Providence,
Trinity Christian Academy.

Each team's full-season schedule is included (all games, not just
intra-district) so that opponent-of-opponent graph chains reach beyond
the district for strength-of-schedule calculation.
"""
from __future__ import annotations
import csv
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "phase0" / "games-district-3-2a-2026.csv"

# Canonical team IDs. Order defines dedup precedence: when two focus-teams
# played each other, the game is recorded once, attached to the team that
# appears earlier in this tuple.
FOCUS_TEAMS = (
    "bishop-snyder",
    "bolles",
    "episcopal",
    "providence",
    "trinity-christian",
)

# Raw-name → canonical-slug map. Applies to opponent names as they appear in
# scraped schedule pages. Only entries that actually appear in the data below
# need to be here.
NAME_MAP = {
    # Focus teams (aliases that appear as opponents on other teams' schedules)
    "Bishop Snyder Cardinals": "bishop-snyder",
    "Bolles": "bolles",
    "Bolles Bulldogs": "bolles",
    "Episcopal School Eagles": "episcopal",
    "Providence": "providence",
    "Providence Stallions": "providence",
    "Trinity Christian Academy": "trinity-christian",
    "Trinity Christian Academy (District SF)": "trinity-christian",
    "Providence (District QF)": "providence",
    # Non-focus opponents (slugs created as-needed)
    "Bishop Kenny": "bishop-kenny",
    "Bishop Kenny Crusaders": "bishop-kenny",
    "Creekside": "creekside",
    "Creekside Knights": "creekside",
    "Trinity Catholic School": "trinity-catholic",
    "Trinity Catholic Celtics": "trinity-catholic",
    "Suwannee": "suwannee",
    "Suwannee Bulldogs": "suwannee",
    "Flagler-Palm Coast": "flagler-palm-coast",
    "Flagler Palm Coast": "flagler-palm-coast",
    "West Nassau": "west-nassau",
    "Columbia": "columbia",
    "Columbia Tigers": "columbia",
    "Fletcher": "fletcher",
    "Fletcher Senators": "fletcher",
    "Yulee": "yulee",
    "St. John Paul II": "st-john-paul-ii",
    "Cardinal Gibbons Catholic": "cardinal-gibbons",
    "Santa Fe": "santa-fe",
    "Beachside": "beachside",
    "Beachside Barracudas": "beachside",
    "Stanton": "stanton",
    "Christ's Church Academy": "christs-church-academy",
    "Bartram Trail": "bartram-trail",
    "Bartram Trail Bears": "bartram-trail",
    "St. Francis": "st-francis",
    "Pedro Menendez": "pedro-menendez",
    "Sandalwood": "sandalwood",
    "Sandalwood Saints": "sandalwood",
    "Fort Dorchester": "fort-dorchester",
    "University Christian": "university-christian",
    "University Christian Christians": "university-christian",
    "St. Augustine": "st-augustine",
    "Eagle's View": "eagles-view",
    "Clay": "clay",
    "Clay Blue Devils": "clay",
    "Nease": "nease",
    "Nease Panthers": "nease",
    "Fernandina Beach Pirates": "fernandina-beach",
    "Lincoln Trojans": "lincoln",
    "Baldwin Indians": "baldwin",
    "Central, AL": "central-al",
    "Newnan": "newnan",
    "Morgan County, GA": "morgan-county-ga",
    "Northridge, AL": "northridge-al",
    "Farragut, TN": "farragut-tn",
    "South Walton Seahawks": "south-walton",
    "Hartselle": "hartselle",
    "West Broward Bobcats": "west-broward",
    "Ponte Vedra Sharks": "ponte-vedra",
    "North Oconee": "north-oconee",
    "North Gwinnett, GA": "north-gwinnett-ga",
    "Parkview, GA": "parkview-ga",
    "Tocoi Creek Toros": "tocoi-creek",
    "Oakleaf Knights": "oakleaf",
    "St. Joseph Academy": "st-joseph-academy",
    "Covenant School Warriors": "covenant-school",
    "Naples Golden Eagles": "naples",
    "Knoxville Catholic, TN": "knoxville-catholic-tn",
    "Barron Collier Cougars": "barron-collier",
    "St. John's Country Day": "st-johns-country-day",
    "Mount Horeb, WI": "mount-horeb-wi",
    "Palatka Panthers": "palatka",
    "John Carroll Rams": "john-carroll",
    "Winter Park Wildcats": "winter-park",
    "Hewitt-Trussville, AL": "hewitt-trussville-al",
    "North Marion Colts": "north-marion",
    "DeLand Bulldogs": "deland",
    "Lowndes, GA": "lowndes-ga",
    "Richmond Hill, GA": "richmond-hill-ga",
    "Maclay Marauders": "maclay",
    "Magnolia Heights, MS": "magnolia-heights-ms",
    "Jesuit Tigers": "jesuit",
    "Edmond Memorial": "edmond-memorial",
    "Orange Lutheran, CA": "orange-lutheran-ca",
    "Don Bosco Prep, NJ": "don-bosco-prep-nj",
    "Baylor School": "baylor-school",
}


def slugify(name: str) -> str:
    if name in NAME_MAP:
        return NAME_MAP[name]
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# Per-team schedules. Each row: (date_iso, opponent_raw, home_away, team_score, opp_score, game_type)
# game_type: "regular" | "district-tournament" | "regional"

BISHOP_SNYDER = [
    ("2026-02-11", "Fernandina Beach Pirates", "away", 2, 0, "regular"),
    ("2026-02-14", "Lincoln Trojans", "away", 4, 3, "regular"),
    ("2026-02-17", "Baldwin Indians", "home", 11, 0, "regular"),
    ("2026-02-20", "Suwannee Bulldogs", "home", 5, 1, "regular"),
    ("2026-02-27", "Central, AL", "away", 8, 3, "regular"),
    ("2026-02-27", "Newnan", "away", 10, 0, "regular"),
    ("2026-02-28", "Morgan County, GA", "away", 2, 1, "regular"),
    ("2026-02-28", "Northridge, AL", "home", 1, 4, "regular"),
    ("2026-03-05", "Sandalwood Saints", "home", 2, 1, "regular"),
    ("2026-03-06", "Providence Stallions", "away", 12, 2, "regular"),
    ("2026-03-12", "Farragut, TN", "away", 11, 0, "regular"),
    ("2026-03-13", "South Walton Seahawks", "away", 2, 1, "regular"),
    ("2026-03-14", "Hartselle", "home", 6, 5, "regular"),
    ("2026-03-18", "West Broward Bobcats", "home", 0, 2, "regular"),
    ("2026-03-19", "Columbia Tigers", "home", 1, 3, "regular"),
    ("2026-03-24", "Bolles Bulldogs", "away", 11, 9, "regular"),
    ("2026-03-25", "Fletcher Senators", "home", 8, 1, "regular"),
    ("2026-03-27", "Bartram Trail Bears", "away", 4, 5, "regular"),
    ("2026-03-31", "Ponte Vedra Sharks", "home", 7, 1, "regular"),
    ("2026-04-01", "Trinity Catholic Celtics", "home", 2, 5, "regular"),
    ("2026-04-07", "North Oconee", "home", 6, 1, "regular"),
    ("2026-04-08", "North Gwinnett, GA", "home", 9, 3, "regular"),
    ("2026-04-09", "Parkview, GA", "home", 9, 2, "regular"),
    ("2026-04-16", "Bolles Bulldogs", "home", 8, 1, "regular"),
    ("2026-04-17", "Trinity Christian Academy", "away", 10, 11, "district-tournament"),
]

BOLLES = [
    ("2026-02-10", "Tocoi Creek Toros", "away", 2, 9, "regular"),
    ("2026-02-13", "Oakleaf Knights", "home", 11, 3, "regular"),
    ("2026-02-19", "St. Joseph Academy", "home", 8, 4, "regular"),
    ("2026-02-20", "Covenant School Warriors", "home", 7, 4, "regular"),
    ("2026-02-24", "Creekside Knights", "away", 2, 6, "regular"),
    ("2026-02-26", "Baldwin Indians", "home", 1, 11, "regular"),
    ("2026-02-28", "University Christian Christians", "home", 5, 3, "regular"),
    ("2026-03-04", "Fernandina Beach Pirates", "away", 1, 0, "regular"),
    ("2026-03-05", "Bishop Kenny Crusaders", "home", 2, 1, "regular"),
    ("2026-03-10", "Naples Golden Eagles", "away", 17, 1, "regular"),
    ("2026-03-11", "Knoxville Catholic, TN", "home", 10, 5, "regular"),
    ("2026-03-12", "Barron Collier Cougars", "away", 3, 1, "regular"),
    ("2026-03-18", "Bartram Trail Bears", "home", 4, 9, "regular"),
    ("2026-03-19", "Ponte Vedra Sharks", "home", 10, 7, "regular"),
    ("2026-03-20", "Episcopal School Eagles", "home", 2, 3, "regular"),
    ("2026-03-24", "Bishop Snyder Cardinals", "home", 9, 11, "regular"),
    ("2026-03-26", "Sandalwood Saints", "home", 3, 2, "regular"),
    ("2026-03-27", "Providence Stallions", "home", 8, 1, "regular"),
    ("2026-03-30", "St. John's Country Day", "home", 3, 2, "regular"),
    ("2026-03-31", "Mount Horeb, WI", "home", 16, 1, "regular"),
    ("2026-04-01", "Nease Panthers", "away", 15, 2, "regular"),
    ("2026-04-07", "Parkview, GA", "home", 2, 0, "regular"),
    ("2026-04-08", "North Oconee", "home", 10, 7, "regular"),
    ("2026-04-09", "North Gwinnett, GA", "home", 11, 6, "regular"),
    ("2026-04-16", "Bishop Snyder Cardinals", "away", 1, 8, "regular"),
]

EPISCOPAL = [
    ("2026-02-03", "Bishop Kenny", "away", 4, 3, "regular"),
    ("2026-02-05", "Creekside", "away", 2, 11, "regular"),
    ("2026-02-10", "Trinity Catholic School", "home", 4, 7, "regular"),
    ("2026-02-11", "Suwannee", "away", 6, 7, "regular"),
    ("2026-02-13", "Flagler-Palm Coast", "away", 5, 6, "regular"),
    ("2026-02-17", "West Nassau", "home", 10, 0, "regular"),
    ("2026-02-19", "Columbia", "away", 3, 13, "regular"),
    ("2026-02-20", "Fletcher", "home", 1, 4, "regular"),
    ("2026-02-24", "Yulee", "home", 11, 1, "regular"),
    ("2026-02-27", "St. John Paul II", "away", 0, 9, "regular"),
    ("2026-02-28", "Cardinal Gibbons Catholic", "away", 5, 1, "regular"),
    ("2026-03-04", "Santa Fe", "home", 10, 4, "regular"),
    ("2026-03-05", "Beachside", "home", 8, 1, "regular"),
    ("2026-03-11", "Stanton", "away", 12, 0, "regular"),
    ("2026-03-13", "Christ's Church Academy", "away", 14, 5, "regular"),
    ("2026-03-17", "Bartram Trail", "home", 2, 6, "regular"),
    ("2026-03-18", "St. Francis", "away", 8, 0, "regular"),
    ("2026-03-20", "Bolles", "away", 3, 2, "regular"),
    ("2026-03-25", "Pedro Menendez", "away", 13, 2, "regular"),
    ("2026-03-26", "Providence", "away", 5, 3, "regular"),
    ("2026-03-27", "Sandalwood", "away", 3, 4, "regular"),
    ("2026-03-30", "Fort Dorchester", "home", 2, 0, "regular"),
    ("2026-03-31", "University Christian", "away", 14, 3, "regular"),
    ("2026-04-01", "St. Augustine", "home", 6, 1, "regular"),
    ("2026-04-06", "Eagle's View", "home", 25, 5, "regular"),
    ("2026-04-07", "Clay", "home", 0, 5, "regular"),
    ("2026-04-10", "Nease", "away", 11, 2, "regular"),
    ("2026-04-14", "Providence", "away", 9, 5, "district-tournament"),
    ("2026-04-16", "Trinity Christian Academy", "away", 0, 9, "district-tournament"),
]

PROVIDENCE = [
    ("2026-02-10", "Fletcher Senators", "away", 6, 3, "regular"),
    ("2026-02-12", "Sandalwood Saints", "home", 3, 1, "regular"),
    ("2026-02-13", "University Christian", "home", 7, 6, "regular"),
    ("2026-02-17", "Palatka Panthers", "home", 12, 5, "regular"),
    ("2026-02-19", "St. John's Country Day", "away", 1, 10, "regular"),
    ("2026-02-21", "John Carroll Rams", "away", 4, 2, "regular"),
    ("2026-02-24", "Columbia Tigers", "away", 6, 4, "regular"),
    ("2026-02-27", "Creekside Knights", "away", 0, 7, "regular"),
    ("2026-03-03", "Clay Blue Devils", "away", 8, 0, "regular"),
    ("2026-03-05", "Flagler Palm Coast", "away", 10, 6, "regular"),
    ("2026-03-06", "Bishop Snyder Cardinals", "home", 2, 12, "regular"),
    ("2026-03-09", "Ponte Vedra Sharks", "away", 15, 7, "regular"),
    ("2026-03-11", "Winter Park Wildcats", "home", 6, 2, "regular"),
    ("2026-03-12", "Farragut, TN", "home", 2, 5, "regular"),
    ("2026-03-13", "Hewitt-Trussville, AL", "away", 0, 6, "regular"),
    ("2026-03-18", "North Marion Colts", "home", 1, 2, "regular"),
    ("2026-03-18", "North Marion Colts", "away", 1, 3, "regular"),
    ("2026-03-24", "DeLand Bulldogs", "away", 12, 2, "regular"),
    ("2026-03-26", "Episcopal School Eagles", "home", 3, 5, "regular"),
    ("2026-03-27", "Bolles Bulldogs", "away", 1, 8, "regular"),
    ("2026-03-30", "Columbia Tigers", "home", 2, 1, "regular"),
    ("2026-03-31", "Beachside Barracudas", "away", 3, 5, "regular"),
    ("2026-04-02", "Ponte Vedra Sharks", "home", 3, 2, "regular"),
    ("2026-04-09", "Bartram Trail Bears", "away", 0, 6, "regular"),
    ("2026-04-14", "Episcopal School Eagles", "home", 5, 9, "district-tournament"),
]

TRINITY_CHRISTIAN = [
    ("2026-02-10", "Suwannee Bulldogs", "home", 4, 2, "regular"),
    ("2026-02-12", "Creekside Knights", "away", 0, 2, "regular"),
    ("2026-02-17", "Beachside Barracudas", "home", 10, 1, "regular"),
    ("2026-02-20", "Lowndes, GA", "away", 11, 3, "regular"),
    ("2026-02-21", "Richmond Hill, GA", "home", 5, 0, "regular"),
    ("2026-02-24", "Tocoi Creek Toros", "home", 5, 1, "regular"),
    ("2026-02-27", "North Marion Colts", "home", 7, 2, "regular"),
    ("2026-02-28", "Maclay Marauders", "home", 11, 1, "regular"),
    ("2026-03-03", "University Christian Christians", "away", 9, 2, "regular"),
    ("2026-03-05", "St. John's Country Day", "away", 3, 4, "regular"),
    ("2026-03-06", "St. John's Country Day", "home", 10, 8, "regular"),
    ("2026-03-12", "South Walton Seahawks", "away", 3, 7, "regular"),
    ("2026-03-13", "Magnolia Heights, MS", "home", 4, 3, "regular"),
    ("2026-03-13", "Lincoln Trojans", "home", 12, 3, "regular"),
    ("2026-03-17", "Columbia Tigers", "home", 4, 1, "regular"),
    ("2026-03-19", "Jesuit Tigers", "home", 2, 5, "regular"),
    ("2026-03-20", "West Broward Bobcats", "home", 5, 1, "regular"),
    ("2026-03-25", "Edmond Memorial", "away", 4, 3, "regular"),
    ("2026-03-26", "Orange Lutheran, CA", "away", 2, 3, "regular"),
    ("2026-03-27", "Don Bosco Prep, NJ", "away", 6, 11, "regular"),
    ("2026-03-28", "Baylor School", "away", 9, 7, "regular"),
    ("2026-04-02", "Clay Blue Devils", "home", 8, 1, "regular"),
    ("2026-04-03", "Clay Blue Devils", "away", 14, 0, "regular"),
    ("2026-04-07", "Baldwin Indians", "home", 10, 0, "regular"),
    ("2026-04-09", "Suwannee Bulldogs", "away", 3, 13, "regular"),
    ("2026-04-16", "Episcopal School Eagles", "home", 9, 0, "district-tournament"),
    ("2026-04-17", "Bishop Snyder Cardinals", "home", 11, 10, "district-tournament"),
]

SCHEDULES = {
    "bishop-snyder": BISHOP_SNYDER,
    "bolles": BOLLES,
    "episcopal": EPISCOPAL,
    "providence": PROVIDENCE,
    "trinity-christian": TRINITY_CHRISTIAN,
}


def main() -> None:
    seen: set[tuple[str, str, str]] = set()  # (date, low_team, high_team)
    rows: list[dict[str, object]] = []

    for focus, schedule in SCHEDULES.items():
        for date, opp_raw, home_away, ts, os_, gtype in schedule:
            opp = slugify(opp_raw)
            if opp == focus:
                raise ValueError(f"{focus} listed as its own opponent on {date}")
            pair_key = (date, *sorted((focus, opp)))
            if opp in FOCUS_TEAMS and pair_key in seen:
                continue
            seen.add(pair_key)

            if home_away == "home":
                home, away, hs, as_ = focus, opp, ts, os_
            else:
                home, away, hs, as_ = opp, focus, os_, ts

            rows.append({
                "date": date,
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "game_type": gtype,
            })

    rows.sort(key=lambda r: (r["date"], r["home_team"], r["away_team"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "home_team", "away_team", "home_score", "away_score", "game_type"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} games to {OUT}")


if __name__ == "__main__":
    main()
