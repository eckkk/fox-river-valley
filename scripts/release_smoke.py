from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run(args: list[str]) -> None:
    print("+ " + " ".join(args))
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def _parse_state(output: str) -> dict:
    state_lines = [line for line in output.splitlines() if line.startswith("STATE ")]
    if len(state_lines) != 1:
        raise AssertionError(output)
    return json.loads(state_lines[0][6:])


def _forbidden_release_markers() -> tuple[str, str, str]:
    return ("/mnt" + "/data", "D:" + "/SilasCheng", "D:" + "\\" + "SilasCheng")


def _with_runtime_home(path: Path):
    class RuntimeHome:
        def __enter__(self):
            self.old_home = os.environ.get("FRV_HOME")
            os.environ["FRV_HOME"] = str(path)
            from fox_river_valley import engine

            engine._current_state = None
            return self

        def __exit__(self, exc_type, exc, tb):
            from fox_river_valley import engine

            engine._current_state = None
            if self.old_home is None:
                os.environ.pop("FRV_HOME", None)
            else:
                os.environ["FRV_HOME"] = self.old_home

    return RuntimeHome()


def _prepare_sleep_state(death_mode: str) -> dict:
    from fox_river_valley.state import create_state
    from fox_river_valley.world import tile_key

    state = create_state("12071008", death_mode=death_mode)
    state["base_pos"] = list(state["pos"])
    state["shelter_pos"] = list(state["pos"])
    state["home_level"] = "shelter"
    state["builds"] = {tile_key(state["pos"]): ["simple_shelter"]}
    state["hp"] = 1
    state["hunger"] = 0
    return state


def _package_checks() -> None:
    from scripts.package_release import build_release_zip

    with tempfile.TemporaryDirectory() as tmp:
        observer_zip = build_release_zip(PROJECT_ROOT, Path(tmp) / "observer.zip", variant="observer")
        with zipfile.ZipFile(observer_zip) as archive:
            names = archive.namelist()
            html = archive.read("observer/observer.html").decode("utf-8")
            state_text = archive.read("observer/observer_state.json").decode("utf-8")
            observer_state = json.loads(state_text)
        if any(name.startswith("saves/") for name in names):
            raise AssertionError("observer release zip contains saves/")
        for forbidden in _forbidden_release_markers():
            if forbidden in html or forbidden in state_text:
                raise AssertionError(f"observer release zip contains forbidden trace: {forbidden}")
        if observer_state.get("screen") != "start_screen" or observer_state.get("has_save") is not False:
            raise AssertionError("observer_state.json is not clean start_screen")
        if '"screen":"start_screen"' not in html.replace(" ", ""):
            raise AssertionError("observer.html does not embed clean start_screen")

        text_zip = build_release_zip(PROJECT_ROOT, Path(tmp) / "text_only.zip", variant="text_only")
        with zipfile.ZipFile(text_zip) as archive:
            names = set(archive.namelist())
            text_blob = "\n".join(names)
        if any(name.startswith("observer/") for name in names):
            raise AssertionError("text-only release zip contains observer/")
        if "Start_Fox_River_Valley.bat" in names or "scripts/run_observer_server.py" in names:
            raise AssertionError("text-only release zip contains observer launcher/server")
        if "fox_river_valley_text.py" not in names or "TEXT_ONLY_PLAYER_GUIDE.md" not in names:
            raise AssertionError("text-only release zip is missing text-only entry or guide")
        if any(name.startswith("saves/") for name in names):
            raise AssertionError("text-only release zip contains saves/")
        for forbidden in _forbidden_release_markers():
            if forbidden in text_blob:
                raise AssertionError(f"text-only release zip contains forbidden trace: {forbidden}")
        print("Package clean state checks OK.")


def _fresh_start_check() -> None:
    from fox_river_valley.runtime import observer_paths, save_path
    from scripts.run_observer_server import initialize_observer_files

    with tempfile.TemporaryDirectory() as tmp, _with_runtime_home(Path(tmp)):
        initialize_observer_files()
        if save_path().exists():
            raise AssertionError("fresh observer start created a save")
        html = observer_paths()["html"].read_text(encoding="utf-8")
        if "start-mode-solo" not in html or '"screen":"start_screen"' not in html.replace(" ", ""):
            raise AssertionError("fresh observer start did not show start_screen")
        print("Fresh start_screen check OK.")


def _silas_yaya_follow_check() -> None:
    from fox_river_valley import cmd
    from scripts.run_observer_server import handle_new_game

    with tempfile.TemporaryDirectory() as tmp, _with_runtime_home(Path(tmp)):
        handle_new_game({"mode": "silas_yaya", "seed": "12071008", "death_mode": "cozy"})
        state = _parse_state(cmd("move north"))
        if state["companion"]["name"] != "Yaya":
            raise AssertionError("Silas-Yaya demo did not create Yaya companion")
        if state["companion"]["pos"] != state["pos"]:
            raise AssertionError("Yaya is not following player after move")
        print("Silas-Yaya demo follow check OK.")


def _death_mode_checks() -> None:
    from fox_river_valley import cmd
    from fox_river_valley.state import save_state

    with tempfile.TemporaryDirectory() as tmp, _with_runtime_home(Path(tmp)):
        save_state(_prepare_sleep_state("cozy"))
        cozy_output = cmd("sleep confirm")
        cozy_state = _parse_state(cozy_output)
        if "昏倒" not in cozy_output or cozy_state.get("game_over"):
            raise AssertionError("Cozy death mode did not faint/rescue")

    with tempfile.TemporaryDirectory() as tmp, _with_runtime_home(Path(tmp)):
        save_state(_prepare_sleep_state("survival"))
        survival_output = cmd("sleep confirm")
        survival_state = _parse_state(survival_output)
        if "Game Over" not in survival_output or not survival_state.get("game_over"):
            raise AssertionError("Survival death mode did not Game Over")
        print("Cozy and Survival death mode checks OK.")


def _ai_playtest_sleep_guard_check() -> None:
    from fox_river_valley import cmd
    from fox_river_valley.state import save_state
    from fox_river_valley.world import tile_key
    from fox_river_valley.state import create_state

    with tempfile.TemporaryDirectory() as tmp, _with_runtime_home(Path(tmp)):
        state = create_state("12071008", death_mode="ai_playtest")
        state["base_pos"] = list(state["pos"])
        state["shelter_pos"] = list(state["pos"])
        state["home_level"] = "shelter"
        state["builds"] = {tile_key(state["pos"]): ["simple_shelter"]}
        state["hunger"] = 10
        save_state(state)
        cmd("sleep")
        cmd("sleep")
        blocked = cmd("sleep")
        if "AI Playtest 禁止跳天等待天气" not in blocked:
            raise AssertionError("AI Playtest consecutive sleep guard did not block")
        print("AI Playtest sleep guard check OK.")


def main() -> int:
    # Required release checks:
    # python -m pytest -q
    # python scripts/long_arc_smoke.py
    # forbidden path scan
    # clean package start_screen
    # Silas-Yaya demo follows player
    # Cozy faint, Survival Game Over, AI Playtest anti-skip
    _run([sys.executable, "-m", "pytest", "-q"])
    _run([sys.executable, "scripts/long_arc_smoke.py"])
    _package_checks()
    _fresh_start_check()
    _silas_yaya_follow_check()
    _death_mode_checks()
    _ai_playtest_sleep_guard_check()
    print("Release smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
