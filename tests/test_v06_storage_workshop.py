import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V06StorageWorkshopTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def saved_state(self) -> dict:
        cmd("save")
        return json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))

    def build_base(self) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        cmd("move north")
        self.add_inventory({"wood": 4, "fiber": 1})
        cmd("build simple_shelter")

    def build_storage_base(self) -> None:
        self.build_base()
        self.add_inventory({"plank": 2})
        cmd("build storage_box")

    def build_workbench_base(self) -> None:
        self.build_base()
        self.add_inventory({"plank": 2, "stick": 2})
        cmd("build workbench")

    def test_storage_deposit_withdraw(self):
        self.build_storage_base()
        self.add_inventory({"wood": 3, "stone": 2})

        deposited = parse_state(cmd("deposit wood 2"))
        self.assertEqual(deposited["inventory"].get("wood"), 1)
        self.assertIn("wood x2", cmd("storage"))

        withdrawn = parse_state(cmd("withdraw wood 1"))
        self.assertEqual(withdrawn["inventory"].get("wood"), 2)
        self.assertIn("wood x1", cmd("storage"))
        self.assertNotIn("storage", withdrawn)

    def test_storage_requires_base_storage_box(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"wood": 2})
        before = parse_state(cmd("status"))
        failed = cmd("deposit wood 1")
        after = parse_state(failed)
        self.assertIn("storage_box", failed)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["inventory"], before["inventory"])

        self.build_storage_base()
        self.add_inventory({"wood": 1})
        cmd("move south")
        away = cmd("deposit wood 1")
        self.assertIn("base", away)
        self.assertEqual(parse_state(away)["inventory"].get("wood"), 1)

    def test_storage_persists_save_load(self):
        self.build_storage_base()
        self.add_inventory({"branch": 4})
        cmd("deposit branch 3")
        cmd("save")
        new_game("other")
        cmd("load")

        self.assertIn("branch x3", cmd("storage"))
        self.assertEqual(self.saved_state()["storage"].get("branch"), 3)

    def test_inventory_grouped_display(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory(
            {
                "berries": 1,
                "wood": 2,
                "plank": 1,
                "stone_axe": 1,
                "strange_shell": 1,
            }
        )
        before = parse_state(cmd("status"))

        output = cmd("inventory")
        after = parse_state(output)

        self.assertIn("food: berries x1", output)
        self.assertIn("raw materials: wood x2", output)
        self.assertIn("processed materials: plank x1", output)
        self.assertIn("tools: stone_axe x1", output)
        self.assertIn("other: strange_shell x1", output)
        self.assertEqual(after["time"], before["time"])

    def test_workbench_required_for_advanced_tools(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"stick": 1, "stone": 2, "cord": 1})
        before = parse_state(cmd("status"))
        failed = cmd("craft stone_axe")
        failed_state = parse_state(failed)
        self.assertIn("需要在 workbench 旁边做这个。", failed)
        self.assertEqual(failed_state["time"], before["time"])
        self.assertNotIn("stone_axe", failed_state["inventory"])

        self.build_workbench_base()
        self.add_inventory({"stick": 1, "stone": 2, "cord": 1})
        crafted = parse_state(cmd("craft stone_axe"))
        self.assertEqual(crafted["inventory"].get("stone_axe"), 1)

    def test_basic_craft_does_not_need_workbench(self):
        new_game("12071008", difficulty="normal")
        self.add_inventory({"branch": 1, "wood": 2, "fiber": 2})

        stick = parse_state(cmd("craft stick"))
        plank = parse_state(cmd("craft plank"))
        cord = parse_state(cmd("craft cord"))

        self.assertGreaterEqual(stick["inventory"].get("stick", 0), 1)
        self.assertGreaterEqual(plank["inventory"].get("plank", 0), 1)
        self.assertGreaterEqual(cord["inventory"].get("cord", 0), 1)

    def test_home_shows_storage_and_stations(self):
        self.build_storage_base()
        self.add_inventory({"plank": 2, "stick": 4, "stone": 3, "wood": 2})
        cmd("build workbench")
        cmd("build campfire")
        cmd("deposit wood 2")

        output = cmd("home")

        self.assertIn("storage: wood x2", output)
        self.assertIn("stations: workbench, campfire", output)
        self.assertIn("safe_sleep: yes", output)

    def test_recipes_show_station_requirement(self):
        new_game("12071008", difficulty="normal")

        axe = cmd("recipes stone_axe")
        meal = cmd("recipes warm_meal")
        table = cmd("recipes window_table")

        self.assertIn("需要 workbench", axe)
        self.assertIn("需要 campfire", meal)
        self.assertIn("需要 workbench", table)

    def test_failed_deposit_withdraw_does_not_mutate(self):
        self.build_storage_base()
        self.add_inventory({"wood": 1})
        before = parse_state(cmd("status"))

        failed_deposit = parse_state(cmd("deposit wood 2"))
        failed_withdraw = parse_state(cmd("withdraw stone 1"))

        self.assertEqual(failed_deposit["inventory"], before["inventory"])
        self.assertEqual(failed_deposit["time"], before["time"])
        self.assertEqual(failed_withdraw["inventory"], before["inventory"])
        self.assertEqual(failed_withdraw["time"], before["time"])
        self.assertIn("storage: empty", cmd("storage"))

    def test_same_seed_same_commands_same_storage_state(self):
        def run_sequence():
            self.build_storage_base()
            self.add_inventory({"wood": 3, "branch": 2})
            cmd("deposit wood 2")
            cmd("deposit branch 1")
            cmd("withdraw wood 1")
            return self.saved_state()["storage"], parse_state(cmd("inventory"))["inventory"]

        first = run_sequence()
        second = run_sequence()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
