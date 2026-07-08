import os
import tempfile
import unittest

from fox_river_valley import cmd
from fox_river_valley import engine
from fox_river_valley.state import create_state, save_state
from fox_river_valley.world import tile_key
from tests.test_commands import parse_state


class P11SmallPolishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("FRV_HOME")
        os.environ["FRV_HOME"] = self.tmp.name
        engine._current_state = None

    def tearDown(self):
        engine._current_state = None
        if self.old_home is None:
            os.environ.pop("FRV_HOME", None)
        else:
            os.environ["FRV_HOME"] = self.old_home
        self.tmp.cleanup()

    def prepare_family(self, *, inventory: dict[str, int] | None = None) -> dict:
        state = create_state("12071008", companion_name="Yaya", companion_profile="silas_yaya")
        state["pos"] = [12, 12]
        state["base_pos"] = [12, 12]
        state["shelter_pos"] = [12, 12]
        state["home_level"] = "warm_cabin"
        state["home_comfort"] = 6
        state["home_security"] = 6
        state["builds"] = {
            tile_key(state["pos"]): [
                "simple_shelter",
                "workbench",
                "hearth",
                "window_table",
                "family_bed",
            ]
        }
        state["inventory"] = inventory or {}
        state["companion"]["security"] = 7
        state["companion"]["comfort"] = 6
        state["companion"]["trust"] = 8
        save_state(state)
        return state

    def prepare_empty_garden(self, *, flower_seed_count: int = 1) -> dict:
        state = self.prepare_family(inventory={"flower_seed": flower_seed_count})
        state["garden"] = {
            "next_id": 2,
            "plots": [
                {
                    "id": 1,
                    "pos": [12, 12],
                    "crop": None,
                    "seed": None,
                    "variety": None,
                    "color": None,
                    "growth": 0,
                    "watered_today": False,
                    "watered_days": 0,
                    "growth_days": 0,
                    "planted_day": None,
                    "ready": False,
                }
            ],
        }
        state["companion"]["wish"] = "plant flower_seed"
        save_state(state)
        return state

    def test_discard_stale_food_removes_all_stale_items_and_refreshes_wish(self):
        self.prepare_family(inventory={"stale_food": 2, "stale_fish": 1, "spoiled_berries": 3})
        before = parse_state(cmd("check companion"))
        self.assertEqual(before["companion"]["wish"], "discard stale food")

        output = cmd("discard stale food")
        after = parse_state(output)

        self.assertNotIn("stale_food", after["inventory"])
        self.assertNotIn("stale_fish", after["inventory"])
        self.assertNotIn("spoiled_berries", after["inventory"])
        self.assertNotEqual(after["companion"]["wish"], "discard stale food")
        self.assertIn("变质食物", output)
        self.assertIn("坏浆果", output)

    def test_discard_default_one_and_all_count(self):
        self.prepare_family(inventory={"spoiled_berries": 3, "stale_food": 2})

        one = parse_state(cmd("discard spoiled_berries"))
        self.assertEqual(one["inventory"].get("spoiled_berries"), 2)

        all_output = cmd("discard stale_food all")
        all_state = parse_state(all_output)
        self.assertNotIn("stale_food", all_state["inventory"])
        self.assertIn("变质食物 x2", all_output)

    def test_help_discard_describes_stale_shortcuts(self):
        self.prepare_family()

        output = cmd("help discard")

        self.assertIn("discard stale food", output)
        self.assertIn("discard <item> all", output)
        self.assertIn("spoiled_berries", output)

    def test_recipes_garden_plot_mentions_hoe_and_recipe_hint(self):
        self.prepare_family()

        output = cmd("recipes garden_plot")

        self.assertIn("小菜地", output)
        self.assertIn("需要 hoe", output)
        self.assertIn("recipes hoe", output)

    def test_rope_alias_recipes_and_craft_to_cord(self):
        state = self.prepare_family(inventory={"fiber": 2})
        state["builds"][tile_key(state["pos"])] = ["simple_shelter"]
        save_state(state)

        recipe = cmd("recipes rope")
        crafted = parse_state(cmd("craft rope"))
        output = cmd("inventory")

        self.assertIn("绳子", recipe)
        self.assertEqual(crafted["inventory"].get("cord"), 1)
        self.assertIn("绳子", output)

    def test_plant_flower_seed_refreshes_wish_and_acknowledges_action(self):
        self.prepare_empty_garden()

        output = cmd("plant flower_seed")
        state = parse_state(output)

        self.assertNotEqual(state["companion"]["wish"], "plant flower_seed")
        self.assertIn("Yaya", output)
        self.assertIn("认可", output)

    def test_common_player_text_uses_chinese_labels(self):
        state = self.prepare_family(inventory={"warm_meal": 1, "cooked_fish": 1, "foxbell": 1})
        state["builds"][tile_key(state["pos"])] = ["simple_shelter", "campfire", "window_table"]
        save_state(state)

        inventory = cmd("inventory")
        status = cmd("status")

        self.assertIn("热饭", inventory)
        self.assertIn("熟鱼", inventory)
        self.assertIn("狐铃花", inventory)
        self.assertIn("小火堆", status)
