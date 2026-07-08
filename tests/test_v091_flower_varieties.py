import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


FLOWER_VARIETIES = {
    "foxbell",
    "dew_daisy",
    "river_forget_me_not",
    "hearth_marigold",
    "moon_violet",
}


class V091FlowerVarietiesTests(unittest.TestCase):
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

    def build_plot_with_flower_seed(self, seed: str = "12071008") -> None:
        new_game(seed, difficulty="normal", companion_name="Yaya")
        cmd("move north")
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
        cmd("build simple_shelter")
        cmd("build workbench")
        cmd("craft hoe")
        cmd("craft watering_can")
        cmd("build garden_plot")

    def plant_and_grow_flower(self, seed: str = "12071008") -> None:
        self.build_plot_with_flower_seed(seed)
        cmd("plant flower_seed")
        cmd("water crops")
        cmd("sleep")
        cmd("water crops")
        cmd("sleep")

    def planted_variety_from_garden(self, output: str) -> str:
        for variety in FLOWER_VARIETIES:
            if variety in output:
                return variety
        self.fail(f"no flower variety found in garden output:\n{output}")

    def harvested_variety_from_state(self, state: dict) -> str:
        found = [item for item in FLOWER_VARIETIES if state["inventory"].get(item, 0) > 0]
        self.assertEqual(len(found), 1, state["inventory"])
        return found[0]

    def test_flower_seed_grows_deterministic_variety(self):
        self.build_plot_with_flower_seed("12071008")
        first = cmd("plant flower_seed")
        first_variety = self.planted_variety_from_garden(cmd("garden"))

        self.build_plot_with_flower_seed("12071008")
        second = cmd("plant flower_seed")
        second_variety = self.planted_variety_from_garden(cmd("garden"))

        self.assertEqual(first_variety, second_variety)
        self.assertIn(first_variety, first)
        self.assertIn(second_variety, second)

    def test_harvest_specific_flower_item(self):
        self.plant_and_grow_flower("12071008")

        harvested = parse_state(cmd("harvest"))
        variety = self.harvested_variety_from_state(harvested)

        self.assertEqual(harvested["inventory"].get(variety), 2)
        self.assertNotIn("flower", harvested["inventory"])

    def test_garden_shows_flower_variety_and_color(self):
        self.build_plot_with_flower_seed("12071008")
        cmd("plant flower_seed")

        output = cmd("garden")

        self.assertIn("foxbell", output)
        self.assertIn("color warm apricot / cream edge", output)
        self.assertIn("growth 0/2", output)

    def test_first_foxbell_journal(self):
        self.plant_and_grow_flower("12071008")

        before = parse_state(cmd("check companion"))
        harvested = parse_state(cmd("harvest"))
        journal = cmd("journal")

        self.assertEqual(harvested["inventory"].get("foxbell"), 2)
        self.assertGreaterEqual(harvested["companion"]["mood"], before["companion"]["mood"])
        self.assertIn("小狐铃花", journal)
        self.assertIn("门口亮起", journal)

    def test_flower_log_records_seen_varieties(self):
        self.plant_and_grow_flower("12071008")
        cmd("harvest")

        output = cmd("flower log")
        state = parse_state(output)

        self.assertIn("flower log", output)
        self.assertIn("foxbell", output)
        self.assertEqual(state["time"], "late_morning")

    def test_save_load_preserves_flower_variety(self):
        self.build_plot_with_flower_seed("12071008")
        cmd("plant flower_seed")
        before = cmd("garden")
        cmd("save")

        new_game("other")
        cmd("load")
        after = cmd("garden")

        self.assertEqual(before.splitlines()[1], after.splitlines()[1])
        self.assertIn("foxbell", after)

    def test_same_seed_same_commands_same_flower_variety(self):
        sequence = ["plant flower_seed", "water crops", "sleep", "garden"]

        def run():
            self.build_plot_with_flower_seed("12071008")
            state = parse_state(cmd("status"))
            output = ""
            for command in sequence:
                output = cmd(command)
                state = parse_state(output)
            return state, output

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
