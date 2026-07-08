import importlib.util
import json
import tempfile
import unittest
import zipfile
import os
import subprocess
from pathlib import Path


def load_package_module():
    spec = importlib.util.spec_from_file_location("package_release", Path("scripts/package_release.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def forbidden_local_path_markers() -> tuple[str, str, str]:
    return ("/mnt" + "/data", "D:" + "/SilasCheng", "D:" + "\\" + "SilasCheng")


class ReleaseVariantTests(unittest.TestCase):
    def test_text_only_entry_does_not_write_observer_files(self):
        import importlib

        from fox_river_valley import engine

        with tempfile.TemporaryDirectory() as tmp:
            old_home = os.environ.get("FRV_HOME")
            old_observer = os.environ.get("FRV_OBSERVER")
            os.environ["FRV_HOME"] = tmp
            os.environ.pop("FRV_OBSERVER", None)
            try:
                engine._current_state = None
                text_entry = importlib.import_module("fox_river_valley_text")
                text_entry.new_game("12071008")
                text_entry.cmd("look")
                self.assertFalse((Path(tmp) / "observer").exists())
            finally:
                engine._current_state = None
                if old_home is None:
                    os.environ.pop("FRV_HOME", None)
                else:
                    os.environ["FRV_HOME"] = old_home
                if old_observer is None:
                    os.environ.pop("FRV_OBSERVER", None)
                else:
                    os.environ["FRV_OBSERVER"] = old_observer

    def test_text_only_package_excludes_observer_console_files(self):
        module = load_package_module()
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "text.zip"
            module.build_release_zip(Path.cwd(), zip_path, variant="text_only")
            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())

        self.assertIn("fox_river_valley_text.py", names)
        self.assertIn("TEXT_ONLY_PLAYER_GUIDE.md", names)
        self.assertIn("fox_river_valley/engine.py", names)
        self.assertFalse(any(name.startswith("observer/") for name in names))
        self.assertNotIn("Start_Fox_River_Valley.bat", names)
        self.assertNotIn("scripts/run_observer_server.py", names)
        self.assertNotIn("scripts/start_observer.ps1", names)

    def test_observer_package_keeps_live_console_bootstrap(self):
        module = load_package_module()
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "observer.zip"
            module.build_release_zip(Path.cwd(), zip_path, variant="observer")
            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                observer_state = json.loads(archive.read("observer/observer_state.json").decode("utf-8"))

        self.assertIn("observer/observer.html", names)
        self.assertIn("observer/observer_state.json", names)
        self.assertIn("Start_Fox_River_Valley.bat", names)
        self.assertIn("scripts/run_observer_server.py", names)
        self.assertEqual(observer_state["screen"], "start_screen")

    def test_script_builds_both_release_variants_by_default(self):
        module = load_package_module()
        paths = module.default_release_outputs(Path.cwd())

        self.assertEqual(
            {path.name for path in paths},
            {
                "fox_river_valley_p1_2_text_only.zip",
                "fox_river_valley_p1_2_observer.zip",
            },
        )

    def test_public_docs_describe_text_only_and_observer_variants(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        ai_guide = Path("AI_PLAYER_GUIDE.md").read_text(encoding="utf-8")
        text_guide = Path("TEXT_ONLY_PLAYER_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn("fox_river_valley_p1_2_text_only.zip", readme)
        self.assertIn("fox_river_valley_p1_2_observer.zip", readme)
        self.assertIn("from fox_river_valley_text import cmd, new_game", text_guide)
        self.assertIn("Text-only", ai_guide)
        self.assertIn("Observer Console", ai_guide)

    def test_release_packages_do_not_embed_local_dev_paths(self):
        module = load_package_module()
        forbidden = forbidden_local_path_markers()
        text_suffixes = (".md", ".json", ".html", ".py", ".bat", ".ps1", ".txt")

        with tempfile.TemporaryDirectory() as tmp:
            for variant in ("text_only", "observer"):
                zip_path = Path(tmp) / f"{variant}.zip"
                module.build_release_zip(Path.cwd(), zip_path, variant=variant)
                with zipfile.ZipFile(zip_path) as archive:
                    for name in archive.namelist():
                        self.assertNotIn("\\", name)
                        if not name.endswith(text_suffixes):
                            continue
                        text = archive.read(name).decode("utf-8", errors="ignore")
                        for marker in forbidden:
                            self.assertNotIn(marker, text, f"{marker} found in {variant}:{name}")

    def test_release_packages_exclude_development_history_artifacts(self):
        module = load_package_module()

        tracked_files = subprocess.run(
            ["git", "ls-files"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        self.assertFalse(any(name.startswith("PLAYTEST_") for name in tracked_files))
        self.assertFalse(any(name.startswith("docs/superpowers/plans/") for name in tracked_files))
        self.assertNotIn("DESIGN_ALIGNMENT.md", tracked_files)

        with tempfile.TemporaryDirectory() as tmp:
            for variant in ("text_only", "observer"):
                zip_path = Path(tmp) / f"{variant}.zip"
                module.build_release_zip(Path.cwd(), zip_path, variant=variant)
                with zipfile.ZipFile(zip_path) as archive:
                    names = archive.namelist()

                self.assertFalse(any(name.startswith("PLAYTEST_") for name in names))
                self.assertFalse(any(name.startswith("docs/superpowers/plans/") for name in names))
                self.assertNotIn("DESIGN_ALIGNMENT.md", names)
