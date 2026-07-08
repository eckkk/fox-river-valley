# Fox River Valley Release Checklist

Use this before publishing a zip or handing the build to another AI player.

## Verification

- Run `python -m unittest discover -v`.
- Run `python -m compileall -q fox_river_valley scripts tests`.
- Build the release zip with `python scripts/package_release.py`.
- Check zip paths are POSIX `/` paths, not Windows backslash paths.
- Confirm the zip contains `README.md`, `CO_PLAY_PROTOCOL.md`, `PLAY_SESSION_TEMPLATE.md`, `tool-schema.json`, and `fox_river_valley_blind.py`.

## Smoke Tests

- Human quick smoke: start `new_game("12071008")`, then run `look`, `options`, `recap`, `save`, `load`.
- blind play smoke test: import from `fox_river_valley_blind`, start a family game, then run `recap` and `options`.
- co-play smoke test: follow one turn from `PLAY_SESSION_TEMPLATE.md` and stop after offering choices.
- save/load smoke test: create a game, build or mutate a simple home checkpoint, save, load, and compare key STATE fields.
- long arc smoke: run `python scripts/long_arc_smoke.py` or the matching unittest segment.

## Boundary Check

- Confirm no private archive has been read or bundled.
- Confirm no LLM API is connected.
- Confirm no UI or Web UI is required.
- Confirm no new gameplay system was added in a release-prep patch.
- Confirm AI co-play docs still warn against speedrun behavior.

## Documentation Check

- README has Human Quick Start, AI Blind Play, and Developer / QA Mode.
- `tool-schema.json` describes `new_game` and `cmd`.
- `CO_PLAY_PROTOCOL.md` and `PLAY_SESSION_TEMPLATE.md` are included.
- `DATA_REGISTRY_GUIDE.md` explains how to add registry items without making Silas/Yaya defaults global.
