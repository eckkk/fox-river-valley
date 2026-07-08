import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V05MaterialsCraftingTests(unittest.TestCase):
    def seed_family(self):
        return parse_state(new_game("12071008", difficulty="normal", companion_name="Yaya"))

    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def build_base(self) -> dict:
        self.seed_family()
        self.add_inventory({"wood": 8, "fiber": 4, "branch": 4, "stone": 8})
        return parse_state(cmd("build simple_shelter"))

    def test_new_materials_can_be_gathered_by_terrain(self):
        new_game("12071008")
        forest = parse_state(cmd("move north"))
        self.assertEqual(forest["terrain"], "forest")
        gathered_forest = parse_state(cmd("gather"))
        self.assertIn("branch", gathered_forest["inventory"])
        self.assertIn("herb", gathered_forest["inventory"])

        new_game("12071008")
        grass_gather = parse_state(cmd("gather"))
        self.assertIn("flower", grass_gather["inventory"])

        new_game("12071008")
        cmd("move north")
        cmd("move west")
        hill_gather = parse_state(cmd("gather"))
        self.assertIn("coal", hill_gather["inventory"])

    def test_craft_plank_cord_stick(self):
        new_game("12071008")
        self.add_inventory({"wood": 3, "fiber": 2, "branch": 1})

        stick = parse_state(cmd("craft stick"))
        self.assertGreaterEqual(stick["inventory"].get("stick", 0), 1)
        self.assertEqual(stick["inventory"].get("branch", 0), 0)

        plank = parse_state(cmd("craft plank"))
        self.assertGreaterEqual(plank["inventory"].get("plank", 0), 1)
        self.assertLess(plank["inventory"].get("wood", 0), stick["inventory"].get("wood", 0))

        cord = parse_state(cmd("craft cord"))
        self.assertEqual(cord["inventory"].get("cord"), 1)
        self.assertNotIn("fiber", cord["inventory"])

    def test_window_table_requires_plank_and_stick(self):
        self.build_base()
        self.add_inventory({"wood": 10})
        failed = parse_state(cmd("build window_table"))
        self.assertNotIn("window_table", failed["builds_here"])

        self.add_inventory({"plank": 4, "stick": 4})
        cmd("build workbench")
        built = parse_state(cmd("build window_table"))
        self.assertIn("window_table", built["builds_here"])

    def test_storage_box_requires_plank(self):
        self.build_base()
        self.add_inventory({"wood": 10})
        failed = parse_state(cmd("build storage_box"))
        self.assertNotIn("storage_box", failed["builds_here"])

        self.add_inventory({"plank": 2})
        built = parse_state(cmd("build storage_box"))
        self.assertIn("storage_box", built["builds_here"])

    def test_workbench_builds_at_base(self):
        self.build_base()
        cmd("move south")
        self.add_inventory({"plank": 2, "stick": 2})
        failed = parse_state(cmd("build workbench"))
        self.assertNotIn("workbench", failed["builds_here"])

        cmd("return home")
        built = parse_state(cmd("build workbench"))
        self.assertIn("workbench", built["builds_here"])
        self.assertGreaterEqual(built["companion"]["comfort"], 1)

    def test_campfire_allows_cooked_fish_and_charcoal(self):
        self.build_base()
        self.add_inventory({"stone": 3, "stick": 2, "fish": 1, "wood": 2})
        cmd("build campfire")

        cooked = parse_state(cmd("cook fish"))
        self.assertEqual(cooked["inventory"].get("cooked_fish"), 1)
        self.assertNotIn("fish", cooked["inventory"])

        charcoal = parse_state(cmd("make charcoal"))
        self.assertEqual(charcoal["inventory"].get("charcoal"), 1)

    def test_warm_meal_requires_campfire_food_herb(self):
        self.build_base()
        self.add_inventory({"cooked_fish": 1, "herb": 1})
        no_fire = parse_state(cmd("make warm_meal"))
        self.assertNotIn("warm_meal", no_fire["inventory"])

        self.add_inventory({"stone": 3, "stick": 2})
        cmd("build campfire")
        with_fire = parse_state(cmd("make warm_meal"))
        self.assertEqual(with_fire["inventory"].get("warm_meal"), 1)

    def test_serve_warm_meal_affects_companion_and_bond(self):
        self.build_base()
        self.add_inventory({"stone": 3, "stick": 2, "warm_meal": 1})
        cmd("build campfire")
        before = parse_state(cmd("relationship"))
        before_companion = before["companion"]

        meal = parse_state(cmd("serve warm_meal"))

        self.assertGreater(meal["companion"]["warmth"], before_companion["warmth"])
        self.assertGreater(meal["relationship"]["bond"], before["relationship"]["bond"])

    def test_hearth_requires_advanced_materials(self):
        self.build_base()
        failed = parse_state(cmd("build hearth"))
        self.assertNotIn("hearth", failed["builds_here"])

        self.add_inventory({"stone": 6, "river_clay": 1, "charcoal": 1})
        built = parse_state(cmd("build hearth"))
        self.assertIn("hearth", built["builds_here"])
        self.assertGreaterEqual(built["companion"]["warmth"], 7)

    def test_recipes_command_no_time_advance(self):
        new_game("12071008")
        before = parse_state(cmd("status"))
        output = cmd("recipes window_table")
        after = parse_state(output)

        self.assertIn("window_table", output)
        self.assertIn("plank", output)
        self.assertEqual(after["time"], before["time"])

    def test_save_load_preserves_new_materials_and_stations(self):
        self.build_base()
        self.add_inventory({"plank": 2, "stick": 2, "charcoal": 1, "paper": 1})
        cmd("build workbench")
        before = parse_state(cmd("save"))
        new_game("other")
        after = parse_state(cmd("load"))

        self.assertEqual(after["inventory"].get("charcoal"), before["inventory"].get("charcoal"))
        self.assertEqual(after["inventory"].get("paper"), before["inventory"].get("paper"))
        self.assertIn("workbench", after["builds_here"])

    def test_day_one_shelter_still_reachable(self):
        new_game("12071008")
        cmd("move north")
        cmd("gather")
        cmd("chop")
        shelter = parse_state(cmd("build simple_shelter"))

        self.assertTrue(shelter["shelter"])
        self.assertEqual(shelter["day"], 1)

    def test_same_seed_same_commands_same_material_state(self):
        sequence = [
            "move north",
            "gather",
            "chop",
            "craft plank",
            "craft stick",
            "build simple_shelter",
            "build workbench",
            "recipes window_table",
        ]

        def run():
            new_game("12071008", difficulty="normal", companion_name="Yaya")
            state = None
            for command in sequence:
                state = parse_state(cmd(command))
            return state

        first = run()
        second = run()
        self.assertEqual(first["inventory"], second["inventory"])
        self.assertEqual(first["builds_here"], second["builds_here"])
        self.assertEqual(first["relationship"], second["relationship"])


if __name__ == "__main__":
    unittest.main()
