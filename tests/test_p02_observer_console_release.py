import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from fox_river_valley import cmd, new_game
from fox_river_valley import engine
from fox_river_valley.state import create_state, save_state
from tests.test_commands import parse_state


class P02ObserverConsoleReleaseTests(unittest.TestCase):
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

    def test_observer_console_has_final_command_surface(self):
        new_game("12071008", companion_name="Alex")
        html = Path(self.tmp.name, "observer", "observer.html").read_text(encoding="utf-8")

        for command in (
            "look",
            "status",
            "inventory",
            "map",
            "check companion",
            "gather",
            "fish",
            "return home",
            "sleep",
        ):
            self.assertIn(f'data-command="{command}"', html)
        self.assertIn('id="command-input"', html)
        self.assertIn('id="run-command"', html)

    def test_observer_state_and_html_show_console_status_fields(self):
        new_game("12071008", companion_name="Alex")
        state_path = Path(self.tmp.name, "observer", "observer_state.json")
        html_path = Path(self.tmp.name, "observer", "observer.html")

        observer_state = json.loads(state_path.read_text(encoding="utf-8"))
        html = html_path.read_text(encoding="utf-8")

        for field in ("hp", "hunger", "energy", "pos", "companion", "family", "home_status", "inventory_summary"):
            self.assertIn(field, observer_state)
        for field in ("hunger", "warmth", "mood", "trust", "security", "comfort", "wish", "thought"):
            self.assertIn(field, observer_state["companion"])
        for label in ("HP", "hunger", "energy", "companion", "wish", "thought", "runtime root", "save path"):
            self.assertIn(label, html)

    def test_package_contains_clean_start_screen_state_and_no_runtime_traces(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("package_release", Path("scripts/package_release.py"))
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as package_tmp:
            zip_path = Path(package_tmp) / "release.zip"
            module.build_release_zip(Path.cwd(), zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                html = archive.read("observer/observer.html").decode("utf-8")
                observer_state = json.loads(archive.read("observer/observer_state.json").decode("utf-8"))

        self.assertFalse(any(name.startswith("saves/") for name in names))
        self.assertEqual(observer_state["screen"], "start_screen")
        self.assertFalse(observer_state["has_save"])
        self.assertIn('"screen":"start_screen"', html.replace(" ", ""))
        for forbidden in ("D:" + "/SilasCheng", "D:" + "\\" + "SilasCheng", "/mnt" + "/data", "runtime_root", "save_path"):
            self.assertNotIn(forbidden, html)
            self.assertNotIn(forbidden, json.dumps(observer_state, ensure_ascii=False))
        self.assertNotIn('"name":"Yaya"', html.replace(" ", ""))

    def test_fresh_server_start_does_not_create_solo_save(self):
        from scripts.run_observer_server import initialize_observer_files
        from fox_river_valley.runtime import observer_paths, save_path

        initialize_observer_files()

        self.assertFalse(save_path().exists())
        self.assertFalse(observer_paths()["state"].exists())
        self.assertIn("start-mode-solo", observer_paths()["html"].read_text(encoding="utf-8"))

    def test_run_tests_entrypoint_runs_unittest_suite(self):
        result = subprocess.run(
            [sys.executable, "scripts/run_tests.py", "-q", "tests/test_commands.py"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_smoke_script_documents_required_checks(self):
        script = Path("scripts/release_smoke.py")
        self.assertTrue(script.exists())
        text = script.read_text(encoding="utf-8")

        for needle in (
            "python -m unittest discover -v",
            "long_arc_smoke.py",
            "forbidden path scan",
            "start_screen",
            "Silas-Yaya demo",
            "Cozy",
            "Survival",
            "AI Playtest",
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
