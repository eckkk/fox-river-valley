import json
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


OBSERVER_DIR = Path("observer")
OBSERVER_STATE = OBSERVER_DIR / "observer_state.json"
OBSERVER_HTML = OBSERVER_DIR / "observer.html"


class V17ObserverViewTests(unittest.TestCase):
    def read_observer_state(self) -> dict:
        self.assertTrue(OBSERVER_STATE.exists(), "observer_state.json was not written")
        return json.loads(OBSERVER_STATE.read_text(encoding="utf-8"))

    def test_observer_state_written_after_new_game(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        state = self.read_observer_state()

        self.assertEqual(state["day"], 1)
        self.assertEqual(state["year"], 1)
        self.assertEqual(state["season"], "spring")
        self.assertEqual(state["day_of_season"], 1)
        self.assertEqual(state["time"], "morning")
        self.assertEqual(state["last_command"], "new_game")
        self.assertEqual(state["companion"]["name"], "Yaya")
        self.assertIn("options", state)
        self.assertEqual(len(state["recent_journal"]), 2)

    def test_observer_state_written_after_cmd(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        cmd("move north")
        state = self.read_observer_state()

        self.assertEqual(state["last_command"], "move north")
        self.assertEqual(state["pos"], [12, 11])
        self.assertIn("last_output_summary", state)
        self.assertTrue(any("北" in line or "走" in line for line in state["last_output_summary"]))

    def test_observer_html_exists(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        self.assertTrue(OBSERVER_HTML.exists())
        self.assertIn("Fox River Valley Observer", OBSERVER_HTML.read_text(encoding="utf-8"))

    def test_observer_html_contains_map_status_journal_options(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        html = OBSERVER_HTML.read_text(encoding="utf-8")

        self.assertIn("小地图", html)
        self.assertIn("@", html)
        self.assertIn("最近行动", html)
        self.assertIn("Journal", html)
        self.assertIn("状态", html)
        self.assertIn("下一步建议", html)

    def test_observer_command_no_time_advance(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("observer")
        after = parse_state(output)

        self.assertIn("observer.html", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_observer_state_does_not_include_hidden_tables(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        state = self.read_observer_state()
        encoded = json.dumps(state, ensure_ascii=False)

        for forbidden in (
            "DIFFICULTY_PROFILES",
            "BUILD_COSTS",
            "CRAFT_RECIPES",
            "PROCESS_RECIPES",
            "FLOWER_VARIETIES",
            "HIDDEN_MATERIAL",
            "probability",
            "rare_conditions",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_save_load_still_works_with_observer(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        cmd("move north")
        before_save = parse_state(cmd("status"))
        cmd("save")

        new_game("other")
        loaded = parse_state(cmd("load"))
        observer_state = self.read_observer_state()

        self.assertEqual(loaded["pos"], before_save["pos"])
        self.assertEqual(observer_state["last_command"], "load")
        self.assertEqual(observer_state["pos"], before_save["pos"])


if __name__ == "__main__":
    unittest.main()
