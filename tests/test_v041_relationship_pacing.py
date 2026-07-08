import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V041RelationshipPacingTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def build_home_ready_for_shared_home(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
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

    def test_stage_advances_only_one_step_per_command(self):
        self.build_home_ready_for_shared_home()

        slept = parse_state(cmd("sleep"))

        self.assertEqual(slept["relationship"]["stage"], "surviving_together")
        self.assertEqual(slept["relationship"].get("next_stage_hint"), "shared_home")

    def test_day_two_after_first_sleep_is_surviving_together_not_shared_home(self):
        self.build_home_ready_for_shared_home()

        state = parse_state(cmd("sleep"))

        self.assertEqual(state["day"], 2)
        self.assertEqual(state["relationship"]["stage"], "surviving_together")
        self.assertNotEqual(state["relationship"]["stage"], "shared_home")

    def test_next_stage_hint_when_shared_home_conditions_met(self):
        self.build_home_ready_for_shared_home()
        output = cmd("sleep")
        state = parse_state(output)

        self.assertEqual(state["relationship"]["stage"], "surviving_together")
        self.assertEqual(state["relationship"].get("next_stage_hint"), "shared_home")

    def test_relationship_command_can_trigger_next_stage_later_if_conditions_met(self):
        self.build_home_ready_for_shared_home()
        slept = parse_state(cmd("sleep"))
        self.assertEqual(slept["relationship"]["stage"], "surviving_together")

        advanced = parse_state(cmd("relationship"))

        self.assertEqual(advanced["relationship"]["stage"], "shared_home")

    def test_milestones_store_day_time(self):
        self.build_home_ready_for_shared_home()
        cmd("sleep")
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        milestones = saved["companion"]["relationship"]["milestones"]

        self.assertTrue(milestones)
        self.assertTrue(all(isinstance(item, dict) for item in milestones))
        first_window = next(item for item in milestones if item["id"] == "first_window_table")
        self.assertEqual(first_window["label"], "第一张窗边桌")
        self.assertEqual(first_window["day"], 1)
        self.assertEqual(first_window["time"], "dusk")

    def test_legacy_string_milestones_migrate(self):
        new_game("12071008", companion_name="Yaya")
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["companion"]["relationship"]["milestones"] = ["first_home", "first_window_table"]
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")

        cmd("load")
        cmd("save")
        migrated = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        milestones = migrated["companion"]["relationship"]["milestones"]

        self.assertTrue(all(isinstance(item, dict) for item in milestones))
        self.assertEqual(milestones[0]["id"], "first_home")
        self.assertIsNone(milestones[0]["day"])
        self.assertEqual(milestones[0]["time"], "unknown")

    def test_remember_together_prints_day_time_labels(self):
        self.build_home_ready_for_shared_home()
        cmd("sleep")

        output = cmd("remember together")

        self.assertIn("你们一起记得：", output)
        self.assertIn("Day 1 dusk：第一张窗边桌。", output)
        self.assertIn("Day 1 night：第一次并肩坐下。", output)
        self.assertIn("Day 2 morning：第一次在家醒来。", output)

    def test_relationship_command_shows_stage_meaning(self):
        new_game("12071008", companion_name="Yaya")

        output = cmd("relationship")

        self.assertIn("meaning: 刚来到河谷，一切还没有定下来。", output)

    def test_debug_care_today_mentions_daily_reset(self):
        new_game("12071008", companion_name="Yaya")

        output = cmd("debug companion")

        self.assertIn("care_today（today only, reset each morning）:", output)
        self.assertIn("shared_food=false", output)

    def test_save_load_preserves_milestone_objects(self):
        self.build_home_ready_for_shared_home()
        cmd("sleep")
        cmd("save")
        new_game("other")

        cmd("load")
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        milestones = saved["companion"]["relationship"]["milestones"]

        self.assertTrue(all(isinstance(item, dict) for item in milestones))
        self.assertTrue(any(item["id"] == "first_sleep_at_home" and item["day"] == 2 for item in milestones))


if __name__ == "__main__":
    unittest.main()
