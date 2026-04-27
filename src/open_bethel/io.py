"""CSV loader for the generic game-list input contract."""
from __future__ import annotations

import csv
from pathlib import Path


def load_games(path: Path | str) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Read a games CSV and return (sorted team list, list of (winner, loser) tuples).

    Required columns: date, home_team, away_team, home_score, away_score.
    Tied games are dropped — Bethel's model is undefined for ties. Team
    identifiers are free-form strings; the engine is identifier-agnostic.
    """
    path = Path(path)
    games: list[tuple[str, str]] = []
    teams: set[str] = set()
    with path.open() as f:
        for row in csv.DictReader(f):
            home = row["home_team"].strip()
            away = row["away_team"].strip()
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            teams.update((home, away))
            if hs == as_:
                continue
            winner, loser = (home, away) if hs > as_ else (away, home)
            games.append((winner, loser))
    return sorted(teams), games


def load_games_with_metadata(
    path: Path | str,
) -> tuple[list[str], list[dict]]:
    """
    Load games with full per-row metadata (date, home/away, scores, type).

    Returns (sorted team list, list of game dicts). Use this when the ranking
    pipeline needs more than winner/loser — for example, chronological
    train/test splitting or per-game contribution analysis.
    """
    path = Path(path)
    rows: list[dict] = []
    teams: set[str] = set()
    with path.open() as f:
        for row in csv.DictReader(f):
            home = row["home_team"].strip()
            away = row["away_team"].strip()
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            teams.update((home, away))
            if hs == as_:
                continue
            winner, loser = (home, away) if hs > as_ else (away, home)
            rows.append({
                "date": row["date"],
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "game_type": row.get("game_type", "regular"),
                "winner": winner,
                "loser": loser,
            })
    return sorted(teams), rows
