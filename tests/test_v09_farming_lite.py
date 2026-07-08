import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V09FarmingLiteTests(unittest.TestCase):
    def mutate_save(self, updates: dict) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(saved.get(key), dict):
                saved[key].update(value)
            else:
                saved[key] = value
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def add_inventory(self, items: dict[str, int]) -> None:
        self.mutate_save({"inventory": items})

    def build_home_with_workbench(self, companion: bool = True) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya" if companion else None)
        cmd("move north")
        self.add_inventory({"wood": 4, "fiber": 1, "plank": 2, "stick": 2})
        cmd("build simple_shelter")
        cmd("build workbench")

    def add_farming_tools(self) -> None:
        self.add_inventory({"stick": 1, "stone": 2, "cord": 2, "clay": 2})
        cmd("craft hoe")
        cmd("craft watering_can")

    def build_plot_with_tools(self) -> None:
        self.build_home_with_workbench()
        self.add_farming_tools()
        cmd("build garden_plot")

    def test_craft_hoe_and_watering_can(self):
        self.build_home_with_workbench()
        self.add_inventory({"stick": 1, "stone": 2, "cord": 2, "clay": 2})

        hoe = parse_state(cmd("craft hoe"))
        can = parse_state(cmd("craft watering_can"))

        self.assertEqual(hoe["inventory"].get("hoe"), 1)
        self.assertEqual(can["inventory"].get("watering_can"), 1)

    def test_build_garden_plot_requires_hoe(self):
        self.build_home_with_workbench()
        before = parse_state(cmd("status"))

        failed = cmd("build garden_plot")
        failed_state = parse_state(failed)

        self.assertIn("hoe", failed)
        self.assertEqual(failed_state["time"], before["time"])
        self.assertEqual(failed_state.get("garden_plots"), 0)

        self.add_farming_tools()
        built = parse_state(cmd("build garden_plot"))

        self.assertEqual(built["garden_plots"], 1)
        self.assertLess(built["energy"], failed_state["energy"])

    def test_garden_plot_must_be_near_base(self):
        self.build_home_with_workbench()
        self.add_farming_tools()
        self.mutate_save({"pos": [20, 20]})
        before = parse_state(cmd("status"))

        failed = cmd("build garden_plot")
        failed_state = parse_state(failed)

        self.assertIn("base", failed)
        self.assertEqual(failed_state["time"], before["time"])
        self.assertEqual(failed_state.get("garden_plots"), 0)

    def test_plant_seed_consumes_seed(self):
        self.build_plot_with_tools()
        self.add_inventory({"flower_seed": 1})

        planted = parse_state(cmd("plant flower_seed"))
        output = cmd("garden")

        self.assertNotIn("flower_seed", planted["inventory"])
        self.assertIn("flower", output)
        self.assertIn("growth 0/2", output)

    def test_water_crops_requires_watering_can(self):
        self.build_plot_with_tools()
        self.add_inventory({"flower_seed": 1})
        cmd("plant flower_seed")
        self.mutate_save({"inventory": {"hoe": 1}})
        before = parse_state(cmd("status"))

        failed = cmd("water crops")
        failed_state = parse_state(failed)

        self.assertIn("watering_can", failed)
        self.assertEqual(failed_state["time"], before["time"])

        self.add_inventory({"watering_can": 1})
        watered = cmd("water crops")

        self.assertIn("浇过水", watered)
        self.assertIn("watered yes", cmd("garden"))

    def test_rain_waters_crops(self):
        self.build_plot_with_tools()
        self.add_inventory({"flower_seed": 1})
        cmd("plant flower_seed")
        self.mutate_save({"weather": "rain"})

        cmd("sleep")
        output = cmd("garden")

        self.assertIn("growth 1/2", output)
        self.assertIn("rain", cmd("journal"))

    def test_crop_growth_advances_each_morning_if_watered(self):
        self.build_plot_with_tools()
        self.add_inventory({"herb_seed": 1})
        cmd("plant herb_seed")
        cmd("water crops")

        cmd("sleep")
        output = cmd("garden")

        self.assertIn("growth 1/2", output)
        self.assertEqual(parse_state(output)["ready_crops"], 0)

    def test_harvest_ready_crop_outputs_items(self):
        self.build_plot_with_tools()
        self.add_inventory({"berry_seed": 1})
        cmd("plant berry_seed")
        cmd("water crops")
        cmd("sleep")
        cmd("water crops")
        cmd("sleep")

        harvested = parse_state(cmd("harvest"))

        self.assertGreaterEqual(harvested["inventory"].get("berries", 0), 2)
        self.assertEqual(harvested["ready_crops"], 0)

    def test_harvest_flower_affects_companion(self):
        self.build_plot_with_tools()
        self.add_inventory({"flower_seed": 1})
        cmd("plant flower_seed")
        cmd("water crops")
        cmd("sleep")
        cmd("water crops")
        cmd("sleep")
        before = parse_state(cmd("check companion"))

        harvested = parse_state(cmd("harvest"))

        flower_varieties = {"foxbell", "dew_daisy", "river_forget_me_not", "hearth_marigold", "moon_violet"}
        self.assertTrue(any(harvested["inventory"].get(item, 0) >= 2 for item in flower_varieties))
        self.assertGreaterEqual(harvested["companion"]["comfort"], before["companion"]["comfort"])
        self.assertGreaterEqual(harvested["companion"]["mood"], before["companion"]["mood"])

    def test_garden_command_no_time_advance(self):
        self.build_plot_with_tools()
        before = parse_state(cmd("status"))

        output = cmd("garden")
        after = parse_state(output)

        self.assertIn("garden:", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_state_shows_garden_summary_only(self):
        self.build_plot_with_tools()

        state = parse_state(cmd("status"))

        self.assertEqual(state["garden_plots"], 1)
        self.assertEqual(state["ready_crops"], 0)
        self.assertNotIn("garden", state)

    def test_save_load_preserves_garden(self):
        self.build_plot_with_tools()
        self.add_inventory({"herb_seed": 1})
        cmd("plant herb_seed")
        cmd("water crops")
        cmd("save")

        new_game("other")
        loaded = parse_state(cmd("load"))
        output = cmd("garden")

        self.assertEqual(loaded["garden_plots"], 1)
        self.assertIn("herb", output)
        self.assertIn("watered yes", output)

    def test_same_seed_same_commands_same_garden_state(self):
        sequence = [
            "move north",
            "build simple_shelter",
            "build workbench",
            "craft hoe",
            "craft watering_can",
            "build garden_plot",
            "plant flower_seed",
            "water crops",
            "sleep",
            "garden",
        ]

        def run():
            new_game("12071008", difficulty="normal", companion_name="Yaya")
            self.add_inventory(
                {
                    "wood": 4,
                    "fiber": 1,
                    "plank": 2,
                    "stick": 3,
                    "stone": 2,
                    "cord": 2,
                    "clay": 2,
                    "flower_seed": 1,
                }
            )
            state = parse_state(cmd("status"))
            garden_output = ""
            for command in sequence:
                garden_output = cmd(command)
                state = parse_state(garden_output)
            return state, garden_output

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
