"""
Generate phase0/team_classes.json mapping each in-state team slug in our
dataset to its FHSAA classification (1A-7A, Independent, Rural, Unknown).

Source of truth is the FHSAA baseball rankings feed — the same JSON the
official rankings page consumes. Re-run this whenever FHSAA reclassifies
teams (typically once per multi-year cycle):

    python3 site/build_team_classes.py

The output JSON is checked in; build.py loads it and attaches `class` to
each ranking row. Out-of-state teams (no FHSAA classification) get no
entry and render with no class chip.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fhsaa_crosscheck import (  # noqa: E402
    FHSAA_RANKINGS_URL,
    MANUAL_SLUG_MAP,
    MISSING_SENTINEL,
    match_slug,
)
import subprocess  # noqa: E402

DATA_JSON = ROOT / "site" / "public" / "data.json"
OUT_PATH = ROOT / "phase0" / "team_classes.json"

# Map FHSAA division names to short class labels for display.
DIVISION_LABEL = {
    "Division 1A": "1A",
    "Division 2A": "2A",
    "Division 3A": "3A",
    "Division 4A": "4A",
    "Division 5A": "5A",
    "Division 6A": "6A",
    "Division 7A": "7A",
    "Division Independent ": "Indep",
    "Division Rural": "Rural",
    "Division Unknown": "Unk",
}


def main() -> int:
    if not DATA_JSON.exists():
        print(f"Build site data first ({DATA_JSON} not found)", file=sys.stderr)
        return 1
    ours = json.load(DATA_JSON.open())
    our_slugs = {r["team"] for r in ours["rankings"]}

    result = subprocess.run(
        ["curl", "-sS", "-A", "Mozilla/5.0", FHSAA_RANKINGS_URL],
        capture_output=True,
        text=True,
        check=True,
    )
    feed = json.loads(result.stdout)

    out: dict[str, str] = {}
    counts: dict[str, int] = {}
    unmatched: list[tuple[str, str]] = []
    absent: list[tuple[str, str]] = []
    for div in feed["Divisions"]:
        label = DIVISION_LABEL.get(div["Name"], div["Name"])
        for t in div["Teams"]:
            name = t["SchoolName"]
            slug = match_slug(name, our_slugs)
            if slug is MISSING_SENTINEL:
                absent.append((label, name))
                continue
            if not slug:
                unmatched.append((label, name))
                continue
            if slug in out and out[slug] != label:
                # Same slug shows up in two divisions — should be impossible
                # for a real team. Last write wins; surface it for review.
                print(f"  COLLISION: {slug} -> {out[slug]} & {label}", file=sys.stderr)
            out[slug] = label
            counts[label] = counts.get(label, 0) + 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(f"Wrote {OUT_PATH} — {len(out)} mapped slugs across {len(counts)} classes")
    for label in sorted(counts):
        print(f"  {label}: {counts[label]}")
    if unmatched:
        print(f"\nUnmatched ({len(unmatched)} — add to MANUAL_SLUG_MAP):")
        for cls, name in unmatched[:20]:
            print(f"  [{cls}] {name}")
        if len(unmatched) > 20:
            print(f"  … and {len(unmatched) - 20} more")
    if absent:
        print(f"\nAbsent from our dataset ({len(absent)}):")
        for cls, name in absent[:10]:
            print(f"  [{cls}] {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
