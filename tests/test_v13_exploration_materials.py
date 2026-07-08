import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V13ExplorationMaterialsTests(unittest.TestCase):
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

    def prepare(self, seed: str, *, pos: list[int], weather: str = "clear", time_slot: str = "morning") -> None:
        new_game(seed, difficulty="normal", companion_name="Yaya")
        self.mutate_save({"pos": pos, "weather": weather, "time_slot": time_slot, "rng_counter": 0})

    def test_explore_can_find_river_glass_near_water_after_rain(self):
        self.prepare("river-glass", pos=[12, 12], weather="rain")

        output = cmd("explore")
        state = parse_state(output)

        self.assertIn("river_glass", output)
        self.assertGreaterEqual(state["inventory"].get("river_glass", 0), 1)
        self.assertIn("river_glass", cmd("findings"))
        self.assertIn("river_glass", cmd("journal"))

    def test_ruins_can_find_old_tile(self):
        self.prepare("old-tile", pos=[10, 11], weather="clear")

        output = cmd("explore ruins")
        state = parse_state(output)

        self.assertIn("old_tile", output)
        self.assertGreaterEqual(state["inventory"].get("old_tile", 0), 1)
        self.assertIn("old_tile", cmd("findings"))

    def test_fog_forest_can_find_moss_thread(self):
        self.prepare("moss-thread", pos=[12, 11], weather="fog")

        output = cmd("explore")
        state = parse_state(output)

        self.assertIn("moss_thread", output)
        self.assertGreaterEqual(state["inventory"].get("moss_thread", 0), 1)
        self.assertIn("moss_thread", cmd("findings"))

    def test_weathered_wood_from_abandoned_camp(self):
        saw_camp = False
        for index in range(200):
            self.prepare(f"camp-{index}", pos=[12, 11], weather="clear")
            output = cmd("explore")
            state = parse_state(output)
            if "abandoned camp" in output:
                saw_camp = True
                self.assertIn("weathered_wood", output)
                self.assertGreaterEqual(state["inventory"].get("weathered_wood", 0), 1)
                self.assertIn("weathered_wood", cmd("findings"))
                break

        self.assertTrue(saw_camp, "expected at least one seeded abandoned camp")

    def test_moon_shard_is_seeded_and_rare(self):
        saw_moon = False
        saw_without = False
        moon_seed = None
        first_inventory = None

        for index in range(300):
            seed = f"moon-{index}"
            self.prepare(seed, pos=[10, 11], weather="fog", time_slot="night")
            state = parse_state(cmd("explore ruins"))
            has_moon = state["inventory"].get("moon_shard", 0) > 0
            saw_moon = saw_moon or has_moon
            saw_without = saw_without or not has_moon
            if has_moon and moon_seed is None:
                moon_seed = seed
                first_inventory = state["inventory"]
            if saw_moon and saw_without:
                break

        self.assertTrue(saw_moon, "expected a seeded moon_shard hit")
        self.assertTrue(saw_without, "moon_shard should remain rare, not guaranteed")

        assert moon_seed is not None
        self.prepare(moon_seed, pos=[10, 11], weather="fog", time_slot="night")
        second_inventory = parse_state(cmd("explore ruins"))["inventory"]
        self.assertEqual(first_inventory, second_inventory)

    def test_materials_log_no_time_advance(self):
        self.prepare("materials-log", pos=[12, 12], weather="rain")
        cmd("explore")
        before = parse_state(cmd("status"))

        output = cmd("materials log")
        after = parse_state(output)

        self.assertIn("materials log", output)
        self.assertIn("river_glass", output)
        self.assertIn("future", output)
        self.assertEqual(before["time"], after["time"])
        self.assertEqual(before["day"], after["day"])

    def test_findings_tracks_hidden_materials(self):
        self.prepare("hidden-findings", pos=[12, 12], weather="rain")
        cmd("explore")

        output = cmd("findings")

        self.assertIn("river_glass", output)
        self.assertIn("river_clay", output)

    def test_save_load_preserves_hidden_material_findings(self):
        self.prepare("save-hidden", pos=[12, 12], weather="rain")
        cmd("explore")
        before = cmd("findings")
        cmd("save")

        new_game("other", companion_name="Yaya")
        loaded = parse_state(cmd("load"))
        after = cmd("findings")

        self.assertIn("river_glass", loaded["inventory"])
        self.assertEqual(before.splitlines()[1:3], after.splitlines()[1:3])

    def test_same_seed_same_commands_same_hidden_materials(self):
        sequence = ["explore", "findings", "materials log"]

        def run() -> tuple[dict, list[str]]:
            self.prepare("same-hidden", pos=[12, 12], weather="rain")
            outputs = []
            state = {}
            for command in sequence:
                output = cmd(command)
                outputs.append(output)
                state = parse_state(output)
            return state["inventory"], outputs

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
