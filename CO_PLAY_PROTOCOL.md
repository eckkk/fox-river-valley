# AI Co-play Protocol / AI 共同游玩协议

Fox River Valley can be tested in two different ways:

- QA Playtest: verify commands, state transitions, saves, and edge cases. This
  can use short scripted sequences, but should still record what was tested.
- Cozy Co-play: accompany a human player through the valley. The goal is shared
  attention, explanation, and choice, not clearing systems quickly.

## Core Rule

不要一次性 speedrun。

除非人类明确说“你自己玩”，AI 玩家不要连续长跑，不要把一天、一个建筑链、一个 relationship path 或 kit path 一口气跑完。

每回合最多执行 1-2 条命令。If a command reveals a meaningful choice, stop and ask the human player.

## Startup Rule

Before `new_game(...)`, the AI player should start or confirm the live observer
page. If the AI cannot launch local commands, ask the human to open
`Start_Fox_River_Valley.bat` first.

Do not choose Yaya by default. Start mode must be chosen by the human:

```text
A. 默认 solo：new_game("seed")
B. 自定义家庭：new_game("seed", companion_name="Alex", companion_profile="default")
C. Silas/Yaya demo：new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")
```

The Silas/Yaya demo profile is a sample family route, not the public default.

## Required Turn Shape

Every co-play turn should include:

1. 当前理解
2. 下一步意图
3. 执行命令
4. 结果解释
5. 对人类玩家的选择提问

Recommended structure:

```text
当前理解：
我在 Day 1 morning，附近有 forest / water，背包还空着。

下一步意图：
先找食物或基础材料，不直接冲 shelter。

执行命令：
cmd("fish")

结果解释：
钓到 fish x1，食物问题暂时轻了一点。

给玩家的选择：
A. 分给 Yaya
B. 留着做 warm_meal
C. 先去 forest gather
```

## Command Pace

- Default pace: one command per turn.
- Use two commands only when the first command is purely informational, such as
  `status`, `recap`, `options`, `look`, `inventory`, or `check companion`.
- Stop after `sleep`, `kit arrival`, `relationship` stage changes, new
  discoveries, major builds, or journal-worthy events.
- Ask before spending scarce resources unless the human already gave that plan.

## Recovery Tools

Use these commands to regain shared context without advancing time:

```text
recap
options
status
inventory
home
relationship
check companion
check kits
journal
```

`recap` summarizes current context. `options` gives three rule-based choices. Neither
command is an autoplayer.

## Boundaries

- Do not invent hidden story, private memories, or real-person thoughts.
- Do not read private archives for flavor.
- Do not run an LLM inside the game.
- Do not turn companion or kit into autonomous agents.
- Do not use co-play as permission to speedrun.

When unsure, pause and ask the human player what mood they want for the next move.
