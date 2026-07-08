import importlib.util
import tempfile
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class V021PolishTests(unittest.TestCase):
    def test_zip_paths_are_posix(self):
        script = Path("scripts/package_release.py")
        self.assertTrue(script.exists(), "release package script is missing")
        spec = importlib.util.spec_from_file_location("package_release", script)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "release.zip"
            module.build_release_zip(Path.cwd(), zip_path)
            import zipfile

            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
        self.assertIn("fox_river_valley/actions.py", names)
        self.assertFalse(any("\\" in name for name in names))

    def test_window_table_requires_shelter(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        output = cmd("build window_table")
        state = parse_state(output)
        self.assertIn("还没有屋子，桌子暂时没有窗可对。", output)
        self.assertNotIn("window_table", state["builds_here"])

    def test_failed_window_table_does_not_mutate(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        before = parse_state(cmd("status"))
        before_journal = cmd("journal")
        output = cmd("build window_table")
        after = parse_state(output)
        after_journal = cmd("journal")
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertEqual(after["companion"], before["companion"])
        self.assertEqual(after_journal, before_journal)

    def test_cozy_journal_deduplicated(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        cmd("build window_table")
        cmd("move south")
        cmd("build riverside_bench")
        journal = cmd("journal")
        journal_body = journal.split("\nSTATE ", 1)[0]
        self.assertNotIn("你在当前位置建好了 window_table", journal_body)
        self.assertNotIn("你在当前位置建好了 riverside_bench", journal_body)

    def test_riverside_bench_requires_water_nearby(self):
        new_game("12071008", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        before = parse_state(cmd("status"))
        output = cmd("build riverside_bench")
        after = parse_state(output)
        self.assertIn("水", output)
        self.assertNotIn("riverside_bench", after["builds_here"])
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertEqual(after["companion"], before["companion"])


if __name__ == "__main__":
    unittest.main()
