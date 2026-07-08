from __future__ import annotations

import html
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from . import actions
from . import calendar as calendar_rules
from .family import compact_family, ensure_family_state, kit_mischief_line, kit_risk_summary
from .farming import garden_plot_count, ready_crop_count
from .relationship import compact_relationship, ensure_home_fields
from .render import compact_companion, state_summary
from .runtime import DEFAULT_SERVER_URL, observer_dir, observer_paths as runtime_observer_paths, runtime_root, save_path
from .world import in_bounds, nearby_terrains, terrain_at, tile_key

OBSERVER_DIR = observer_dir()
OBSERVER_STATE_PATH = OBSERVER_DIR / "observer_state.json"
OBSERVER_HTML_PATH = OBSERVER_DIR / "observer.html"
OBSERVER_SERVER_URL = DEFAULT_SERVER_URL
_TURN_ID = 0

TERRAIN_SYMBOLS = {
    "grass": ".",
    "forest": "♣",
    "water": "~",
    "hill": "△",
    "stone": "◼",
    "cave": "◼",
    "ruins": "⌂",
}


def observer_paths() -> dict[str, Path]:
    return runtime_observer_paths()


def write_observer_files(
    state: dict[str, Any],
    *,
    last_command: str,
    output: str,
    reset_turn: bool = False,
) -> dict[str, Path]:
    global _TURN_ID
    if reset_turn:
        _TURN_ID = 0
    _TURN_ID += 1
    paths = observer_paths()
    paths["dir"].mkdir(parents=True, exist_ok=True)
    observer_state = build_observer_state(state, last_command=last_command, output=output, turn_id=_TURN_ID)
    write_json_atomic(paths["state"], observer_state)
    paths["html"].write_text(render_observer_html(observer_state), encoding="utf-8")
    return paths


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    tmp_path = path.with_name("observer_state.tmp.json")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    last_error: PermissionError | None = None
    for _ in range(8):
        try:
            tmp_path.replace(path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.05)
    if tmp_path.exists():
        tmp_path.unlink(missing_ok=True)
    if last_error:
        raise last_error


def build_start_screen_state() -> dict[str, Any]:
    return {
        "screen": "start_screen",
        "has_save": False,
        "last_command": None,
        "last_output_summary": ["等待开局。"],
    }


def build_observer_state(state: dict[str, Any], *, last_command: str, output: str, turn_id: int) -> dict[str, Any]:
    summary = state_summary(state)
    ensure_home_fields(state)
    calendar = calendar_rules.ensure_calendar(state)
    family = compact_family(state)
    data: dict[str, Any] = {
        "turn_id": turn_id,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "runtime_root": str(runtime_root()),
        "save_path": str(save_path()),
        "day": summary["day"],
        "year": calendar["year"],
        "season": calendar["season"],
        "day_of_season": calendar["day_of_season"],
        "time": summary["time"],
        "weather": summary["weather"],
        "pos": summary["pos"],
        "terrain": summary["terrain"],
        "hp": summary["hp"],
        "hunger": summary["hunger"],
        "energy": summary["energy"],
        "nearby": summary["nearby"],
        "home_name": summary.get("home_name"),
        "home_level": summary.get("home_level"),
        "base_pos": summary.get("base_pos"),
        "home_status": _home_status_summary(state, summary),
        "builds_here": summary.get("builds_here", []),
        "companion": summary.get("companion"),
        "family": family,
        "kits": _kit_summary(state),
        "relationship": compact_relationship(state),
        "inventory_summary": _count_summary(state.get("inventory", {})),
        "storage_summary": _count_summary(state.get("storage", {})),
        "garden_summary": _garden_summary(state),
        "status_warnings": _status_warnings(state),
        "recent_journal": _recent_journal(state),
        "last_command": last_command,
        "last_output_summary": _output_summary(output),
        "options": actions.co_play_options(state),
        "local_map": _local_map(state),
    }
    return data


def _home_status_summary(state: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    base_pos = summary.get("base_pos")
    builds = []
    if base_pos:
        builds = state.get("builds", {}).get(tile_key(list(base_pos)), [])
    return {
        "home_name": summary.get("home_name"),
        "home_level": summary.get("home_level"),
        "base_pos": base_pos,
        "builds": builds,
        "safe_sleep": bool(base_pos and list(state.get("pos", [])) == list(base_pos)),
        "comfort": summary.get("home_comfort", 0),
        "security": summary.get("home_security", 0),
    }


def _count_summary(items: dict[str, Any], limit: int = 12) -> dict[str, int]:
    clean = {
        str(item): int(count)
        for item, count in items.items()
        if isinstance(count, int) and count > 0
    }
    return dict(sorted(clean.items())[:limit])


def _garden_summary(state: dict[str, Any]) -> dict[str, Any]:
    plots = []
    for plot in state.get("garden", {}).get("plots", [])[:6]:
        plots.append(
            {
                "id": plot.get("id"),
                "pos": plot.get("pos"),
                "crop": plot.get("crop"),
                "seed": plot.get("seed"),
                "variety": plot.get("variety"),
                "growth": plot.get("growth", 0),
                "ready": bool(plot.get("ready")),
            }
        )
    return {
        "plot_count": garden_plot_count(state),
        "ready_crops": ready_crop_count(state),
        "plots": plots,
    }


def _kit_summary(state: dict[str, Any]) -> list[dict[str, Any]]:
    family = ensure_family_state(state)
    kits = []
    for kit in family.get("kits", []):
        kits.append(
            {
                "name": kit.get("name"),
                "display_name": kit.get("display_name"),
                "species": kit.get("species"),
                "hunger": kit.get("hunger"),
                "warmth": kit.get("warmth"),
                "sleep": kit.get("sleep"),
                "security": kit.get("security"),
                "mischief": kit.get("mischief"),
                "status": kit_mischief_line(kit),
            }
        )
    return kits


def _status_warnings(state: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    expiring = actions.expiring_food_counts(state, minimum_count=1)
    if expiring:
        warnings.append("即将变质：" + " / ".join(f"{item} x{count}" for item, count in expiring.items()))
    kit_risk = kit_risk_summary(state)
    if kit_risk:
        warnings.append(f"kit risk: {kit_risk}")
    return warnings


def _recent_journal(state: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    entries = []
    for entry in state.get("journal", [])[-limit:]:
        entries.append(
            {
                "day": entry.get("day"),
                "time": entry.get("time"),
                "text": entry.get("text"),
            }
        )
    return entries


def _output_summary(output: str, limit: int = 6) -> list[str]:
    lines = []
    for line in output.splitlines():
        if line.startswith("STATE "):
            continue
        if line.strip():
            lines.append(line.strip())
        if len(lines) >= limit:
            break
    return lines


def _local_map(state: dict[str, Any], radius: int = 3) -> list[list[dict[str, Any]]]:
    current = list(state.get("pos", [0, 0]))
    base = state.get("base_pos")
    discovered = set(state.get("discovered", []))
    nearby_keys = {tile_key(pos) for pos in _nearby_positions(current)}
    garden_positions = {
        tile_key(plot.get("pos"))
        for plot in state.get("garden", {}).get("plots", [])
        if isinstance(plot.get("pos"), list) and len(plot.get("pos")) == 2
    }
    rows = []
    for y in range(current[1] - radius, current[1] + radius + 1):
        row = []
        for x in range(current[0] - radius, current[0] + radius + 1):
            pos = [x, y]
            key = tile_key(pos)
            known = in_bounds(pos) and (key in discovered or key in nearby_keys or pos == current)
            terrain = terrain_at(str(state.get("seed", "default")), pos) if known else "unknown"
            symbol = " "
            if known:
                symbol = TERRAIN_SYMBOLS.get(terrain, "?")
            if key in garden_positions:
                symbol = "✿"
            if base and pos == list(base):
                symbol = "🏠"
            if pos == current:
                symbol = "@"
            row.append({"pos": pos, "terrain": terrain, "symbol": symbol, "known": known})
        rows.append(row)
    return rows


def _nearby_positions(pos: list[int]) -> list[list[int]]:
    x, y = pos
    return [[x, y - 1], [x + 1, y], [x, y + 1], [x - 1, y]]


def render_start_screen_html() -> str:
    start_state_json = json.dumps(build_start_screen_state(), ensure_ascii=False, separators=(",", ":"))
    start_state_json = start_state_json.replace("</", "<\\/")
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fox River Valley Observer</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f0e8;
      --panel: #fffaf0;
      --ink: #28231c;
      --muted: #6d6255;
      --line: #d6cabb;
      --accent: #2f6f68;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.45;
    }
    main {
      max-width: 860px;
      margin: 28px auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h1 { margin: 0 0 6px; font-size: 28px; letter-spacing: 0; }
    fieldset { border: 1px solid var(--line); border-radius: 8px; margin: 14px 0; padding: 12px; }
    legend { font-weight: 700; }
    label { display: block; margin: 8px 0; }
    input[type="text"] {
      width: 100%;
      max-width: 360px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      font: inherit;
    }
    button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 9px 13px;
      font: inherit;
      cursor: pointer;
    }
    pre { white-space: pre-wrap; background: #f8f4eb; padding: 12px; border-radius: 6px; min-height: 80px; }
    .muted { color: var(--muted); }
  </style>
</head>
<body>
  <main>
    <h1>Fox River Valley / 狐狸河谷</h1>
    <p class="muted">选择开局模式。这里会调用 new_game(...)，不是把第一条命令当成默认 solo。</p>

    <fieldset>
      <legend>开局模式</legend>
      <label><input id="start-mode-solo" type="radio" name="start_mode" value="solo" checked> solo</label>
      <label><input id="start-mode-custom-family" type="radio" name="start_mode" value="custom_family"> custom family</label>
      <label><input id="start-mode-silas-yaya" type="radio" name="start_mode" value="silas_yaya"> Silas/Yaya demo profile</label>
      <p class="muted">Yaya 是 Silas/Yaya demo，不是公开默认路线。</p>
    </fieldset>

    <fieldset>
      <legend>死亡模式</legend>
      <label><input id="death-mode-cozy" type="radio" name="death_mode" value="cozy" checked> cozy</label>
      <label><input id="death-mode-survival" type="radio" name="death_mode" value="survival"> survival</label>
      <label><input id="death-mode-ai-playtest" type="radio" name="death_mode" value="ai_playtest"> ai_playtest</label>
    </fieldset>

    <fieldset>
      <legend>自定义</legend>
      <label>seed <input id="seed-input" type="text" value="12071008"></label>
      <label>companion name <input id="companion-name-input" type="text" value="Alex"></label>
      <label>family species <input id="family-species-input" type="text" placeholder="optional"></label>
    </fieldset>

    <button id="start-game" type="button">开始游戏</button>
    <pre id="output">等待开局。</pre>
  </main>
  <script type="application/json" id="observer-state">__START_SCREEN_STATE__</script>
  <script>
    function selected(name) {
      const found = document.querySelector(`input[name="${name}"]:checked`);
      return found ? found.value : "";
    }
    async function startGame() {
      const mode = selected("start_mode");
      const payload = {
        mode,
        seed: document.getElementById("seed-input").value || "12071008",
        death_mode: selected("death_mode") || "cozy",
        companion_name: document.getElementById("companion-name-input").value || "Alex",
        companion_profile: "default",
        family_species: document.getElementById("family-species-input").value || null
      };
      const output = document.getElementById("output");
      output.textContent = "开局中...";
      try {
        const response = await fetch("./new_game", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        output.textContent = data.output || "已开始。";
        setTimeout(() => location.reload(), 400);
      } catch (error) {
        output.textContent = "Observer is not connected. Please run Start_Fox_River_Valley.bat or python scripts/run_observer_server.py.";
      }
    }
    document.getElementById("start-game").addEventListener("click", startGame);
  </script>
</body>
</html>
""".replace("__START_SCREEN_STATE__", start_state_json)


def render_observer_html(observer_state: dict[str, Any]) -> str:
    state_json = json.dumps(observer_state, ensure_ascii=False)
    safe_state_json = state_json.replace("</", "<\\/")
    rows = "\n".join(_map_row(row) for row in observer_state["local_map"])
    recent_action = _list_items(observer_state["last_output_summary"])
    journal = _journal_items(observer_state["recent_journal"])
    options = _list_items(observer_state["options"])
    inventory = _counts_text(observer_state["inventory_summary"])
    storage = _counts_text(observer_state["storage_summary"])
    companion = observer_state.get("companion") or {}
    relationship = observer_state.get("relationship") or {}
    family = observer_state.get("family") or {}
    kits = observer_state.get("kits") or []
    garden = observer_state.get("garden_summary") or {}
    status_warnings = observer_state.get("status_warnings") or []
    title = "Fox River Valley Observer"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f0e8;
      --panel: #fffaf0;
      --ink: #28231c;
      --muted: #6d6255;
      --line: #d6cabb;
      --accent: #2f6f68;
      --warm: #a85d32;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.45;
    }}
    header {{
      padding: 18px 22px 12px;
      border-bottom: 1px solid var(--line);
      background: #f8f4eb;
    }}
    h1 {{ margin: 0; font-size: 26px; font-weight: 700; letter-spacing: 0; }}
    .subtitle {{ color: var(--muted); margin-top: 4px; }}
    main {{
      display: grid;
      grid-template-columns: minmax(250px, 0.9fr) minmax(320px, 1.3fr) minmax(270px, 0.9fr);
      gap: 14px;
      padding: 14px;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }}
    h2 {{ margin: 0 0 10px; font-size: 17px; letter-spacing: 0; }}
    .map {{
      display: grid;
      grid-template-columns: repeat(7, 32px);
      grid-auto-rows: 32px;
      gap: 4px;
      align-items: center;
    }}
    .tile {{
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #eee7d9;
      font-size: 18px;
      font-family: "Segoe UI Symbol", "Microsoft YaHei", sans-serif;
    }}
    .tile.unknown {{ opacity: 0.42; }}
    .tile.player {{ outline: 2px solid var(--accent); font-weight: 700; }}
    .legend {{ margin-top: 12px; color: var(--muted); font-size: 13px; }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 5px 0; }}
    .stat-grid {{ display: grid; gap: 8px; }}
    .stat {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid #eadfce;
      padding-bottom: 5px;
    }}
    .label {{ color: var(--muted); }}
    .value {{ text-align: right; font-weight: 600; overflow-wrap: anywhere; }}
    footer {{
      padding: 0 14px 14px;
    }}
    .command-panel {{
      margin: 10px 14px 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }}
    .command-row {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }}
    #command-input {{
      flex: 1 1 260px;
      min-width: 180px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      font: inherit;
      background: #fffdf7;
    }}
    button {{
      border: 1px solid #b9aa99;
      background: #f5eadc;
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
      cursor: pointer;
    }}
    button.primary {{
      background: var(--accent);
      border-color: var(--accent);
      color: white;
      font-weight: 700;
    }}
    .quick-buttons {{
      margin-top: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .options {{
      background: #eef6f1;
      border-color: #bed5c9;
    }}
    .notice {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .warning {{
      margin: 10px 14px 0;
      padding: 10px 12px;
      border: 1px solid #e1c597;
      background: #fff4d6;
      border-radius: 8px;
      color: #5e4320;
    }}
    @media (max-width: 920px) {{
      main {{ grid-template-columns: 1fr; }}
      .map {{ grid-template-columns: repeat(7, minmax(28px, 1fr)); }}
      .tile {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="subtitle" id="observer-subtitle">Year {observer_state["year"]} {html.escape(str(observer_state["season"]))} Day {observer_state["day_of_season"]} · Day {observer_state["day"]} · {html.escape(str(observer_state["time"]))} · {html.escape(str(observer_state["weather"]))}</div>
    <div class="notice" id="connection-status">Live observer ready. If this file is opened with file://, some browsers may block observer_state.json polling. Run python scripts/run_observer_server.py and open {OBSERVER_SERVER_URL}.</div>
  </header>
  <div class="warning" id="file-warning">file:// compatibility note: if live updates do not appear, run python scripts/run_observer_server.py, then open {OBSERVER_SERVER_URL}.</div>
  <section class="command-panel" aria-label="command runner">
    <h2>命令</h2>
    <div class="command-row">
      <input id="command-input" type="text" placeholder="输入命令，例如 gather" autocomplete="off">
      <button id="run-command" class="primary" type="button">执行</button>
    </div>
    <div class="quick-buttons" id="quick-buttons">
      <button type="button" data-command="look">look</button>
      <button type="button" data-command="status">status</button>
      <button type="button" data-command="inventory">inventory</button>
      <button type="button" data-command="map">map</button>
      <button type="button" data-command="check companion">check companion</button>
      <button type="button" data-command="gather">gather</button>
      <button type="button" data-command="fish">fish</button>
      <button type="button" data-command="return home">return home</button>
      <button type="button" data-command="sleep">sleep</button>
    </div>
    <div class="notice" id="command-result">网页会调用同一个 cmd()，并写入统一存档。</div>
  </section>
  <main>
    <section>
      <h2>小地图</h2>
      <div class="map" aria-label="local map" id="local-map">{rows}</div>
      <div class="legend">@ player · 🏠 base · ♣ forest · ~ water · △ hill · ◼ stone/cave · ⌂ ruins · ✿ garden · . grass</div>
    </section>
    <section>
      <h2>最近行动</h2>
      <p><strong>last_command:</strong> <span id="last-command">{html.escape(str(observer_state["last_command"]))}</span></p>
      <ul id="recent-action">{recent_action}</ul>
      <h2>Journal</h2>
      <ul id="journal-list">{journal}</ul>
    </section>
    <section>
      <h2>状态</h2>
      <div class="stat-grid" id="status-panel">
        {_stat("HP", observer_state.get("hp"))}
        {_stat("hunger", observer_state.get("hunger"))}
        {_stat("energy", observer_state.get("energy"))}
        {_stat("位置", f'{observer_state["terrain"]} {observer_state["pos"]}')}
        {_stat("runtime root", observer_state.get("runtime_root"))}
        {_stat("save path", observer_state.get("save_path"))}
        {_stat("附近", ", ".join(observer_state["nearby"]))}
        {_stat("家", f'{observer_state.get("home_name") or "未命名"} / {observer_state.get("home_level") or "none"}')}
        {_stat("base_pos", observer_state.get("base_pos"))}
        {_stat("builds_here", ", ".join(observer_state.get("builds_here") or []) or "none")}
        {_stat("companion", _companion_status_text(companion))}
        {_stat("companion hunger", companion.get("hunger", "none"))}
        {_stat("companion warmth", companion.get("warmth", "none"))}
        {_stat("companion mood", companion.get("mood", "none"))}
        {_stat("companion trust", companion.get("trust", "none"))}
        {_stat("companion security", companion.get("security", "none"))}
        {_stat("companion comfort", companion.get("comfort", "none"))}
        {_stat("wish", companion.get("wish", "none"))}
        {_stat("thought", companion.get("thought", "none"))}
        {_stat("home status", _home_status_text(observer_state.get("home_status") or {}))}
        {_stat("family", f'{family.get("kit_status", "none")} / kits {family.get("kit_count", 0)}')}
        {_stat("kits status", _kits_status_text(kits))}
        {_stat("status warning", "; ".join(status_warnings) or "none")}
        {_stat("relationship", f'{relationship.get("stage", "none")} / bond {relationship.get("bond", 0)}')}
        {_stat("inventory", inventory)}
        {_stat("storage", storage)}
        {_stat("garden", f'plots {garden.get("plot_count", 0)} / ready {garden.get("ready_crops", 0)}')}
      </div>
    </section>
  </main>
  <footer>
    <section class="options">
      <h2>下一步建议</h2>
      <ul id="options-list">{options}</ul>
    </section>
  </footer>
  <script type="application/json" id="observer-state">{safe_state_json}</script>
  <script>
    let currentTurnId = null;

    function escapeHtml(value) {{
      return String(value ?? "").replace(/[&<>"']/g, (ch) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[ch]));
    }}

    function listHtml(items, emptyText = "none") {{
      if (!items || !items.length) return "<li>" + escapeHtml(emptyText) + "</li>";
      return items.map((item) => "<li>" + escapeHtml(item) + "</li>").join("");
    }}

    function journalHtml(entries) {{
      if (!entries || !entries.length) return "<li>暂无。</li>";
      return entries.map((entry) => {{
        const text = `Day ${{entry.day}} ${{entry.time}}: ${{entry.text}}`;
        return "<li>" + escapeHtml(text) + "</li>";
      }}).join("");
    }}

    function countsText(items) {{
      if (!items || !Object.keys(items).length) return "empty";
      return Object.entries(items).map(([item, count]) => `${{item}} x${{count}}`).join(", ");
    }}

    function stat(label, value) {{
      return `<div class="stat"><span class="label">${{escapeHtml(label)}}</span><span class="value">${{escapeHtml(value)}}</span></div>`;
    }}

    function mapHtml(rows) {{
      return (rows || []).map((row) => row.map((cell) => {{
        const classes = ["tile"];
        if (!cell.known) classes.push("unknown");
        if (cell.symbol === "@") classes.push("player");
        const title = `${{cell.terrain}} ${{JSON.stringify(cell.pos)}}`;
        return `<div class="${{classes.join(" ")}}" title="${{escapeHtml(title)}}">${{escapeHtml(cell.symbol || " ")}}</div>`;
      }}).join("")).join("\\n");
    }}

    function renderObserver(data) {{
      currentTurnId = data.turn_id;
      document.getElementById("observer-subtitle").textContent =
        `Year ${{data.year}} ${{data.season}} Day ${{data.day_of_season}} · Day ${{data.day}} · ${{data.time}} · ${{data.weather}} · turn ${{data.turn_id}} · ${{data.last_updated}}`;
      document.getElementById("local-map").innerHTML = mapHtml(data.local_map);
      document.getElementById("last-command").textContent = data.last_command;
      document.getElementById("recent-action").innerHTML = listHtml(data.last_output_summary);
      document.getElementById("journal-list").innerHTML = journalHtml(data.recent_journal);
      document.getElementById("options-list").innerHTML = listHtml(data.options);
      const companion = data.companion || {{}};
      const homeStatus = data.home_status || {{}};
      const family = data.family || {{}};
      const kits = data.kits || [];
      const relationship = data.relationship || {{}};
      const garden = data.garden_summary || {{}};
      const statusWarnings = data.status_warnings || [];
      document.getElementById("status-panel").innerHTML = [
        stat("HP", data.hp ?? "unknown"),
        stat("hunger", data.hunger ?? "unknown"),
        stat("energy", data.energy ?? "unknown"),
        stat("位置", `${{data.terrain}} ${{JSON.stringify(data.pos)}}`),
        stat("runtime root", data.runtime_root || "unknown"),
        stat("save path", data.save_path || "unknown"),
        stat("附近", (data.nearby || []).join(", ")),
        stat("家", `${{data.home_name || "未命名"}} / ${{data.home_level || "none"}}`),
        stat("base_pos", JSON.stringify(data.base_pos)),
        stat("builds_here", (data.builds_here || []).join(", ") || "none"),
        stat("companion", companionStatusText(companion)),
        stat("companion hunger", companion.hunger ?? "none"),
        stat("companion warmth", companion.warmth ?? "none"),
        stat("companion mood", companion.mood ?? "none"),
        stat("companion trust", companion.trust ?? "none"),
        stat("companion security", companion.security ?? "none"),
        stat("companion comfort", companion.comfort ?? "none"),
        stat("wish", companion.wish || "none"),
        stat("thought", companion.thought || "none"),
        stat("home status", homeStatusText(homeStatus)),
        stat("family", `${{family.kit_status || "none"}} / kits ${{family.kit_count || 0}}`),
        stat("kits status", kitsStatusText(kits)),
        stat("status warning", statusWarnings.join("; ") || "none"),
        stat("relationship", `${{relationship.stage || "none"}} / bond ${{relationship.bond || 0}}`),
        stat("inventory", countsText(data.inventory_summary)),
        stat("storage", countsText(data.storage_summary)),
        stat("garden", `plots ${{garden.plot_count || 0}} / ready ${{garden.ready_crops || 0}}`)
      ].join("");
      document.getElementById("connection-status").textContent =
        `Connected. Last update: turn ${{data.turn_id}} at ${{data.last_updated}}.`;
    }}

    async function pollObserverState() {{
      try {{
        const response = await fetch("./observer_state.json?ts=" + Date.now());
        if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
        const data = await response.json();
        if (data.turn_id !== currentTurnId) renderObserver(data);
      }} catch (error) {{
        document.getElementById("connection-status").textContent =
          "Observer is not connected. Please run scripts/run_observer_server.py or refresh manually.";
      }}
    }}

    function companionStatusText(companion) {{
      if (!companion || !companion.name) return "none";
      const mode = companion.location_mode || companion.location || "with_player";
      const label = mode === "with_player" ? "跟随中" : (mode === "at_home" ? "在家" : mode);
      return `${{companion.name}}：${{label}} ${{JSON.stringify(companion.pos || [])}}`;
    }}

    function homeStatusText(homeStatus) {{
      if (!homeStatus || !homeStatus.base_pos) return "none";
      const builds = (homeStatus.builds || []).join(", ") || "none";
      return `${{homeStatus.home_name || "未命名"}} / ${{homeStatus.home_level || "none"}} / safe_sleep ${{homeStatus.safe_sleep ? "yes" : "no"}} / builds ${{builds}}`;
    }}

    function kitsStatusText(kits) {{
      if (!kits || !kits.length) return "none";
      return kits.map((kit) => `${{kit.name || kit.display_name || "第一只小崽"}} hunger ${{kit.hunger}} / warmth ${{kit.warmth}} / mischief ${{kit.mischief}} / ${{kit.status || ""}}`).join("; ");
    }}

    async function runGameCommand(command) {{
      const trimmed = String(command || "").trim();
      if (!trimmed) return;
      document.getElementById("command-result").textContent = "执行中：" + trimmed;
      try {{
        const response = await fetch("./cmd", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{command: trimmed}})
        }});
        if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
        const data = await response.json();
        document.getElementById("command-result").textContent = data.output || "已执行。";
        await pollObserverState();
      }} catch (error) {{
        document.getElementById("command-result").textContent =
          "网页命令未连接。请确认 Start_Fox_River_Valley.bat 或 observer server 正在运行。";
      }}
    }}

    const initialState = JSON.parse(document.getElementById("observer-state").textContent);
    renderObserver(initialState);
    document.getElementById("run-command").addEventListener("click", () => {{
      const input = document.getElementById("command-input");
      runGameCommand(input.value);
    }});
    document.getElementById("command-input").addEventListener("keydown", (event) => {{
      if (event.key === "Enter") runGameCommand(event.target.value);
    }});
    document.querySelectorAll("#quick-buttons [data-command]").forEach((button) => {{
      button.addEventListener("click", () => {{
        const command = button.getAttribute("data-command");
        document.getElementById("command-input").value = command;
        runGameCommand(command);
      }});
    }});
    setInterval(pollObserverState, 1000);
  </script>
</body>
</html>
"""


def _map_row(row: list[dict[str, Any]]) -> str:
    return "".join(_map_cell(cell) for cell in row)


def _map_cell(cell: dict[str, Any]) -> str:
    classes = ["tile"]
    if not cell.get("known"):
        classes.append("unknown")
    if cell.get("symbol") == "@":
        classes.append("player")
    title = f"{cell.get('terrain')} {cell.get('pos')}"
    return f'<div class="{" ".join(classes)}" title="{html.escape(title)}">{html.escape(str(cell.get("symbol", " ")))}</div>'


def _list_items(lines: list[str]) -> str:
    if not lines:
        return "<li>none</li>"
    return "".join(f"<li>{html.escape(str(line))}</li>" for line in lines)


def _journal_items(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "<li>暂无。</li>"
    items = []
    for entry in entries:
        text = f"Day {entry.get('day')} {entry.get('time')}: {entry.get('text')}"
        items.append(f"<li>{html.escape(text)}</li>")
    return "".join(items)


def _counts_text(items: dict[str, int]) -> str:
    if not items:
        return "empty"
    return ", ".join(f"{item} x{count}" for item, count in items.items())


def _stat(label: str, value: Any) -> str:
    return f'<div class="stat"><span class="label">{html.escape(label)}</span><span class="value">{html.escape(str(value))}</span></div>'


def _companion_status_text(companion: dict[str, Any]) -> str:
    if not companion or not companion.get("name"):
        return "none"
    mode = companion.get("location_mode") or companion.get("location") or "with_player"
    label = "跟随中" if mode == "with_player" else ("在家" if mode == "at_home" else str(mode))
    return f"{companion.get('name')}：{label} {companion.get('pos', [])}"


def _home_status_text(home_status: dict[str, Any]) -> str:
    if not home_status or not home_status.get("base_pos"):
        return "none"
    builds = ", ".join(home_status.get("builds") or []) or "none"
    safe_sleep = "yes" if home_status.get("safe_sleep") else "no"
    return (
        f"{home_status.get('home_name') or '未命名'} / {home_status.get('home_level') or 'none'} "
        f"/ safe_sleep {safe_sleep} / builds {builds}"
    )


def _kits_status_text(kits: list[dict[str, Any]]) -> str:
    if not kits:
        return "none"
    parts = []
    for kit in kits:
        label = kit.get("name") or kit.get("display_name") or "第一只小崽"
        details = [
            f"hunger {kit.get('hunger')}",
            f"warmth {kit.get('warmth')}",
            f"mischief {kit.get('mischief')}",
        ]
        status = kit.get("status")
        if status:
            details.append(str(status))
        parts.append(f"{label}: " + " / ".join(details))
    return "; ".join(parts)
