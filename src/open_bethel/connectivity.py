"""Pairwise indirection diagnostic for the opponent graph."""
from __future__ import annotations

from collections import defaultdict, deque


def indirection(
    teams: list[str],
    games: list[tuple[str, str]],
    a: str,
    b: str,
) -> int | None:
    """
    Shortest-path indirection in the opponent graph between two teams.

    0    — teams played each other at least once
    1    — teams share a common opponent
    n    — requires n-hop chain through opponents
    None — teams live in different graph components

    This is the diagnostic Bethel's §8 calls out as the method's only
    genuinely unsolved issue: if two teams have no transitive path through
    the graph of games, their relative strength is not defined by the data.
    """
    if a == b:
        return 0
    adj: dict[str, set[str]] = defaultdict(set)
    for w, l in games:
        adj[w].add(l)
        adj[l].add(w)
    if b in adj[a]:
        return 0

    visited = {a}
    frontier = deque([(a, 0)])
    while frontier:
        node, depth = frontier.popleft()
        for nxt in adj[node]:
            if nxt == b:
                return depth
            if nxt not in visited:
                visited.add(nxt)
                frontier.append((nxt, depth + 1))
    return None
