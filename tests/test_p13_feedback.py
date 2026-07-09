import json
import os
import tempfile
import unittest

from fox_river_valley import cmd, engine, new_game
from fox_river_valley.runtime import save_path
from fox_river_valley.state import create_state, save_state
from tests.test_commands import parse_state


class P13FeedbackImplementationTests(unittest.TestCase):
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

    def mutate_save(self, mutator) -> dict:
        cmd("save")
        path = save_path()
        saved = json.loads(path.read_text(encoding="utf-8"))
        mutator(saved)
        path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def add_inventory(self, items: dict[str, int]) -> None:
        def mutate(saved: dict) -> None:
            inventory = saved.setdefault("inventory", {})
            for item, count in items.items():
                inventory[item] = inventory.get(item, 0) + count

        self.mutate_save(mutate)

    def prepare_base(self) -> None:
        new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")
        self.add_inventory({"wood": 4, "fiber": 1})
        cmd("build simple_shelter")

    def prepare_workbench(self) -> None:
        self.prepare_base()
        self.add_inventory({"plank": 4, "stick": 4})
        cmd("build workbench")

    def test_house_progression_accepts_player_facing_aliases(self):
        self.prepare_workbench()
        self.add_inventory({"plank": 4, "stick": 2})
        frame = parse_state(cmd("upgrade home to cabin_frame"))
        self.assertEqual(frame["home_level"], "shelter")
        self.assertIn("cabin_frame", cmd("home"))

        self.add_inventory({"plank": 4, "weathered_wood": 1, "river_clay": 1})
        small = parse_state(cmd("upgrade home to small_cabin"))
        self.assertEqual(small["home_level"], "little_cabin")
        self.assertIn("small_cabin", cmd("home"))

        self.add_inventory({"stone": 3, "stick": 2})
        cmd("build campfire")
        self.add_inventory({"river_glass": 1, "old_tile": 1, "moss_thread": 1})
        cozy = parse_state(cmd("upgrade home to cozy_cabin"))
        self.assertEqual(cozy["home_level"], "warm_cabin")
        self.assertIn("cozy_cabin", cmd("home"))

    def test_decorations_build_with_warm_feedback(self):
        self.prepare_workbench()
        self.add_inventory(
            {
                "fiber": 4,
                "plank": 6,
                "stick": 4,
                "river_clay": 1,
                "foxbell": 1,
                "stinky_shoe": 1,
            }
        )

        outputs = [
            cmd("build bedroll"),
            cmd("build storage_shelf"),
            cmd("build door_charm"),
            cmd("build tool_wall"),
            cmd("build drying_rack"),
            cmd("build flower_pot"),
        ]
        state = parse_state(outputs[-1])

        for item in ("bedroll", "storage_shelf", "door_charm", "tool_wall", "drying_rack", "flower_pot"):
            self.assertIn(item, state["builds_here"])
        self.assertTrue(any("臭鞋" in output or "stinky_shoe" in output for output in outputs))
        self.assertIn("decorations:", cmd("home"))

    def test_craft_aliases_reuse_existing_items_and_recipes(self):
        self.prepare_workbench()
        self.add_inventory({"fiber": 4, "stick": 4, "stone": 4, "clay": 2})

        cord = parse_state(cmd("craft fiber_cord"))
        self.assertEqual(cord["inventory"].get("cord"), 1)
        self.assertNotIn("fiber_cord", cord["inventory"])

        axe = parse_state(cmd("craft basic_axe"))
        self.assertEqual(axe["inventory"].get("stone_axe"), 1)
        self.assertNotIn("basic_axe", axe["inventory"])

        self.add_inventory({"cord": 3})
        self.assertIn("fishing_rod", cmd("recipes fishing_rod"))
        self.assertIn("watering_can", cmd("recipes watering_can"))
        self.assertIn("repair_kit", cmd("recipes repair_kit"))
        rod = parse_state(cmd("craft fishing_rod"))
        flask = parse_state(cmd("craft water_flask"))
        repair = parse_state(cmd("craft repair_kit"))
        self.assertEqual(rod["inventory"].get("fishing_rod"), 1)
        self.assertEqual(flask["inventory"].get("water_flask"), 1)
        self.assertEqual(repair["inventory"].get("repair_kit"), 1)

    def test_look_and_inspect_offer_public_resource_hints(self):
        new_game("12071008")
        look = cmd("look")
        inspect = cmd("inspect")

        for text in (look, inspect):
            self.assertIn("fiber", text)
            self.assertIn("water", text)
            self.assertIn("reed", text)
            self.assertIn("wood", text)
            self.assertIn("clay", text)
            self.assertNotIn("概率", text)

    def test_collect_water_needs_container_and_works_near_water(self):
        state = create_state("12071008")
        state["pos"] = [12, 12]
        save_state(state)
        engine._current_state = None

        no_container = cmd("collect water")
        self.assertIn("water_flask", no_container)
        before = parse_state(cmd("status"))

        self.add_inventory({"water_flask": 1})
        collected = parse_state(cmd("collect water"))
        self.assertEqual(collected["inventory"].get("water"), 1)
        self.assertGreaterEqual(before["energy"], collected["energy"])
        self.assertIn("water_flask", cmd("inventory"))

    def test_spoilage_is_clear_in_inventory_food_and_status(self):
        state = create_state("12071008", companion_name="Yaya")
        state["inventory"] = {"fish": 2, "stale_food": 1, "spoiled_berries": 1}
        state["food_age"] = {"fish": 1}
        save_state(state)
        engine._current_state = None

        inventory = cmd("inventory")
        food = cmd("food")
        status = cmd("status")

        self.assertIn("near expiry", inventory)
        self.assertIn("spoiled", inventory)
        self.assertIn("fish", food)
        self.assertIn("stale_food", food)
        self.assertIn("即将变质", status)

    def test_home_command_uses_player_facing_home_level_names(self):
        self.prepare_workbench()
        self.add_inventory({"plank": 4, "weathered_wood": 1, "river_clay": 1})
        cmd("upgrade home to small_cabin")
        home = cmd("home")
        self.assertIn("home_level: small_cabin (internal: little_cabin)", home)
        self.assertNotIn("home_level: little_cabin\n", home)

        self.add_inventory({"stone": 3, "stick": 2})
        cmd("build campfire")
        self.add_inventory({"river_glass": 1, "old_tile": 1, "moss_thread": 1})
        cmd("upgrade home to cozy_cabin")
        home = cmd("home")
        self.assertIn("home_level: cozy_cabin (internal: warm_cabin)", home)
        self.assertNotIn("home_level: warm_cabin\n", home)

    def test_door_charm_appears_in_decor_command(self):
        self.prepare_workbench()
        self.add_inventory({"stick": 1, "stinky_shoe": 1})
        cmd("build door_charm")

        decor = cmd("decor")

        self.assertIn("door_charm", decor)
        self.assertNotIn("- none", decor)

    def test_player_friendly_craft_text_for_p13_tools(self):
        self.prepare_workbench()
        self.add_inventory({"fiber": 2, "stick": 3, "stone": 4, "clay": 1, "cord": 3, "reed": 2})

        water_flask = cmd("craft water_flask")
        basic_axe = cmd("craft basic_axe")
        basket = cmd("craft basket")
        repair_kit = cmd("craft repair_kit")

        for output in (water_flask, basic_axe, basket, repair_kit):
            self.assertNotIn("削出一根", output)
        self.assertIn("水壶", water_flask)
        self.assertIn("basic_axe", basic_axe)
        self.assertIn("篮子", basket)
        self.assertIn("修理包", repair_kit)

    def test_p13_playtest_notes_exist(self):
        with open("P1_3_FEEDBACK_NOTES.md", encoding="utf-8") as handle:
            text = handle.read()

        self.assertIn("first external human-observed AI playtest", text)
        self.assertIn("house buildings", text)
        self.assertIn("resource hints", text)
