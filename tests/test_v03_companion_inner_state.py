import unittest

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class V03CompanionInnerStateTests(unittest.TestCase):
    def build_home(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        cmd("craft plank")
        cmd("craft stick")
        cmd("build workbench")
        cmd("craft plank")
        return parse_state(cmd("craft stick"))

    def test_family_companion_has_inner_state(self):
        state = parse_state(new_game("12071008", companion_name="Yaya"))
        companion = state["companion"]
        self.assertEqual(companion["security"], 5)
        self.assertEqual(companion["comfort"], 0)
        self.assertIsInstance(companion["thought"], str)
        self.assertEqual(companion["wish"], "build simple_shelter")

    def test_check_companion_returns_thought_and_wish_no_time_advance(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))
        output = cmd("check companion")
        after = parse_state(output)
        self.assertIn("thought", output)
        self.assertIn("wish", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_ask_companion_no_time_advance(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))
        output = cmd("ask companion")
        after = parse_state(output)
        self.assertIn("build simple_shelter", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_wish_updates_from_shelter_to_window_table(self):
        home = self.build_home()
        self.assertEqual(home["companion"]["wish"], "build window_table")
        self.assertIn("第一个家", cmd("journal"))

    def test_building_wish_completion_increases_mood_or_comfort(self):
        home = self.build_home()
        before = parse_state(cmd("check companion"))
        table = parse_state(cmd("build window_table"))
        self.assertGreaterEqual(table["companion"]["mood"], before["companion"]["mood"])
        self.assertGreater(table["companion"]["comfort"], before["companion"]["comfort"])
        self.assertIn("wish", cmd("journal"))

    def test_comfort_companion_changes_security_or_mood(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("check companion"))
        output = cmd("comfort companion")
        after = parse_state(output)
        self.assertTrue(
            after["companion"]["security"] > before["companion"]["security"]
            or after["companion"]["mood"] > before["companion"]["mood"]
        )
        self.assertIn("comfort", output)

    def test_sit_with_companion_requires_valid_place(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))
        failed = parse_state(cmd("sit with companion"))
        self.assertEqual(failed["time"], before["time"])

        self.build_home()
        before_success = parse_state(cmd("check companion"))
        output = cmd("sit with companion")
        after_success = parse_state(output)
        self.assertGreater(after_success["companion"]["comfort"], before_success["companion"]["comfort"])
        self.assertIn("坐", output)

    def test_make_warm_meal_requires_campfire_and_food(self):
        new_game("12071008", companion_name="Yaya")
        fish_state = parse_state(cmd("fish"))
        failed = parse_state(cmd("make warm meal"))
        self.assertEqual(failed["time"], fish_state["time"])

        cmd("move north")
        cmd("gather")
        cmd("chop")
        cmd("chop")
        cmd("build simple_shelter")
        cmd("craft stick")
        cmd("build campfire")
        cmd("cook fish")
        before_meal = parse_state(cmd("check companion"))
        cmd("make warm meal")
        output = cmd("serve warm meal")
        after_meal = parse_state(output)
        self.assertGreater(after_meal["companion"]["warmth"], before_meal["companion"]["warmth"])
        self.assertGreaterEqual(after_meal["hunger"], before_meal["hunger"])
        self.assertIn("warm meal", output)

    def test_save_load_preserves_companion_inner_state(self):
        self.build_home()
        cmd("comfort companion")
        before = parse_state(cmd("save"))
        new_game("other")
        after = parse_state(cmd("load"))
        self.assertEqual(after["companion"]["security"], before["companion"]["security"])
        self.assertEqual(after["companion"]["comfort"], before["companion"]["comfort"])
        self.assertEqual(after["companion"]["thought"], before["companion"]["thought"])
        self.assertEqual(after["companion"]["wish"], before["companion"]["wish"])

    def test_solo_mode_has_no_companion_inner_state(self):
        state = parse_state(new_game("12071008"))
        self.assertNotIn("companion", state)
        output = cmd("ask companion")
        after = parse_state(output)
        self.assertNotIn("companion", after)
        self.assertIn("solo mode", output)


if __name__ == "__main__":
    unittest.main()
