import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V07NightWeatherSpoilageTests(unittest.TestCase):
    def add_inventory(self, items: dict[str, int]) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        saved["inventory"].update(items)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def mutate_save(self, updates: dict) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(saved.get(key), dict):
                saved[key].update(value)
            else:
                saved[key] = value
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def build_home(self, seed: str = "12071008") -> None:
        new_game(seed, difficulty="normal", companion_name="Yaya")
        cmd("move north")
        self.add_inventory({"wood": 4, "fiber": 1})
        cmd("build simple_shelter")

    def prepare_night_home(self, weather: str, builds: tuple[str, ...] = ()) -> dict:
        self.build_home("seed-1")
        if "campfire" in builds:
            self.add_inventory({"stone": 3, "stick": 2})
            cmd("build campfire")
        if "hearth" in builds:
            self.add_inventory({"stone": 6, "river_clay": 1, "charcoal": 1})
            cmd("build hearth")
        self.mutate_save({"time_slot": "night", "weather": weather, "companion": {"warmth": 5, "security": 5}})
        return parse_state(cmd("status"))

    def test_weather_deterministic_by_seed(self):
        rain = parse_state(new_game("seed-1", companion_name="Yaya"))
        rain_again = parse_state(new_game("seed-1", companion_name="Yaya"))
        clear = parse_state(new_game("seed-8", companion_name="Yaya"))

        self.assertEqual(rain["weather"], "rain")
        self.assertEqual(rain_again["weather"], rain["weather"])
        self.assertEqual(clear["weather"], "clear")

    def test_weather_command_no_time_advance(self):
        before = parse_state(new_game("seed-1", companion_name="Yaya"))

        output = cmd("weather")
        after = parse_state(output)

        self.assertIn("rain", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["weather"], before["weather"])

    def test_rain_affects_night_warmth_without_fire(self):
        before = self.prepare_night_home("rain")

        after = parse_state(cmd("sleep"))

        self.assertLess(after["companion"]["warmth"], before["companion"]["warmth"])
        self.assertIn("weather", after)

    def test_campfire_protects_warmth_at_base(self):
        before = self.prepare_night_home("rain", ("campfire",))

        after = parse_state(cmd("sleep"))

        self.assertGreaterEqual(after["companion"]["warmth"], before["companion"]["warmth"] - 1)
        self.assertIn("campfire", cmd("home"))

    def test_hearth_stronger_than_campfire_if_available(self):
        campfire_before = self.prepare_night_home("cold_wind", ("campfire",))
        campfire_after = parse_state(cmd("sleep"))

        hearth_before = self.prepare_night_home("cold_wind", ("hearth",))
        hearth_after = parse_state(cmd("sleep"))

        self.assertLess(campfire_after["companion"]["warmth"], campfire_before["companion"]["warmth"])
        self.assertGreaterEqual(hearth_after["companion"]["warmth"], hearth_before["companion"]["warmth"])

    def test_food_freshness_advances_each_morning(self):
        self.build_home()
        self.add_inventory({"fish": 1})
        self.mutate_save({"time_slot": "night"})

        cmd("sleep")
        output = cmd("food")

        self.assertIn("fish", output)
        self.assertIn("age 1/2", output)

    def test_fish_turns_stale_after_days(self):
        self.build_home()
        self.add_inventory({"fish": 1})
        self.mutate_save({"time_slot": "night"})

        cmd("sleep")
        self.mutate_save({"time_slot": "night"})
        after = parse_state(cmd("sleep"))

        self.assertNotIn("fish", after["inventory"])
        self.assertEqual(after["inventory"].get("stale_fish"), 1)
        self.assertIn("变质", cmd("journal"))

    def test_serve_stale_food_to_companion_fails(self):
        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"stale_food": 1})
        before = parse_state(cmd("status"))

        output = cmd("serve stale_food")
        after = parse_state(output)

        self.assertIn("不适合", output)
        self.assertEqual(after["inventory"].get("stale_food"), 1)
        self.assertEqual(after["time"], before["time"])

    def test_discard_removes_items(self):
        new_game("12071008", companion_name="Yaya")
        self.add_inventory({"spoiled_berries": 2})
        before = parse_state(cmd("status"))

        output = cmd("discard spoiled_berries 1")
        after = parse_state(output)

        self.assertIn("丢弃", output)
        self.assertEqual(after["inventory"].get("spoiled_berries"), 1)
        self.assertEqual(after["time"], before["time"])

    def test_wait_advances_time_and_applies_night_pressure(self):
        new_game("seed-0", companion_name="Yaya")
        self.mutate_save({"time_slot": "dusk", "weather": "cold_wind", "companion": {"warmth": 5, "security": 5}})
        before = parse_state(cmd("status"))

        output = cmd("wait")
        after = parse_state(output)

        self.assertEqual(after["time"], "night")
        self.assertLess(after["companion"]["warmth"], before["companion"]["warmth"])
        self.assertIn(after["night_pressure"], {"mild", "high"})

    def test_save_load_preserves_weather_and_food_age(self):
        new_game("seed-1", companion_name="Yaya")
        self.add_inventory({"fish": 1})
        self.mutate_save({"weather": "rain", "food_age": {"fish": 1}})

        before = parse_state(cmd("save"))
        new_game("other")
        after = parse_state(cmd("load"))
        cmd("save")
        raw = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(after["weather"], before["weather"])
        self.assertEqual(raw["food_age"].get("fish"), 1)

    def test_same_seed_same_commands_same_weather_food_state(self):
        sequence = ["weather", "fish", "food", "wait", "save"]

        def run():
            state = parse_state(new_game("seed-1", companion_name="Yaya"))
            food_output = ""
            for command in sequence:
                output = cmd(command)
                if command == "food":
                    food_output = output
                state = parse_state(output)
            return state["weather"], state["inventory"], food_output

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
