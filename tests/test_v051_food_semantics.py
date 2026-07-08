import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V051FoodSemanticsTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def build_family_campfire(self) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        cmd("move north")
        self.add_inventory({"wood": 4, "fiber": 1, "stone": 3, "stick": 2})
        cmd("build simple_shelter")
        cmd("build campfire")

    def test_make_warm_meal_creates_item_without_feeding(self):
        self.build_family_campfire()
        self.add_inventory({"cooked_fish": 1, "herb": 1})
        before = parse_state(cmd("check companion"))

        output = cmd("make warm_meal")
        after = parse_state(output)

        self.assertEqual(after["inventory"].get("warm_meal"), 1)
        self.assertEqual(after["hunger"], before["hunger"])
        self.assertEqual(after["companion"]["hunger"], before["companion"]["hunger"])
        self.assertEqual(after["companion"]["warmth"], before["companion"]["warmth"])
        self.assertEqual(after["relationship"]["bond"], before["relationship"]["bond"])
        self.assertIn("可以用 serve warm_meal 和 Yaya 一起吃。", output)
        self.assertNotIn("第一份热饭", cmd("debug companion"))

    def test_serve_warm_meal_consumes_item_and_feeds_family(self):
        self.build_family_campfire()
        self.add_inventory({"warm_meal": 1})
        before = parse_state(cmd("relationship"))

        output = cmd("serve warm_meal")
        after = parse_state(output)

        self.assertNotIn("warm_meal", after["inventory"])
        self.assertGreater(after["hunger"], before["hunger"])
        self.assertGreater(after["companion"]["hunger"], before["companion"]["hunger"])
        self.assertGreater(after["companion"]["warmth"], before["companion"]["warmth"])
        self.assertGreater(after["relationship"]["bond"], before["relationship"]["bond"])
        self.assertIn("warm_meal", output)

    def test_eat_warm_meal_in_solo_mode(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"warm_meal": 1})
        before = parse_state(cmd("status"))

        eaten = parse_state(cmd("eat warm_meal"))

        self.assertNotIn("warm_meal", eaten["inventory"])
        self.assertEqual(eaten["hunger"], min(8, before["hunger"] + 4))
        self.assertNotIn("companion", eaten)

    def test_serve_warm_meal_requires_companion(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"warm_meal": 1})
        before = parse_state(cmd("status"))

        output = cmd("serve warm_meal")
        after = parse_state(output)

        self.assertIn("没有 companion", output)
        self.assertEqual(after["inventory"].get("warm_meal"), 1)
        self.assertEqual(after["time"], before["time"])

    def test_first_warm_meal_journal_on_serve_not_make(self):
        self.build_family_campfire()
        self.add_inventory({"cooked_fish": 1, "herb": 1})

        cmd("make warm_meal")
        journal_after_make = cmd("journal")
        self.assertNotIn("第一份 warm meal", journal_after_make)
        self.assertNotIn("第一份热饭", cmd("debug companion"))

        cmd("serve warm_meal")
        journal_after_serve = cmd("journal")

        self.assertIn("第一份 warm meal", journal_after_serve)
        self.assertIn("first_warm_meal", cmd("debug companion"))

    def test_save_load_preserves_warm_meal_item(self):
        self.build_family_campfire()
        self.add_inventory({"cooked_fish": 1, "herb": 1})
        made = parse_state(cmd("make warm_meal"))
        cmd("save")
        new_game("other")

        loaded = parse_state(cmd("load"))

        self.assertEqual(loaded["inventory"].get("warm_meal"), made["inventory"].get("warm_meal"))

    def test_recipes_warm_meal_describes_make_and_serve(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("recipes warm_meal")
        after = parse_state(output)

        self.assertIn("warm_meal 加工：cooked_fish x1, herb x1，需要 campfire", output)
        self.assertIn("serve warm_meal：消耗 warm_meal x1，恢复自己和 companion", output)
        self.assertEqual(after["time"], before["time"])


if __name__ == "__main__":
    unittest.main()
