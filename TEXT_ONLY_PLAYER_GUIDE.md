# Fox River Valley Text-Only Guide

Use this release when you want pure text play without the Observer Console or live map.

```python
from fox_river_valley_text import cmd, new_game

print(new_game("12071008"))
print(cmd("look"))
print(cmd("options"))
print(cmd("gather"))
```

This entry point disables observer file generation for the current Python
process. It still uses the same core game, save format, rules, and final
`STATE {...}` output as the Observer release.

## Low-Token Co-Play

- Run at most 1-2 commands per turn.
- Read the final `STATE {...}` line before deciding the next action.
- Prefer `look`, `status`, `inventory`, `options`, and `recap`.
- Use `map` only when the player asks for spatial context.
- Avoid pasting long transcripts back to the human player.
- Stop and ask before major milestones, danger, kit arrival, proposal, ceremony, or Game
  Over risk.

## Start Modes

```python
new_game("seed")
new_game("seed", companion_name="Alex", companion_profile="default")
new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")
```

The Silas/Yaya profile is a demo route, not the default route.
For public blind play, start solo unless the human explicitly chooses a family
mode.
