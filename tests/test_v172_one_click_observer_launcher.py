import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class V172OneClickObserverLauncherTests(unittest.TestCase):
    def with_env(self, key: str, value: str | None):
        old = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
        self.addCleanup(self.restore_env, key, old)

    @staticmethod
    def restore_env(key: str, value: str | None) -> None:
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    def test_runtime_root_uses_env_frv_home(self):
        from fox_river_valley.runtime import runtime_root

        with tempfile.TemporaryDirectory() as tmp:
            self.with_env("FRV_HOME", tmp)

            self.assertEqual(runtime_root(), Path(tmp).resolve())

    def test_runtime_paths_not_temp_when_frv_home_set(self):
        from fox_river_valley.runtime import observer_paths, save_path

        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            self.with_env("FRV_HOME", home)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)

                new_game("12071008", difficulty="normal", companion_name="Yaya")
                cmd("save")

                saved = save_path()
                paths = observer_paths()
                self.assertTrue(saved.exists())
                self.assertTrue(paths["html"].exists())
                self.assertTrue(paths["state"].exists())
                self.assertTrue(saved.is_relative_to(Path(home).resolve()))
                self.assertTrue(paths["state"].is_relative_to(Path(home).resolve()))
                self.assertFalse((Path(cwd) / "observer" / "observer_state.json").exists())
                self.assertFalse((Path(cwd) / "saves" / "fox_river_valley.save.json").exists())
            finally:
                os.chdir(old_cwd)

    def test_runtime_command_no_time_advance(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("runtime")
        after = parse_state(output)

        self.assertIn("Runtime root:", output)
        self.assertIn("Save path:", output)
        self.assertIn("Observer HTML:", output)
        self.assertIn("Observer state:", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_observer_command_includes_runtime_root_and_live_url(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        output = cmd("observer")

        self.assertIn("Runtime root:", output)
        self.assertIn("Observer HTML:", output)
        self.assertIn("Observer state:", output)
        self.assertIn("Live URL: http://127.0.0.1:8765/observer.html", output)
        self.assertIn("Start_Fox_River_Valley.bat", output)
        self.assertIn("python scripts/run_observer_server.py", output)

    def test_start_bat_exists(self):
        script = Path("Start_Fox_River_Valley.bat")

        self.assertTrue(script.exists())
        text = script.read_text(encoding="utf-8")
        self.assertIn("FRV_HOME", text)
        self.assertIn("scripts\\start_observer.ps1", text)
        self.assertIn("http://127.0.0.1:8765/observer.html", text)

    def test_play_module_exists(self):
        module_path = Path("fox_river_valley/play.py")
        spec = importlib.util.spec_from_file_location("fox_river_valley.play", module_path)

        self.assertTrue(module_path.exists())
        self.assertIsNotNone(spec)
        text = module_path.read_text(encoding="utf-8")
        self.assertIn("FRV>", text)
        self.assertIn("webbrowser.open", text)
        self.assertIn("run_observer_server", text)

    def test_readme_has_one_click_player_start(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("For players", readme)
        self.assertIn("双击 Start_Fox_River_Valley.bat", readme)
        self.assertIn("浏览器会打开观战页", readme)
        self.assertIn("页面会自动更新", readme)

    def test_kimi_player_guide_exists(self):
        guide = Path("AI_PLAYER_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn("cmd(\"runtime\")", guide)
        self.assertIn("FRV_HOME", guide)
        self.assertIn("不要读源码", guide)
        self.assertIn("不要进入工程模式", guide)


if __name__ == "__main__":
    unittest.main()
