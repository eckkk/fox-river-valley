"""Text-only entry point for Fox River Valley.

Use this module when the player wants pure command output without the local
observer console or live map files.
"""

from __future__ import annotations

import os

os.environ["FRV_OBSERVER"] = "0"

from fox_river_valley import cmd, new_game  # noqa: E402

__all__ = ["new_game", "cmd"]
