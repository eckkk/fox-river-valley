import os
import tempfile
import unittest

from fox_river_valley import cmd
from fox_river_valley import engine
from fox_river_valley.state import create_state, load_state, save_state
from fox_river_valley.world import tile_key
from tests.test_commands import parse_state


class P12LongFamilyExperienceTests(unittest.TestCase):
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

    def prepare_family(
        self,
        *,
        builds: list[str] | None = None,
        inventory: dict[str, int] | None = None,
        food_age: dict[str, int] | None = None,
        kit: dict | None = None,
    ) -> dict:
        state = create_state("12071008", companion_name="Yaya", companion_profile="silas_yaya")
        state["day"] = 120
        state["calendar"] = {"year": 2, "season": "spring", "day_of_season": 8, "total_day": 120}
        state["pos"] = [12, 12]
        state["base_pos"] = [12, 12]
        state["shelter_pos"] = [12, 12]
        state["home_name"] = "Little Fox Cabin"
        state["home_level"] = "warm_cabin"
        state["home_comfort"] = 6
        state["home_security"] = 6
        state["builds"] = {
            tile_key(state["pos"]): builds
            or ["simple_shelter", "workbench", "storage_box", "window_table", "hearth", "family_bed"]
        }
        state["inventory"] = inventory or {}
        state["food_age"] = food_age or {}
        buddy = state["companion"]
        buddy["hunger"] = 7
        buddy["warmth"] = 7
        buddy["mood"] = 7
        buddy["security"] = 7
        buddy["comfort"] = 6
        buddy["trust"] = 8
        buddy["relationship"]["stage"] = "married_family"
        buddy["relationship"]["bond"] = 16
        if kit:
            state["family"] = {
                "kit_status": "arrived",
                "kit_count": 1,
                "kit_days_waited": 2,
                "kit_arrival_wait_days": 2,
                "expected_species": "silicon_fox",
                "kits": [kit],
            }
        save_state(state)
        return state

    def kit(self, *, mischief: int = 0, security: int = 8, hunger: int = 6, warmth: int = 6) -> dict:
        return {
            "id": "kit_1",
            "species": "silicon_fox",
            "display_name": "小硅狐崽",
            "hidden_breed": "curly_brace_fox",
            "name": None,
            "hunger": hunger,
            "warmth": warmth,
            "sleep": 6,
            "security": security,
            "curiosity": 5,
            "mischief": mischief,
            "favorite_place": "hearth",
            "trait": "curly_brace_tail",
        }

    def body(self, output: str) -> str:
        return output.split("\nSTATE ", 1)[0]

    def test_play_with_calm_secure_kit_has_no_cost_or_false_journal(self):
        self.prepare_family(kit=self.kit(mischief=0, security=8))
        before = parse_state(cmd("status"))

        output = cmd("play with kit")
        after = parse_state(output)
        journal = self.body(cmd("journal"))

        self.assertEqual(after["energy"], before["energy"])
        self.assertIn("已经很安静", output)
        self.assertNotIn("energy -1", output)
        self.assertNotIn("mischief -1", output)
        self.assertNotIn("security +1", output)
        self.assertNotIn("调皮劲收回了一点", journal)

    def test_play_with_kit_security_cap_does_not_claim_security_gain(self):
        self.prepare_family(kit=self.kit(mischief=2, security=8))

        output = cmd("play with kit")
        debug = cmd("debug family")

        self.assertIn("mischief -1", output)
        self.assertNotIn("security +1", output)
        self.assertIn("security: 8", debug)

    def test_talk_companion_uses_state_specific_lines(self):
        variants = [
            {"weather": "rain"},
            {"weather": "cold_wind"},
            {"day": 90},
            {"day": 35, "weather": "clear"},
            {"hunger": 2},
            {"kit": self.kit(mischief=5)},
            {"kit": self.kit(hunger=1)},
            {"home_level": "shelter", "builds": ["simple_shelter"]},
            {"inventory": {"stale_food": 1}},
            {"event": "first_hidden_material:moon_shard"},
        ]
        lines = set()
        for index, variant in enumerate(variants, start=1):
            state = self.prepare_family(
                builds=variant.get("builds"),
                inventory=variant.get("inventory"),
                kit=variant.get("kit"),
            )
            state["day"] = variant.get("day", 120 + index)
            state["weather"] = variant.get("weather", state["weather"])
            state["home_level"] = variant.get("home_level", state["home_level"])
            if "hunger" in variant:
                state["companion"]["hunger"] = variant["hunger"]
            if "event" in variant:
                state["flags"][variant["event"]] = True
            save_state(state)
            lines.add(self.body(cmd("talk companion")).splitlines()[0])

        self.assertGreaterEqual(len(lines), 10)

    def test_sleep_journal_uses_weather_season_home_variants(self):
        state = self.prepare_family()
        state["hunger"] = 8
        state["companion"]["hunger"] = 8
        save_state(state)

        for weather, season in (("clear", "spring"), ("rain", "summer"), ("cold_wind", "winter")):
            cmd("status")
            state = load_state()
            state["weather"] = weather
            state["calendar"]["season"] = season
            state["hunger"] = 8
            state["companion"]["hunger"] = 8
            save_state(state)
            cmd("sleep")

        journal = self.body(cmd("journal"))
        sleep_lines = [line for line in journal.splitlines() if "在家里睡" in line or "睡过一夜" in line]
        self.assertGreaterEqual(len(sleep_lines), 3)
        self.assertGreaterEqual(len(set(sleep_lines)), 3)
        self.assertNotIn("醒来时河谷还很安静。\n- Day", journal)

    def test_sleep_warning_does_not_force_confirm_for_herb_pile(self):
        state = self.prepare_family(inventory={"herb": 30}, food_age={"herb": 4})
        state["hunger"] = 8
        state["companion"]["hunger"] = 8
        save_state(state)

        output = cmd("sleep")
        after = parse_state(output)

        self.assertNotIn("sleep confirm", output)
        self.assertEqual(after["day"], 121)

    def test_make_tea_consumes_herb_as_long_term_use(self):
        self.prepare_family(inventory={"herb": 2})

        output = cmd("make tea")
        state = parse_state(output)

        self.assertIn("herb", output)
        self.assertIn("茶", output)
        self.assertEqual(state["inventory"].get("herb"), 1)

    def test_repeated_same_tile_explore_gets_recently_searched_hint(self):
        state = self.prepare_family()
        state["pos"] = [12, 12]
        state["weather"] = "clear"
        save_state(state)

        outputs = [self.body(cmd("explore")) for _ in range(4)]

        self.assertEqual(len(outputs), len(set(outputs)))
        self.assertTrue(any("刚刚已经找过" in output for output in outputs))
