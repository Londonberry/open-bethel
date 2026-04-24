"""
open-bethel: an open, auditable ranking engine for high school sports.

Core methods are exposed at the top level for convenience:

    from open_bethel import bethel_strengths, classical_rpi, indirection
    from open_bethel import load_games, contributions

The modules underneath can be imported directly if a specific method is
needed without pulling in the rest of the package.
"""
from __future__ import annotations

from .bethel import bethel_strengths
from .connectivity import indirection
from .contributions import loo_contributions
from .io import load_games
from .rpi import classical_rpi

__all__ = [
    "bethel_strengths",
    "classical_rpi",
    "indirection",
    "load_games",
    "loo_contributions",
]

__version__ = "0.1.0"
