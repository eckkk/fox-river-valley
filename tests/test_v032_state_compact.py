import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


COMPACT_COMPANION_KEYS = {
    "name",
    "hunger",
    "warmth",
    "mood",
    "trust",
    "energy",
    "security",
    "comfort",
    "thought",
    "wish",
    "location",
    "location_mode",
    "pos",
}


class V032StateCompactTests(unittest.TestCase):
    def test_state_companion_is_compact(self):
        state = parse_state(new_game("12071008", companion_name="Yaya"))

        self.assertEqual(set(state["companion"]), COMPACT_COMPANION_KEYS)
        self.assertNotIn("profile", state["companion"])

    def test_check_companion_shows_profile_summary(self):
        before = parse_state(new_game("12071008", companion_name="Yaya"))

        output = cmd("check companion")
        after = parse_state(output)

        self.assertEqual(before["time"], after["time"])
        self.assertIn("likes: window_table, riverside_bench, warm_meal", output)
        self.assertIn("dislikes: cave_at_night", output)
        self.assertIn("comfort_priority: medium", output)
        self.assertNotIn("profile", after["companion"])

    def test_debug_companion_shows_full_profile(self):
        before = parse_state(new_game("12071008", companion_name="Yaya"))

        output = cmd("debug companion")
        after = parse_state(output)

        self.assertEqual(before["time"], after["time"])
        self.assertIn("likes_window_table: true", output)
        self.assertIn("likes_riverside_bench: true", output)
        self.assertIn("likes_warm_meal: true", output)
        self.assertIn("dislikes_cave_at_night: true", output)
        self.assertIn("comfort_priority: medium", output)
        self.assertNotIn("profile", after["companion"])

    def test_save_load_preserves_profile(self):
        new_game("12071008", companion_name="Yaya")
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))

        self.assertIn("profile", saved["companion"])

        new_game("other")
        cmd("load")
        output = cmd("debug companion")

        self.assertIn("likes_window_table: true", output)
        self.assertIn("comfort_priority: medium", output)

    def test_existing_v031_tests_still_pass(self):
        first = parse_state(new_game("12071008", companion_name="Yaya"))
        second = parse_state(new_game("12071008", companion_name="Yaya"))
        self.assertEqual(first["companion"]["thought"], second["companion"]["thought"])
        self.assertEqual(first["companion"]["wish"], "build simple_shelter")

        check = cmd("check companion")
        first_check = parse_state(check)["companion"]["thought"]
        second_check = parse_state(cmd("check companion"))["companion"]["thought"]
        self.assertEqual(first_check, second_check)

        advice = cmd("ask companion")
        self.assertIn("Yaya", advice)
        self.assertIn("thought:", advice)
        self.assertNotIn("她现在像是在提示", advice)
        self.assertNotIn("任务", advice)


if __name__ == "__main__":
    unittest.main()
