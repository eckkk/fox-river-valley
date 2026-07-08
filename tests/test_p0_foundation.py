import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fox_river_valley import engine
from fox_river_valley import cmd, new_game
from fox_river_valley.state import create_state, load_state, save_state
from tests.test_commands import parse_state


class TempRuntimeMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("FRV_HOME")
        os.environ["FRV_HOME"] = self.tmp.name
        engine._current_state = None

    def tearDown(self):
        engine._current_state = None
        if self.old_home is None:
            os.environ.pop("FRV_HOME", None)
        else:
            os.environ["FRV_HOME"] = self.old_home
        self.tmp.cleanup()


class P0FoundationTests(TempRuntimeMixin, unittest.TestCase):
    def save_path(self) -> Path:
        from fox_river_valley.runtime import save_path

        return save_path()

    def observer_state_path(self) -> Path:
        from fox_river_valley.runtime import observer_paths

        return observer_paths()["state"]

    def mutate_save(self, updates: dict) -> dict:
        state = load_state()
        state.update(updates)
        save_state(state)
        return state

    def test_cmd_loads_existing_save_and_autosaves_between_process_style_calls(self):
        new_game("12071008")
        first = parse_state(cmd("gather"))
        engine._current_state = None

        inventory_output = cmd("inventory")
        second = parse_state(inventory_output)

        self.assertTrue(first["inventory"])
        self.assertEqual(second["inventory"], first["inventory"])
        saved = json.loads(self.save_path().read_text(encoding="utf-8"))
        self.assertEqual(saved["inventory"], first["inventory"])

    def test_observer_html_has_command_ui_and_runtime_debug_paths(self):
        new_game("12071008", companion_name="Yaya")
        html = Path(os.environ["FRV_HOME"]) / "observer" / "observer.html"
        text = html.read_text(encoding="utf-8")
        observer_state = json.loads(self.observer_state_path().read_text(encoding="utf-8"))

        self.assertIn('id="command-input"', text)
        self.assertIn('id="run-command"', text)
        for command in ("look", "status", "inventory", "map", "gather", "fish", "return home", "sleep"):
            self.assertIn(command, text)
        self.assertIn("runtime_root", observer_state)
        self.assertIn("save_path", observer_state)

    def test_observer_server_cmd_api_executes_command_and_updates_save(self):
        from scripts.run_observer_server import handle_command

        new_game("12071008")
        result = handle_command("gather")
        state = json.loads(self.save_path().read_text(encoding="utf-8"))

        self.assertIn("STATE ", result["output"])
        self.assertEqual(result["last_command"], "gather")
        self.assertTrue(state["inventory"])

    def test_companion_defaults_to_following_and_moves_with_player(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))

        after = parse_state(cmd("move north"))

        self.assertEqual(before["companion"]["location_mode"], "with_player")
        self.assertEqual(after["companion"]["pos"], after["pos"])

    def test_cozy_mode_hunger_collapse_rescues_home_without_game_over(self):
        state = create_state("12071008", companion_name="Yaya", death_mode="cozy")
        state.update(
            {
                "hp": 1,
                "hunger": 0,
                "zero_hunger_days": 2,
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
                "pos": [12, 12],
                "inventory": {"fish": 3, "wood": 5},
            }
        )
        save_state(state)

        output = cmd("sleep confirm")
        after = parse_state(output)

        self.assertIn("昏倒", output)
        self.assertFalse(after.get("game_over", False))
        self.assertEqual(after["hp"], 3)
        self.assertEqual(after["hunger"], 2)
        self.assertEqual(after["pos"], [12, 12])

    def test_survival_mode_hunger_collapse_game_over_blocks_play(self):
        state = create_state("12071008", death_mode="survival")
        state.update(
            {
                "hp": 1,
                "hunger": 0,
                "zero_hunger_days": 2,
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
                "pos": [12, 12],
            }
        )
        save_state(state)

        output = cmd("sleep confirm")
        blocked = cmd("gather")

        self.assertIn("Game Over", output)
        self.assertIn("只能 restart / load", blocked)

    def test_rain_sleep_auto_waters_crops(self):
        state = create_state("12071008")
        state.update(
            {
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
                "weather": "rain",
                "garden": {
                    "plots": [
                        {
                            "id": 1,
                            "pos": [12, 12],
                            "crop": "herb",
                            "seed": "herb_seed",
                            "variety": None,
                            "color": None,
                            "growth": 0,
                            "watered_today": False,
                            "watered_days": 0,
                            "growth_days": 0,
                            "planted_day": 1,
                            "ready": False,
                        }
                    ],
                    "next_id": 2,
                },
            }
        )
        save_state(state)

        after = parse_state(cmd("sleep"))

        self.assertEqual(after["garden_plots"], 1)
        saved = load_state()
        self.assertGreaterEqual(saved["garden"]["plots"][0]["growth"], 1)

    def test_cold_wind_without_fire_costs_hp_or_warmth(self):
        state = create_state("12071008", companion_name="Yaya")
        state.update(
            {
                "hp": 6,
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
                "weather": "cold_wind",
            }
        )
        save_state(state)

        before = load_state()
        cmd("sleep")
        after = load_state()

        self.assertLess(after["hp"], before["hp"])
        self.assertLess(after["companion"]["warmth"], before["companion"]["warmth"])

    def test_fog_forest_explore_can_find_moss_thread_without_waiting_many_days(self):
        state = create_state("12071008")
        state.update({"weather": "fog", "pos": [12, 11], "discovered": ["12,12", "12,11"]})
        save_state(state)

        output = cmd("explore")
        after = parse_state(output)

        self.assertIn("moss_thread", output)
        self.assertGreaterEqual(after["inventory"].get("moss_thread", 0), 1)

    def test_sleep_warns_before_low_hunger_or_spoilage_and_requires_confirm(self):
        state = create_state("12071008", companion_name="Yaya")
        state.update(
            {
                "hunger": 1,
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
                "inventory": {"fish": 3},
                "food_age": {"fish": 1},
            }
        )
        save_state(state)

        warning = cmd("sleep")
        after_warning = parse_state(warning)
        confirmed = cmd("sleep confirm")
        after_confirmed = parse_state(confirmed)

        self.assertIn("sleep confirm", warning)
        self.assertEqual(after_warning["day"], 1)
        self.assertEqual(after_confirmed["day"], 2)

    def test_sleep_warns_at_zero_hunger_with_urgent_language(self):
        state = create_state("12071008", companion_name="Yaya")
        state.update(
            {
                "hunger": 0,
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
            }
        )
        state["companion"]["hunger"] = 0
        save_state(state)

        warning = cmd("sleep")
        after = parse_state(warning)

        self.assertIn("最高级警告", warning)
        self.assertIn("hunger 0", warning)
        self.assertIn("sleep confirm", warning)
        self.assertEqual(after["day"], 1)

    def test_ai_playtest_blocks_third_consecutive_sleep_without_action(self):
        state = create_state("12071008", death_mode="ai_playtest")
        state.update(
            {
                "hunger": 10,
                "base_pos": [12, 12],
                "shelter_pos": [12, 12],
                "builds": {"12,12": ["simple_shelter"]},
            }
        )
        save_state(state)

        first = parse_state(cmd("sleep"))
        second = parse_state(cmd("sleep"))
        blocked = cmd("sleep")
        after_block = parse_state(blocked)

        self.assertEqual(first["day"], 2)
        self.assertEqual(second["day"], 3)
        self.assertIn("AI Playtest 禁止跳天等待天气", blocked)
        self.assertEqual(after_block["day"], 3)

    def test_observer_start_screen_has_new_game_mode_controls(self):
        from scripts import run_observer_server
        from fox_river_valley.runtime import observer_paths

        run_observer_server.initialize_observer_files()

        html = observer_paths()["html"].read_text(encoding="utf-8")
        self.assertIn("start-mode-solo", html)
        self.assertIn("start-mode-custom-family", html)
        self.assertIn("start-mode-silas-yaya", html)
        self.assertIn("death-mode-cozy", html)
        self.assertIn("death-mode-survival", html)
        self.assertIn("death-mode-ai-playtest", html)
        self.assertIn("./new_game", html)
        self.assertNotIn("D:" + "/SilasCheng", html)
        self.assertNotIn("/mnt" + "/data", html)

    def test_observer_new_game_endpoint_creates_selected_family_mode(self):
        from scripts import run_observer_server

        result = run_observer_server.handle_new_game(
            {
                "mode": "custom_family",
                "seed": "custom-seed",
                "companion_name": "Alex",
                "companion_profile": "default",
                "death_mode": "survival",
            }
        )

        state = parse_state(result["output"])
        self.assertEqual(result["last_command"], "new_game")
        self.assertEqual(state["mode"], "family")
        self.assertEqual(state["death_mode"], "survival")
        self.assertEqual(state["companion"]["name"], "Alex")

    def test_observer_server_start_loads_save_or_writes_start_screen(self):
        from scripts import run_observer_server
        from fox_river_valley.runtime import observer_paths

        run_observer_server.initialize_observer_files()
        html_without_save = observer_paths()["html"].read_text(encoding="utf-8")
        self.assertIn("选择开局模式", html_without_save)
        self.assertFalse(observer_paths()["state"].exists())

        state = create_state("12071008", companion_name="Alex")
        save_state(state)
        run_observer_server.initialize_observer_files()
        observer_state = json.loads(observer_paths()["state"].read_text(encoding="utf-8"))

        self.assertEqual(observer_state["last_command"], "load")
        self.assertEqual(observer_state["companion"]["name"], "Alex")

    def test_packaged_observer_html_has_no_runtime_or_dev_paths(self):
        import importlib.util
        import zipfile

        script = Path("scripts/package_release.py")
        spec = importlib.util.spec_from_file_location("package_release", script)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "release.zip"
            module.build_release_zip(Path.cwd(), zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                html = archive.read("observer/observer.html").decode("utf-8")

        self.assertNotIn("D:" + "/SilasCheng", html)
        self.assertNotIn("D:" + "\\" + "SilasCheng", html)
        self.assertNotIn("/mnt" + "/data", html)
        self.assertIn("./new_game", html)

    def test_package_release_script_runs_directly(self):
        env = os.environ.copy()
        env["FRV_HOME"] = self.tmp.name

        result = subprocess.run(
            [sys.executable, "scripts/package_release.py"],
            cwd=Path.cwd(),
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fox_river_valley_p1_2_text_only.zip", result.stdout)
        self.assertIn("fox_river_valley_p1_2_observer.zip", result.stdout)

    def test_long_arc_smoke_script_runs_directly(self):
        env = os.environ.copy()
        env["FRV_HOME"] = self.tmp.name

        result = subprocess.run(
            [sys.executable, "scripts/long_arc_smoke.py"],
            cwd=Path.cwd(),
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"ok": true', result.stdout)


class P0FairPlayDocsTests(unittest.TestCase):
    def test_ai_player_guide_contains_fair_play_bans(self):
        text = Path("AI_PLAYER_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn("不能查未来 15/30/58 天天气表", text)
        self.assertIn("不能读代码找资源表或隐藏条件", text)
        self.assertIn("每次 sleep 前检查 hunger、HP、companion、kit、perishable food", text)
        self.assertIn("long_arc_smoke 属于开发测试", text)
