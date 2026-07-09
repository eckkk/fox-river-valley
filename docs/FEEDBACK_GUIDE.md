# Fox River Valley Feedback Guide

Fox River Valley is built for fair AI blind play, human observation, and
human-AI co-play. The most useful feedback tells us what an AI could understand
from public game output, where it got confused, and what made the run fun to
watch.

## Fair Blind Play Setup

Ask the AI player to use only public player-facing material:

- `README.md`
- `AI_PLAYER_GUIDE.md`
- `TEXT_ONLY_PLAYER_GUIDE.md`
- `CO_PLAY_PROTOCOL.md`
- command output from `new_game(...)` and `cmd(...)`
- the final `STATE {...}` line returned by each command

The AI player should not inspect:

- source code
- tests
- resource tables
- probability tables
- hidden material conditions
- future weather tables
- private local saves

## Recommended Playtest Rhythm

- Start with solo, custom family, or the explicit Silas/Yaya demo route.
- Run only 1-2 commands per turn unless the human says otherwise.
- Read the final `STATE {...}` line before choosing the next action.
- Use `recap`, `options`, `status`, `weather`, `inventory`, `home`, and
  `check companion` when context is unclear.
- Stop and ask the human before home naming, commitment, ceremony, kit/family
  milestones, major danger, or Game Over risk.

## What To Include

Please include:

- AI model or agent used
- start mode: solo, custom family, or Silas/Yaya demo
- package used: text-only, Observer Console, or source checkout
- seed and difficulty/death mode
- command transcript or important excerpts
- short summaries of key `STATE {...}` lines
- where the AI got stuck or guessed wrong
- bugs, confusing text, or unfair hidden assumptions
- moments that were funny, cozy, surprising, or boring

## Transcript Template

```text
AI model:
Package/mode:
Seed:
Difficulty/death mode:
Start route:

Turn 1
Command:
Result summary:
STATE summary:
AI decision:
Human intervention:

Confusion points:
- ...

Bugs:
- ...

Suggestions:
- ...
```

## Feedback Areas

We especially want feedback about:

- AI readability: did public output give enough information?
- Resource hints: water, fiber, reeds, wood, clay, food, and shelter materials.
- Home progression: house names, decorations, tool crafting, and cozy goals.
- Observer Console: was it useful or fun for a human watching the AI?
- Balance: hunger, weather, spoilage, rare materials, and failure pressure.
- Funny events: `stinky_shoe`, spoiled food, strange AI choices, or other
  moments humans enjoyed watching.

## Report Format

Open a GitHub issue or share a short playtest note with:

- a concise title
- the transcript or excerpt
- what the AI knew at the time
- what you expected to happen
- what actually happened
- whether this is a bug, balance issue, documentation issue, or feature request

Chinese feedback is welcome.

中文反馈也欢迎：请尽量附上 AI 型号、开局模式、命令记录、卡住的位置、bug 截图或观战时觉得好笑/不好玩的地方。
