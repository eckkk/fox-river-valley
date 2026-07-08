import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V04RelationshipStageTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def build_shelter(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        return parse_state(cmd("build simple_shelter"))

    def build_home_with_table(self):
        self.build_shelter()
        self.add_inventory({"plank": 4, "stick": 4})
        cmd("build workbench")
        return parse_state(cmd("build window_table"))

    def test_family_mode_has_relationship_object(self):
        state = parse_state(new_game("12071008", companion_name="Yaya"))

        self.assertEqual(state["relationship"], {"stage": "new_arrival", "bond": 0, "commitment": "none"})
        self.assertNotIn("relationship", state["companion"])

    def test_relationship_command_no_time_advance(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("relationship")
        after = parse_state(output)

        self.assertEqual(before["time"], after["time"])
        self.assertIn("relationship stage: new_arrival", output)
        self.assertIn("bond: 0", output)

    def test_share_food_adds_bond_once_per_day(self):
        new_game("12071008", companion_name="Yaya")
        cmd("fish")
        cmd("fish")

        first = parse_state(cmd("share fish"))
        second = parse_state(cmd("share fish"))

        self.assertEqual(first["relationship"]["bond"], 1)
        self.assertEqual(second["relationship"]["bond"], 1)

    def test_talk_companion_adds_bond_once_per_day(self):
        new_game("12071008", companion_name="Yaya")

        first = parse_state(cmd("talk companion"))
        second = parse_state(cmd("talk companion"))

        self.assertEqual(first["relationship"]["bond"], 1)
        self.assertEqual(second["relationship"]["bond"], 1)

    def test_sit_with_companion_adds_milestone(self):
        self.build_home_with_table()

        state = parse_state(cmd("sit with companion"))
        output = cmd("relationship")

        self.assertGreaterEqual(state["relationship"]["bond"], 1)
        self.assertIn("first_sit_together", output)

    def test_sleep_at_home_can_upgrade_surviving_together(self):
        self.build_shelter()

        state = parse_state(cmd("sleep"))
        relationship = state["relationship"]

        self.assertEqual(state["day"], 2)
        self.assertEqual(relationship["stage"], "surviving_together")
        self.assertGreaterEqual(relationship["bond"], 1)
        self.assertIn("撑过了第一夜", cmd("journal"))

    def test_window_table_can_create_first_window_table_milestone(self):
        state = self.build_home_with_table()
        output = cmd("relationship")

        self.assertGreaterEqual(state["relationship"]["bond"], 1)
        self.assertIn("first_window_table", output)

    def test_stage_shared_home_requires_home_conditions(self):
        self.build_shelter()
        before_sleep = parse_state(cmd("talk companion"))
        self.assertEqual(before_sleep["relationship"]["stage"], "new_arrival")

        cmd("sleep")
        cmd("talk companion")
        cmd("comfort companion")
        cmd("return home")
        self.add_inventory({"plank": 4, "stick": 4})
        cmd("build workbench")
        cmd("build window_table")
        after_sit = parse_state(cmd("sit with companion"))

        self.assertEqual(after_sit["relationship"]["stage"], "shared_home")

    def test_name_home_requires_shelter(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))

        failed = cmd("name home Little Fox Cabin")
        after_failed = parse_state(failed)

        self.assertIn("还没有家", failed)
        self.assertEqual(before["time"], after_failed["time"])
        self.assertIsNone(after_failed["home_name"])

        self.build_shelter()
        named = parse_state(cmd("name home Little Fox Cabin"))
        self.assertEqual(named["home_name"], "Little Fox Cabin")
        self.assertEqual(named["relationship"]["bond"], 2)

    def test_home_command_shows_base_info(self):
        self.build_shelter()
        cmd("name home Little Fox Cabin")

        output = cmd("home")
        state = parse_state(output)

        self.assertEqual(state["home_name"], "Little Fox Cabin")
        self.assertIn("Little Fox Cabin", output)
        self.assertIn("base_pos: [12, 11]", output)
        self.assertIn("base builds: simple_shelter", output)
        self.assertIn("safe_sleep: yes", output)

    def test_save_load_preserves_relationship_home_name_milestones(self):
        self.build_home_with_table()
        cmd("name home Little Fox Cabin")
        cmd("sit with companion")
        cmd("save")

        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["home_name"], "Little Fox Cabin")
        self.assertIn("relationship", saved["companion"])
        self.assertTrue(
            any(item["id"] == "first_window_table" for item in saved["companion"]["relationship"]["milestones"])
        )

        new_game("other")
        loaded = parse_state(cmd("load"))
        relationship = loaded["relationship"]

        self.assertEqual(loaded["home_name"], "Little Fox Cabin")
        self.assertGreaterEqual(relationship["bond"], 1)
        self.assertIn("first_window_table", cmd("debug companion"))

    def test_debug_companion_shows_full_relationship(self):
        self.build_home_with_table()

        output = cmd("debug companion")

        self.assertIn("relationship:", output)
        self.assertIn("stage:", output)
        self.assertIn("bond:", output)
        self.assertIn("milestones:", output)
        self.assertIn("care_today（today only, reset each morning）:", output)

    def test_solo_mode_has_no_relationship_object(self):
        state = parse_state(new_game("12071008"))

        self.assertNotIn("relationship", state)
        self.assertIn("solo mode", cmd("relationship"))
        self.assertIn("solo mode", cmd("home"))

    def test_same_seed_same_commands_same_relationship_state(self):
        def run_sequence():
            new_game("12071008", companion_name="Yaya")
            cmd("move north")
            cmd("gather")
            cmd("chop")
            cmd("build simple_shelter")
            cmd("name home Little Fox Cabin")
            self.add_inventory({"plank": 4, "stick": 4})
            cmd("build workbench")
            cmd("build window_table")
            cmd("talk companion")
            cmd("sit with companion")
            state = parse_state(cmd("sleep"))
            return state["relationship"], state["home_name"]

        self.assertEqual(run_sequence(), run_sequence())


if __name__ == "__main__":
    unittest.main()
