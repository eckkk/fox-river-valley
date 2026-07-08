import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V11CalendarSeasonsTests(unittest.TestCase):
    def mutate_save(self, mutator) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def set_home_for_sleep(self, *, total_day: int = 1, season: str = "spring", day_of_season: int = 1, year: int = 1, weather: str = "clear") -> None:
        def mutate(saved: dict) -> None:
            saved["day"] = total_day
            saved["calendar"] = {
                "season": season,
                "day_of_season": day_of_season,
                "year": year,
                "total_day": total_day,
            }
            saved["weather"] = weather
            saved["pos"] = [12, 12]
            saved["base_pos"] = [12, 12]
            saved["shelter_pos"] = [12, 12]
            saved["builds"] = {"12,12": ["simple_shelter"]}

        self.mutate_save(mutate)

    def add_inventory(self, items: dict[str, int]) -> None:
        def mutate(saved: dict) -> None:
            saved.setdefault("inventory", {}).update(items)

        self.mutate_save(mutate)

    def test_same_seed_same_calendar_weather(self):
        first = parse_state(new_game("12071008"))
        second = parse_state(new_game("12071008"))

        self.assertEqual(
            (first["year"], first["season"], first["day_of_season"], first["weather"]),
            (second["year"], second["season"], second["day_of_season"], second["weather"]),
        )
        self.assertEqual((first["year"], first["season"], first["day_of_season"]), (1, "spring", 1))

    def test_sleep_advances_date(self):
        new_game("12071008", companion_name="Yaya")
        self.set_home_for_sleep()

        state = parse_state(cmd("sleep"))

        self.assertEqual(state["day"], 2)
        self.assertEqual(state["year"], 1)
        self.assertEqual(state["season"], "spring")
        self.assertEqual(state["day_of_season"], 2)

    def test_season_rolls_over_after_28_days(self):
        new_game("12071008", companion_name="Yaya")
        self.set_home_for_sleep(total_day=28, season="spring", day_of_season=28, weather="clear")

        state = parse_state(cmd("sleep"))

        self.assertEqual(state["day"], 29)
        self.assertEqual(state["year"], 1)
        self.assertEqual(state["season"], "summer")
        self.assertEqual(state["day_of_season"], 1)

    def test_calendar_command_no_time_advance(self):
        new_game("12071008", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("calendar")
        after = parse_state(output)

        self.assertIn("Year 1 Spring Day 1", output)
        self.assertIn("weather:", output)
        self.assertIn("today hint:", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["day"], before["day"])

    def test_season_affects_forage_table(self):
        new_game("12071008")
        spring = parse_state(cmd("gather"))

        new_game("12071008")
        self.mutate_save(
            lambda saved: saved.update(
                {
                    "day": 57,
                    "calendar": {"season": "autumn", "day_of_season": 1, "year": 1, "total_day": 57},
                    "weather": "cloudy",
                    "rng_counter": 0,
                }
            )
        )
        autumn = parse_state(cmd("gather"))

        self.assertTrue({"flower_seed", "herb_seed", "reed", "foxbell"}.intersection(spring["inventory"]))
        self.assertTrue({"mushroom", "dry_branch", "seed_pod"}.intersection(autumn["inventory"]))

    def test_rain_still_waters_crops(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        self.mutate_save(
            lambda saved: saved.update(
                {
                    "pos": [12, 12],
                    "base_pos": [12, 12],
                    "shelter_pos": [12, 12],
                    "builds": {"12,12": ["simple_shelter", "workbench"]},
                    "weather": "rain",
                    "inventory": {"hoe": 1},
                    "garden": {
                        "plots": [
                            {
                                "id": 1,
                                "pos": [12, 12],
                                "crop": "herb",
                                "seed": "herb_seed",
                                "variety": None,
                                "color": None,
                                "growth": 0,
                                "watered_today": False,
                                "planted_day": 1,
                                "ready": False,
                            }
                        ],
                        "next_id": 2,
                    },
                }
            )
        )

        cmd("sleep")
        output = cmd("garden")

        self.assertIn("growth 1/2", output)

    def test_memory_dates_saved_loaded(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile="silas_yaya")
        self.add_inventory({"wood": 4, "fiber": 1})
        cmd("build simple_shelter")
        self.mutate_save(
            lambda saved: saved.update(
                {
                    "garden": {
                        "plots": [
                            {
                                "id": 1,
                                "pos": [12, 12],
                                "crop": "flower",
                                "seed": "flower_seed",
                                "variety": "foxbell",
                                "color": "warm apricot / cream edge",
                                "growth": 2,
                                "watered_today": False,
                                "planted_day": 1,
                                "ready": True,
                            }
                        ],
                        "next_id": 2,
                    }
                }
            )
        )
        cmd("harvest")
        self.mutate_save(
            lambda saved: saved.update(
                {
                    "home_name": "Little Fox Cabin",
                    "builds": {"12,12": ["simple_shelter", "campfire", "window_table"]},
                }
            )
        )
        self.add_inventory({"warm_meal": 1})
        self.mutate_save(
            lambda saved: saved["companion"].update(
                {
                    "trust": 7,
                    "comfort": 4,
                    "security": 6,
                    "relationship": {
                        **saved["companion"]["relationship"],
                        "stage": "shared_home",
                        "bond": 10,
                        "milestones": [
                            {"id": "first_home", "label": "第一个家", "day": 1, "time": "morning"},
                            {"id": "stage_shared_home", "label": "关系阶段：shared_home", "day": 1, "time": "morning"},
                        ],
                    },
                }
            )
        )
        cmd("propose with foxbell")
        cmd("hold ceremony")
        cmd("save")

        new_game("other")
        cmd("load")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        memory_dates = saved["memory_dates"]

        self.assertEqual(memory_dates["first_home_day"]["season"], "spring")
        self.assertEqual(memory_dates["first_foxbell_day"]["total_day"], 1)
        self.assertEqual(memory_dates["first_promise_day"]["total_day"], 1)
        self.assertEqual(memory_dates["first_ceremony_day"]["total_day"], 1)


if __name__ == "__main__":
    unittest.main()
