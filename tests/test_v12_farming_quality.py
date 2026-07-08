import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V12FarmingQualityTests(unittest.TestCase):
    def mutate_save(self, mutator) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def prepare_ready_crop(
        self,
        *,
        seed: str = "12071008",
        crop: str = "flower",
        variety: str | None = "foxbell",
        season: str = "spring",
        day: int | None = None,
        weather: str = "clear",
        watered_days: int = 2,
        growth: int = 2,
        comfort: int = 4,
        base_builds: list[str] | None = None,
        pos: list[int] | None = None,
        time_slot: str = "morning",
    ) -> None:
        new_game(seed, difficulty="normal", companion_name="Yaya")
        position = pos or [12, 12]
        builds = base_builds or ["simple_shelter", "window_table"]
        season_start = {"spring": 1, "summer": 29, "autumn": 57, "winter": 85}
        total_day = day or season_start[season]

        def mutate(saved: dict) -> None:
            saved["day"] = total_day
            saved["calendar"] = {
                "year": 1,
                "season": season,
                "day_of_season": ((total_day - 1) % 28) + 1,
                "total_day": total_day,
            }
            saved["weather"] = weather
            saved["time_slot"] = time_slot
            saved["pos"] = list(position)
            saved["base_pos"] = list(position)
            saved["shelter_pos"] = list(position)
            saved["builds"] = {f"{position[0]},{position[1]}": list(builds)}
            saved["companion"]["comfort"] = comfort
            saved["garden"] = {
                "plots": [
                    {
                        "id": 1,
                        "pos": list(position),
                        "crop": crop,
                        "seed": f"{crop[:-1]}_seed" if crop in {"berries"} else ("herb_seed" if crop == "herb" else "flower_seed"),
                        "variety": variety,
                        "color": "warm apricot / cream edge" if variety == "foxbell" else None,
                        "growth": growth,
                        "watered_today": False,
                        "watered_days": watered_days,
                        "growth_days": growth,
                        "planted_day": 1,
                        "ready": growth >= 2,
                    }
                ],
                "next_id": 2,
            }

        self.mutate_save(mutate)

    def harvest_output(self) -> tuple[str, dict]:
        output = cmd("harvest")
        return output, parse_state(output)

    def test_crop_quality_deterministic(self):
        self.prepare_ready_crop()
        first_output, first_state = self.harvest_output()

        self.prepare_ready_crop()
        second_output, second_state = self.harvest_output()

        self.assertIn("品质：perfect", first_output)
        self.assertEqual(first_output.splitlines()[1:3], second_output.splitlines()[1:3])
        self.assertEqual(first_state["inventory"], second_state["inventory"])

    def test_season_match_improves_quality(self):
        self.prepare_ready_crop(season="spring", comfort=4)
        spring_output, spring_state = self.harvest_output()

        self.prepare_ready_crop(season="summer", comfort=4)
        summer_output, summer_state = self.harvest_output()

        self.assertIn("品质：perfect", spring_output)
        self.assertIn("品质：good", summer_output)
        self.assertIn("perfect_foxbell", spring_state["inventory"])
        self.assertIn("good_foxbell", summer_state["inventory"])

    def test_off_season_slows_or_lowers_quality(self):
        self.prepare_ready_crop(season="winter", growth=0, watered_days=0, weather="clear")

        cmd("sleep")
        output = cmd("garden")

        self.assertIn("growth 0/2", output)
        self.assertIn("season fit off-season", output)

    def test_rain_bonus_for_river_forget_me_not(self):
        self.prepare_ready_crop(variety="river_forget_me_not", season="summer", weather="rain", comfort=4)

        output, state = self.harvest_output()

        self.assertIn("品质：perfect", output)
        self.assertIn("river_blue_petal", output)
        self.assertGreaterEqual(state["inventory"].get("river_blue_petal", 0), 1)

    def test_perfect_foxbell_can_yield_dye_material(self):
        self.prepare_ready_crop(variety="foxbell", season="spring", weather="clear", comfort=4)

        output, state = self.harvest_output()

        self.assertIn("品质：perfect", output)
        self.assertIn("foxbell_dye_material", output)
        self.assertGreaterEqual(state["inventory"].get("foxbell_dye_material", 0), 1)

    def test_autumn_food_crop_can_yield_seed_pod(self):
        self.prepare_ready_crop(crop="herb", variety=None, season="autumn", weather="clear", comfort=4)

        output, state = self.harvest_output()

        self.assertIn("品质：good", output)
        self.assertIn("seed_pod", output)
        self.assertGreaterEqual(state["inventory"].get("seed_pod", 0), 1)

    def test_flower_log_tracks_best_quality(self):
        self.prepare_ready_crop(variety="foxbell", season="spring", comfort=4)
        cmd("harvest")

        output = cmd("flower log")

        self.assertIn("best_quality perfect", output)
        self.assertIn("rare_yields_found foxbell_dye_material", output)

    def test_harvest_untracked_mature_plot_backfills_planted_count(self):
        self.prepare_ready_crop(variety="foxbell", season="spring", comfort=4)

        cmd("harvest")
        output = cmd("flower log")

        self.assertIn("planted 1, harvested 1", output)

    def test_flower_log_never_shows_harvested_more_than_planted(self):
        self.prepare_ready_crop(variety="foxbell", season="spring", comfort=4)

        cmd("harvest")
        output = cmd("flower log")

        self.assertNotIn("planted 0, harvested 1", output)

    def test_crop_log_never_shows_harvested_more_than_planted(self):
        self.prepare_ready_crop(crop="herb", variety=None, season="autumn", comfort=4)

        cmd("harvest")
        output = cmd("crop log")

        self.assertNotIn("planted 0, harvested 1", output)
        self.assertIn("planted 1, harvested 1", output)

    def test_crop_log_no_time_advance(self):
        self.prepare_ready_crop(variety="foxbell", season="spring", comfort=4)
        cmd("harvest")
        before = parse_state(cmd("status"))

        output = cmd("crop log")
        after = parse_state(output)

        self.assertIn("crop log:", output)
        self.assertIn("foxbell", output)
        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["day"], before["day"])

    def test_save_load_preserves_crop_quality_history(self):
        self.prepare_ready_crop(variety="foxbell", season="spring", comfort=4)
        cmd("harvest")
        before = cmd("crop log")
        cmd("save")

        new_game("other")
        cmd("load")
        after = cmd("crop log")

        self.assertEqual(before.splitlines()[1], after.splitlines()[1])
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["crop_log"]["foxbell"]["best_quality"], "perfect")

    def test_same_seed_same_commands_same_quality_result(self):
        def run() -> dict:
            self.prepare_ready_crop(seed="quality-seed", variety="moon_violet", season="autumn", weather="fog", comfort=4)
            state = parse_state(cmd("harvest"))
            return {"inventory": state["inventory"], "flower_log": cmd("flower log")}

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
