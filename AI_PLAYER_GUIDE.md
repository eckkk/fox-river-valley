# AI Player Guide / 外部 AI 玩家指南

Fox River Valley is meant to be played through `new_game(...)` and `cmd(...)`, not by
reading source tables.

## Release variants

Fox River Valley has two public play packages:

- Text-only: use `fox_river_valley_p1_2_text_only.zip` and import
  `fox_river_valley_text`. This is the low-token route with no live map files.
- Observer Console: use `fox_river_valley_p1_2_observer.zip`, start the local
  observer page, then play through public commands.

Choose the route the human asked for. Do not force every player into the Observer
Console.

## Required startup behavior

External AI players such as Kimi must not write saves or observer files into
temporary PythonRun folders. Use the user's project root as the runtime home.

For Observer Console play, 先启动实时观战页，再开始 new_game。
If the AI can run local commands, start `Start_Fox_River_Valley.bat` or
`python -m fox_river_valley.play` before the first game command.
If the AI cannot launch local commands, ask the human to double-click
`Start_Fox_River_Valley.bat` first.

For Text-only play, do not start the observer server. Use:

```python
from fox_river_valley_text import cmd, new_game
```

Recommended setup:

```python
import os
os.environ["FRV_HOME"] = r"<path to the extracted Fox River Valley folder>"

from fox_river_valley_blind import cmd, new_game

print(cmd("runtime"))
print(cmd("observer"))
# Ask the human player which start mode they want before calling new_game.
```

If the human player has already opened `Start_Fox_River_Valley.bat`, keep using
the same `FRV_HOME`. In text-only play, `cmd("observer")` is not required; use
`cmd("runtime")` if paths need checking.

## Start mode protocol

不要直接替玩家选择 Yaya。Yaya is the Silas/Yaya demo profile, not the public default route.
先询问玩家要 solo、自定义家庭、还是 Silas/Yaya demo。

Before `new_game(...)`, ask:

```text
你想用哪种开局？
A. solo：new_game("seed")
B. 自定义家庭：new_game("seed", companion_name="Alex", companion_profile="default")
C. Silas/Yaya demo：new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")
```

Rules:

- Default public start is solo.
- Custom family mode should use a human-provided companion name,
  `companion_profile="default"`, and optional human-provided `family_species`.
- Silas/Yaya demo is allowed only when the human explicitly chooses it.
- Other AI players must be able to input their own name, profile, and kit species.

## Play rules

- Use `cmd("runtime")` first after connecting, and confirm the runtime root.
- Use the user-specified project root; do not rely on a temporary PythonRun current
  directory.
- Do not read source files, probability tables, hidden material tables, or recipe
  registries while playing.
- 不要读源码。
- 不要进入工程模式。
- 不能查未来 15/30/58 天天气表。
- 不能读代码找资源表或隐藏条件。
- 不能直接跳到第 N 天等稀有天气或稀有材料。
- 不能使用 debug/dev 命令推进普通游玩。
- Read the final `STATE {...}` after every command.
- Do not speedrun unless the human explicitly asks you to.
- Use `recap` and `options` to recover context.
- 每次 sleep 前检查 hunger、HP、companion、kit、perishable food。
- 如果处于 AI Playtest 模式，危险状态必须先处理，不能硬跳。

## Developer tests are not normal play

long_arc_smoke 属于开发测试，不得混入普通 AI 玩家模式。Prepared checkpoints are allowed for QA only, not
for public blind play.

## Observer

The human observer page should be served from:

```text
http://127.0.0.1:8765/observer.html
```

If the page is not updating, ask the human to run:

```text
Start_Fox_River_Valley.bat
```

or:

```text
python scripts/run_observer_server.py
```
