"""
Detect and collapse alias team slugs in the games CSV.

Two records are the same real game when they share date, sorted-score pair,
and at least one team slug. When that happens, the non-matching team slug on
each side is an alias of the other.

Algorithm:
  1. Group rows by (date, sorted_scores).
  2. Within each group, use union-find on team slugs: records that share a
     slug cluster together, and any "other side" slugs in the cluster are
     aliased to the cluster's canonical slug.
  3. Canonical slug: within each alias cluster, choose the shortest slug
     (canonical team URLs tend to be shorter than re-listings).
  4. Rewrite all rows with canonical slugs, then re-dedupe by
     (date, sorted_team_pair).

Writes the cleaned CSV in place after backing up to ./<name>.csv.bak.
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def group_by_date_scores(rows: list[dict]) -> dict:
    groups: dict = defaultdict(list)
    for r in rows:
        key = (
            r["date"],
            tuple(sorted([int(r["home_score"]), int(r["away_score"])])),
        )
        groups[key].append(r)
    return groups


def detect_aliases(rows: list[dict], min_collisions: int = 3) -> tuple[dict[str, str], dict]:
    """
    Return ({slug -> canonical_slug}, evidence).

    An alias is only recorded when the two candidate slugs collide on at least
    `min_collisions` distinct (date, score, shared-opponent) tuples. A single
    accidental same-date-same-score collision between two unrelated teams
    that happen to share an opponent is common enough that the threshold
    needs real evidence before collapsing.
    """
    # Count collisions per unordered-candidate-pair.
    pair_collisions: dict[tuple[str, str], int] = defaultdict(int)

    groups = group_by_date_scores(rows)
    for key, rs in groups.items():
        if len(rs) < 2:
            continue
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a_pair = {rs[i]["home_team"], rs[i]["away_team"]}
                b_pair = {rs[j]["home_team"], rs[j]["away_team"]}
                shared = a_pair & b_pair
                if len(shared) != 1:
                    continue
                only_a = (a_pair - shared).pop()
                only_b = (b_pair - shared).pop()
                pk = tuple(sorted([only_a, only_b]))
                pair_collisions[pk] += 1

    # Only union pairs that cleared the threshold.
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if (len(rx), rx) <= (len(ry), ry):
            parent[ry] = rx
        else:
            parent[rx] = ry

    evidence: dict = {}
    for (a, b), n in pair_collisions.items():
        if n >= min_collisions:
            union(a, b)
            evidence[(a, b)] = n

    aliases: dict[str, str] = {}
    for slug in parent:
        root = find(slug)
        if root != slug:
            aliases[slug] = root

    # Also return the full collision table for audit.
    return aliases, pair_collisions


def apply_and_dedupe(rows: list[dict], aliases: dict[str, str]) -> list[dict]:
    def canon(s: str) -> str:
        return aliases.get(s, s)

    seen_keys: set = set()
    out: list[dict] = []
    for r in rows:
        home = canon(r["home_team"])
        away = canon(r["away_team"])
        key = (r["date"], *sorted([home, away]))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append({
            "date": r["date"],
            "home_team": home,
            "away_team": away,
            "home_score": r["home_score"],
            "away_score": r["away_score"],
            "game_type": r.get("game_type", "regular"),
        })
    out.sort(key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    return out


def write(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["date", "home_team", "away_team", "home_score", "away_score", "game_type"],
        )
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                "phase0/games-fhsaa-fl-2026.csv")
    path = path.resolve()
    rows = load(path)
    print(f"Loaded {len(rows)} rows from {path}")

    aliases, collisions = detect_aliases(rows, min_collisions=3)
    print(f"Detected {len(aliases)} alias slugs (≥3 collisions each):")
    for src, dst in sorted(aliases.items()):
        n = max(collisions.get((src, dst), 0), collisions.get((dst, src), 0))
        print(f"  {src}  →  {dst}   ({n} collisions)")

    # Show one-off collisions below threshold, for audit.
    below = [(p, n) for p, n in collisions.items() if 1 <= n < 3]
    if below:
        below.sort(key=lambda x: -x[1])
        print(f"\n{len(below)} pairs collided under threshold (NOT aliased):")
        for (a, b), n in below[:15]:
            print(f"  {a}  ↔  {b}   ({n}x)")
        if len(below) > 15:
            print(f"  … and {len(below) - 15} more")

    out = apply_and_dedupe(rows, aliases)
    print(f"\nAfter canonicalization + re-dedupe: {len(out)} rows "
          f"({len(rows) - len(out)} collapsed)")

    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copyfile(path, bak)
    write(out, path)
    print(f"Wrote cleaned CSV to {path}")
    print(f"Backup at {bak}")


if __name__ == "__main__":
    main()
