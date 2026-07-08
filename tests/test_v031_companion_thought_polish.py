import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V031CompanionThoughtPolishTests(unittest.TestCase):
    def build_home(self, seed="12071008"):
        new_game(seed, difficulty="normal", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        return parse_state(cmd("build simple_shelter"))

    def test_thought_templates_are_seeded_and_stable(self):
        first = parse_state(new_game("12071008", companion_name="Yaya"))
        second = parse_state(new_game("12071008", companion_name="Yaya"))
        other = parse_state(new_game("seed-with-different-shape", companion_name="Yaya"))
        self.assertEqual(first["companion"]["thought"], second["companion"]["thought"])
        templates = {
            "她看着还没有家的草地，像在等你决定第一件事。",
            "她把随身的小包抱紧了一点，目光落在附近的树林上。",
            "河谷很安静，她没有催你，只是看着这片还没有名字的地方。",
        }
        self.assertIn(first["companion"]["thought"], templates)
        self.assertIn(other["companion"]["thought"], templates)

    def test_check_companion_does_not_rotate_thought_randomly(self):
        new_game("12071008", companion_name="Yaya")
        first = parse_state(cmd("check companion"))["companion"]["thought"]
        second = parse_state(cmd("check companion"))["companion"]["thought"]
        third = parse_state(cmd("check companion"))["companion"]["thought"]
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_preference_profile_saved_loaded(self):
        before = parse_state(new_game("12071008", companion_name="Yaya"))
        self.assertNotIn("profile", before["companion"])
        debug_before = cmd("debug companion")
        self.assertIn("likes_window_table: true", debug_before)
        self.assertIn("likes_riverside_bench: true", debug_before)
        self.assertIn("likes_warm_meal: true", debug_before)
        self.assertIn("dislikes_cave_at_night: true", debug_before)
        self.assertIn("comfort_priority: medium", debug_before)
        cmd("save")
        profile = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))["companion"]["profile"]
        new_game("other")
        cmd("load")
        debug_after = cmd("debug companion")
        self.assertEqual(profile["comfort_priority"], "medium")
        self.assertIn("likes_window_table: true", debug_after)
        self.assertIn("comfort_priority: medium", debug_after)

    def test_wish_weight_prefers_shelter_before_cozy_items(self):
        state = parse_state(new_game("12071008", companion_name="Yaya"))
        self.assertEqual(state["companion"]["wish"], "build simple_shelter")

    def test_wish_can_prefer_window_table_after_shelter(self):
        home = self.build_home()
        self.assertEqual(home["companion"]["wish"], "build window_table")

    def test_ask_companion_uses_natural_advice(self):
        new_game("12071008", companion_name="Yaya")
        output = cmd("ask companion")
        self.assertIn("Yaya", output)
        self.assertIn("thought:", output)
        self.assertNotIn("她现在像是在提示", output)
        self.assertNotIn("任务", output)

    def test_solo_mode_no_companion_profile(self):
        state = parse_state(new_game("12071008"))
        self.assertNotIn("companion", state)
        output = cmd("check companion")
        after = parse_state(output)
        self.assertNotIn("companion", after)
        self.assertIn("solo mode", output)

    def test_same_seed_same_commands_same_thought(self):
        def run_sequence():
            new_game("12071008", companion_name="Yaya")
            cmd("check companion")
            cmd("ask companion")
            cmd("move north")
            cmd("gather")
            cmd("chop")
            state = parse_state(cmd("build simple_shelter"))
            return state["companion"]["thought"], state["companion"]["wish"]

        self.assertEqual(run_sequence(), run_sequence())


if __name__ == "__main__":
    unittest.main()
