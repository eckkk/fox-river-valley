import os
import tempfile
import unittest

from fox_river_valley import cmd
from fox_river_valley import engine
from fox_river_valley.state import create_state, save_state
from fox_river_valley.world import tile_key
from tests.test_commands import parse_state


class P1FamilyExperiencePatchTests(unittest.TestCase):
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
        storage: dict[str, int] | None = None,
        kit: dict | None = None,
    ) -> dict:
        state = create_state("12071008", companion_name="Yaya", companion_profile="silas_yaya")
        state["pos"] = [12, 12]
        state["base_pos"] = [12, 12]
        state["shelter_pos"] = [12, 12]
        state["home_name"] = "Little Fox Cabin"
        state["home_level"] = "warm_cabin"
        state["home_comfort"] = 6
        state["home_security"] = 6
        state["builds"] = {tile_key(state["pos"]): builds or ["simple_shelter", "workbench", "hearth", "family_bed"]}
        state["inventory"] = inventory or {}
        state["storage"] = storage or {}
        buddy = state["companion"]
        buddy["security"] = 7
        buddy["comfort"] = 6
        buddy["trust"] = 8
        buddy["relationship"]["stage"] = "married_family"
        buddy["relationship"]["bond"] = 14
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

    def kit(self, *, hunger: int = 6, warmth: int = 6, mischief: int = 3) -> dict:
        return {
            "id": "kit_1",
            "species": "silicon_fox",
            "display_name": "小硅狐崽",
            "hidden_breed": "curly_brace_fox",
            "name": None,
            "hunger": hunger,
            "warmth": warmth,
            "sleep": 6,
            "security": 6,
            "curiosity": 5,
            "mischief": mischief,
            "favorite_place": "hearth",
            "trait": "curly_brace_tail",
        }

    def test_hearth_blocks_campfire_wish(self):
        state = self.prepare_family(builds=["simple_shelter", "workbench", "hearth"])
        state["weather"] = "cold_wind"
        state["companion"]["warmth"] = 2
        save_state(state)
        state = parse_state(cmd("check companion"))

        self.assertNotEqual(state["companion"]["wish"], "build campfire")
        self.assertNotIn("wish: build campfire", cmd("check companion"))

    def test_warm_cabin_without_fire_does_not_suggest_warm_meal(self):
        state = self.prepare_family(builds=["simple_shelter", "workbench", "family_bed"])
        state["companion"]["warmth"] = 2
        save_state(state)

        state = parse_state(cmd("check companion"))

        self.assertNotEqual(state["companion"]["wish"], "make warm meal")

    def test_warm_meal_completes_fresh_food_wish(self):
        state = self.prepare_family(
            builds=["simple_shelter", "workbench", "hearth"],
            inventory={"warm_meal": 1},
        )
        state["companion"]["wish"] = "find fresh food"
        save_state(state)

        output = cmd("serve warm_meal")
        journal = cmd("journal")

        self.assertIn("warm meal", output)
        self.assertIn("wish：find fresh food", journal)

    def test_stale_food_causes_discard_stale_food_wish(self):
        self.prepare_family(
            builds=["simple_shelter", "workbench", "hearth"],
            inventory={"stale_food": 1, "warm_meal": 1},
        )

        output = cmd("check companion")
        state = parse_state(output)

        self.assertEqual(state["companion"]["wish"], "discard stale food")
        self.assertIn("wish: discard stale food", output)

    def test_special_fish_can_be_cooked(self):
        self.prepare_family(
            builds=["simple_shelter", "workbench", "hearth"],
            inventory={"silver_fish": 1},
        )

        output = cmd("cook fish")
        state = parse_state(output)

        self.assertIn("silver_fish", output)
        self.assertEqual(state["inventory"].get("silver_fish", 0), 0)
        self.assertEqual(state["inventory"].get("cooked_fish"), 1)

    def test_help_includes_family_commands_after_unlock(self):
        self.prepare_family()

        output = cmd("help propose")

        self.assertIn("propose with <item>", output)
        self.assertIn("shared_home", output)
        self.assertIn("bond >= 10", output)
        self.assertIn("未解锁", cmd("help check kits"))

    def test_status_warns_about_perishable_food(self):
        state = self.prepare_family(inventory={"fish": 3})
        state["food_age"] = {"fish": 1}
        save_state(state)

        output = cmd("status")

        self.assertIn("即将变质", output)
        self.assertIn("fish x3", output)
        self.assertIn("companion wish", output)
        self.assertIn("保暖", output)

    def test_kit_mischief_changes_check_kits_text(self):
        self.prepare_family(kit=self.kit(mischief=1))
        quiet = cmd("check kits")

        self.prepare_family(kit=self.kit(mischief=5))
        lively = cmd("check kits")

        self.assertIn("安静", quiet)
        self.assertIn("调皮", lively)
        self.assertNotEqual(quiet, lively)

    def test_play_with_kit_lowers_mischief(self):
        self.prepare_family(kit=self.kit(mischief=4))

        output = cmd("play with kit")
        debug = cmd("debug family")

        self.assertIn("陪第一只小崽玩了一会儿", output)
        self.assertIn("mischief: 3", debug)

    def test_feed_kit_improves_kit_hunger(self):
        self.prepare_family(inventory={"berries": 1}, kit=self.kit(hunger=2))

        output = cmd("feed kit")
        check = cmd("check kits")

        self.assertIn("第一只小崽吃了 berries", output)
        self.assertIn("hunger 4", check)
