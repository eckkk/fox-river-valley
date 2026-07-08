import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


FISH_SPECIES = {"fish", "silver_fish", "rain_carp", "dusk_eel", "river_crab"}


class V08FishingRuinsExplorationTests(unittest.TestCase):
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

    def fish_count(self, state: dict) -> int:
        return sum(state["inventory"].get(item, 0) for item in FISH_SPECIES)

    def go_to_ruins(self) -> None:
        cmd("move north")
        cmd("move west")
        cmd("move west")

    def test_fishing_weather_affects_possible_catches(self):
        clear = parse_state(new_game("seed-8", companion_name="Yaya"))
        self.assertEqual(clear["weather"], "clear")
        clear_catch = parse_state(cmd("fish"))

        rain = parse_state(new_game("seed-1", companion_name="Yaya"))
        self.assertEqual(rain["weather"], "rain")
        rain_catch = parse_state(cmd("fish"))

        self.assertIn("silver_fish", clear_catch["inventory"])
        self.assertIn("rain_carp", rain_catch["inventory"])

    def test_fishing_rod_improves_fishing_result(self):
        new_game("12071008", companion_name="Yaya")
        bare = parse_state(cmd("fish"))

        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"fishing_rod": 1})
        rod = parse_state(cmd("fish"))

        self.assertGreater(self.fish_count(rod), self.fish_count(bare))
        self.assertGreaterEqual(rod["inventory"].get("fish", 0), 2)

    def test_fish_log_records_seen_species(self):
        new_game("seed-1", companion_name="Yaya")
        cmd("fish")

        output = cmd("fish log")
        state = parse_state(output)

        self.assertIn("fish log", output)
        self.assertIn("rain_carp", output)
        self.assertEqual(state["time"], "late_morning")

    def test_drift_bottle_opens_with_seeded_text(self):
        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"drift_bottle": 1})

        first = cmd("open drift_bottle")
        first_state = parse_state(first)

        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"drift_bottle": 1})
        second = cmd("open drift_bottle")

        self.assertEqual(first.splitlines()[0], second.splitlines()[0])
        self.assertNotIn("drift_bottle", first_state["inventory"])
        self.assertTrue(any(item in first_state["inventory"] for item in {"paper", "reed", "map_fragment", "small_charm"}))

    def test_explore_ruins_requires_ruins_nearby(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))

        failed = cmd("explore ruins")
        failed_state = parse_state(failed)

        self.assertIn("遗迹", failed)
        self.assertEqual(failed_state["time"], before["time"])

    def test_explore_ruins_can_give_map_fragment(self):
        new_game("12071008", companion_name="Yaya")
        self.go_to_ruins()

        explored = parse_state(cmd("explore ruins"))

        self.assertEqual(explored["terrain"], "ruins")
        self.assertGreaterEqual(explored["inventory"].get("map_fragment", 0), 1)
        self.assertIn("ruins", cmd("journal"))

    def test_explore_events_deterministic(self):
        sequence = ["move north", "explore", "explore", "journal"]

        def run():
            state = parse_state(new_game("12071008", companion_name="Yaya"))
            output = ""
            for command in sequence:
                output = cmd(command)
                state = parse_state(output)
            return state["inventory"], output

        self.assertEqual(run(), run())

    def test_map_fragment_hint_at_three(self):
        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"map_fragment": 2})
        self.go_to_ruins()

        output = cmd("explore ruins")
        state = parse_state(output)

        self.assertGreaterEqual(state["inventory"].get("map_fragment", 0), 3)
        self.assertIn("旧路", output)
        self.assertIn("旧路", cmd("journal"))

    def test_explore_weather_pressure(self):
        new_game("seed-1", companion_name="Yaya")
        self.mutate_save({"weather": "rain"})
        before = parse_state(cmd("status"))

        output = cmd("explore")
        after = parse_state(output)

        self.assertIn("天气", output)
        self.assertLess(after["energy"], before["energy"])

    def test_save_load_preserves_fish_log_and_fragments(self):
        new_game("seed-1", companion_name="Yaya")
        cmd("fish")
        self.add_inventory({"map_fragment": 2})
        before_log = cmd("fish log")
        cmd("save")

        new_game("other")
        loaded = parse_state(cmd("load"))
        after_log = cmd("fish log")

        self.assertEqual(loaded["inventory"].get("map_fragment"), 2)
        self.assertIn("rain_carp", before_log)
        self.assertIn("rain_carp", after_log)

    def test_same_seed_same_commands_same_exploration_state(self):
        sequence = ["weather", "fish", "fish log", "move north", "explore", "move west", "move west", "explore ruins"]

        def run():
            state = parse_state(new_game("12071008", companion_name="Yaya"))
            for command in sequence:
                state = parse_state(cmd(command))
            return state["inventory"], state["relationship"], cmd("journal")

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
