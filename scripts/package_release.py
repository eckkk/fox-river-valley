from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INCLUDE = (
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CO_PLAY_PROTOCOL.md",
    "AI_PLAYER_GUIDE.md",
    "PLAY_SESSION_TEMPLATE.md",
    "TEXT_ONLY_PLAYER_GUIDE.md",
    "RELEASE_CHECKLIST.md",
    "DATA_REGISTRY_GUIDE.md",
    "tool-schema.json",
    "Start_Fox_River_Valley.bat",
    "fox_river_valley_blind.py",
    "fox_river_valley_text.py",
    "observer",
    "fox_river_valley",
    "saves",
    "tests",
    "scripts",
)

OBSERVER_OUTPUT = Path("dist/fox_river_valley_p1_2_observer.zip")
TEXT_ONLY_OUTPUT = Path("dist/fox_river_valley_p1_2_text_only.zip")
DEFAULT_OUTPUT = OBSERVER_OUTPUT
VALID_VARIANTS = {"observer", "text_only"}
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
SKIP_RUNTIME_FILES = {
    "fox_river_valley.save.json",
    "fox_river_valley.manual.save.json",
    "observer_state.json",
    "observer_state.tmp.json",
}
TEXT_ONLY_SKIP_PATHS = {
    "Start_Fox_River_Valley.bat",
    "observer",
    "scripts/run_observer_server.py",
    "scripts/start_observer.ps1",
    "fox_river_valley/play.py",
}

BOOTSTRAP_OBSERVER_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fox River Valley Observer</title>
  <style>
    body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 2rem; background: #f4f0e8; color: #28231c; }
    main { max-width: 760px; background: #fffaf0; border: 1px solid #d6cabb; border-radius: 8px; padding: 1rem; }
    input { min-width: 260px; padding: 0.55rem; }
    button { padding: 0.55rem 0.75rem; margin: 0.25rem; }
    pre { white-space: pre-wrap; background: #f8f4eb; padding: 0.75rem; border-radius: 6px; }
  </style>
</head>
<body>
  <main>
    <h1>Fox River Valley Observer</h1>
    <p>观战页已启动。输入命令后，游戏会生成完整地图和状态面板。</p>
    <input id="command-input" placeholder="例如 gather">
    <button id="run-command">执行</button>
    <div>
      <button data-command="look">look</button>
      <button data-command="status">status</button>
      <button data-command="inventory">inventory</button>
      <button data-command="map">map</button>
      <button data-command="gather">gather</button>
      <button data-command="fish">fish</button>
      <button data-command="return home">return home</button>
      <button data-command="sleep">sleep</button>
    </div>
    <pre id="output">等待命令。</pre>
  </main>
  <script>
    async function run(command) {
      const clean = String(command || "").trim();
      if (!clean) return;
      const output = document.getElementById("output");
      output.textContent = "执行中：" + clean;
      try {
        const response = await fetch("./cmd", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({command: clean})
        });
        const data = await response.json();
        output.textContent = data.output || "已执行。";
        setTimeout(() => location.reload(), 300);
      } catch (error) {
        output.textContent = "Observer is not connected. Please run Start_Fox_River_Valley.bat or python scripts/run_observer_server.py.";
      }
    }
    document.getElementById("run-command").addEventListener("click", () => run(document.getElementById("command-input").value));
    document.getElementById("command-input").addEventListener("keydown", (event) => {
      if (event.key === "Enter") run(event.target.value);
    });
    document.querySelectorAll("[data-command]").forEach((button) => {
      button.addEventListener("click", () => run(button.getAttribute("data-command")));
    });
  </script>
</body>
</html>
"""


def _skip_for_variant(relative_path: str, variant: str) -> bool:
    if variant != "text_only":
        return False
    if relative_path in TEXT_ONLY_SKIP_PATHS:
        return True
    return any(relative_path.startswith(f"{path}/") for path in TEXT_ONLY_SKIP_PATHS)


def _iter_package_files(root: Path, names: tuple[str, ...] = DEFAULT_INCLUDE, variant: str = "observer"):
    root = root.resolve()
    for name in names:
        normalized_name = Path(name).as_posix()
        if _skip_for_variant(normalized_name, variant):
            continue
        path = root / name
        if not path.exists():
            continue
        if path.is_file():
            relative = path.resolve().relative_to(root).as_posix()
            if not _skip_for_variant(relative, variant):
                yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_dir():
                continue
            if any(part in SKIP_DIRS for part in child.relative_to(root).parts):
                continue
            if child.suffix in SKIP_SUFFIXES:
                continue
            if child.name in SKIP_RUNTIME_FILES:
                continue
            relative = child.resolve().relative_to(root).as_posix()
            if _skip_for_variant(relative, variant):
                continue
            yield child


def default_release_outputs(root: Path | str = Path(".")) -> list[Path]:
    root_path = Path(root).resolve()
    return [root_path / TEXT_ONLY_OUTPUT, root_path / OBSERVER_OUTPUT]


def build_release_zip(root: Path | str = Path("."), output: Path | str = DEFAULT_OUTPUT, variant: str = "observer") -> Path:
    from fox_river_valley.observer import build_start_screen_state, render_start_screen_html

    if variant not in VALID_VARIANTS:
        raise ValueError(f"invalid release variant: {variant}")
    root_path = Path(root).resolve()
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    bootstrap_observer_html = render_start_screen_html()
    bootstrap_observer_state = json.dumps(
        build_start_screen_state(),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        wrote_bootstrap_observer = False
        wrote_bootstrap_state = False
        for path in _iter_package_files(root_path, variant=variant):
            arcname = path.resolve().relative_to(root_path).as_posix()
            if arcname == "observer/observer.html":
                if not wrote_bootstrap_observer:
                    archive.writestr(arcname, bootstrap_observer_html)
                    wrote_bootstrap_observer = True
                continue
            if arcname == "observer/observer_state.json":
                if not wrote_bootstrap_state:
                    archive.writestr(arcname, bootstrap_observer_state)
                    wrote_bootstrap_state = True
                continue
            archive.write(path, arcname)
        if variant == "observer" and not wrote_bootstrap_observer:
            archive.writestr("observer/observer.html", bootstrap_observer_html)
        if variant == "observer" and not wrote_bootstrap_state:
            archive.writestr("observer/observer_state.json", bootstrap_observer_state)
    return output_path


def build_default_release_zips(root: Path | str = Path(".")) -> list[Path]:
    root_path = Path(root).resolve()
    text_zip = build_release_zip(root_path, root_path / TEXT_ONLY_OUTPUT, variant="text_only")
    observer_zip = build_release_zip(root_path, root_path / OBSERVER_OUTPUT, variant="observer")
    return [text_zip, observer_zip]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Fox River Valley release zip packages.")
    parser.add_argument("--variant", choices=["both", "text_only", "observer"], default="both")
    parser.add_argument("--output", default=None, help="Optional output path when building one variant.")
    args = parser.parse_args()

    if args.variant == "both":
        built_paths = build_default_release_zips(PROJECT_ROOT)
    else:
        default_output = TEXT_ONLY_OUTPUT if args.variant == "text_only" else OBSERVER_OUTPUT
        built_paths = [build_release_zip(PROJECT_ROOT, Path(args.output) if args.output else default_output, variant=args.variant)]
    for built in built_paths:
        print(built)
