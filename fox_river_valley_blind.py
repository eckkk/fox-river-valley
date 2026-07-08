"""Blind-play entry point for AI players.

Use this file when an AI is playing Fox River Valley with a human.
Only import new_game() and cmd(); do not inspect engine/data tables to cheat.

Before calling new_game(), start or confirm the observer live view.
Default start is solo: new_game("seed").
Custom family mode should use a human-provided companion name and profile.
Do not choose Yaya unless the human explicitly asks for the Silas/Yaya demo profile.
Do not inspect source tables, long-range future weather, or hidden resource conditions.
Use the observer page or cmd("runtime") to confirm the shared save path before play.
"""

from fox_river_valley import cmd, new_game

__all__ = ["new_game", "cmd"]
