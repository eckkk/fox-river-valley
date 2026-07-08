import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V15KitReadinessArrivalTests(unittest.TestCase):
    def mutate_save(self, mutator) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def prepare_ready_family(self, *, profile: str = "silas_yaya", food: dict[str, int] | None = None) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile=profile)

        def mutate(saved: dict) -> None:
            saved["pos"] = [12, 12]
            saved["base_pos"] = [12, 12]
            saved["shelter_pos"] = [12, 12]
            saved["home_name"] = "Little Fox Cabin"
            saved["home_level"] = "warm_cabin"
            saved["home_comfort"] = 6
            saved["home_security"] = 6
            saved["home_decor"] = {"flower_pot": "foxbell", "hearth": True}
            saved["builds"] = {
                "12,12": [
                    "simple_shelter",
                    "workbench",
                    "storage_box",
                    "window_table",
                    "hearth",
                    "family_bed",
                    "flower_pot",
                ]
            }
            saved["inventory"] = food or {"warm_meal": 1}
            buddy = saved["companion"]
            buddy["security"] = 7
            buddy["comfort"] = 6
            buddy["trust"] = 8
            buddy["relationship"]["stage"] = "married_family"
            buddy["relationship"]["bond"] = 14
            buddy["relationship"]["milestones"] = [
                {"id": "first_home", "label": "第一个家", "day": 1, "time": "morning"},
                {"id": "first_ceremony", "label": "第一次家庭仪式", "day": 2, "time": "evening"},
            ]

        self.mutate_save(mutate)

    def test_family_readiness_requires_married_family(self):
        self.prepare_ready_family()
        self.mutate_save(lambda saved: saved["companion"]["relationship"].update({"stage": "trusted_family"}))
        before = parse_state(cmd("status"))

        output = cmd("family readiness")
        state = parse_state(output)

        self.assertIn("commitment: no", output)
        self.assertIn("missing:", output)
        self.assertIn("married_family", output)
        self.assertEqual(state["time"], before["time"])
        self.assertEqual(state["kit_readiness"], "not_ready")

    def test_family_readiness_requires_warm_cabin_bed_hearth_food(self):
        self.prepare_ready_family()

        def mutate(saved: dict) -> None:
            saved["home_level"] = "little_cabin"
            saved["builds"]["12,12"] = ["simple_shelter", "workbench", "storage_box"]
            saved["home_decor"] = {}
            saved["inventory"] = {}
            saved["storage"] = {}

        self.mutate_save(mutate)

        output = cmd("family readiness")

        self.assertIn("warm_cabin: no", output)
        self.assertIn("family_bed: no", output)
        self.assertIn("hearth: no", output)
        self.assertIn("food security: no", output)
        self.assertIn("missing:", output)
        self.assertIn("warm_meal or berries x3 or cooked_fish x2", output)

    def test_wish_for_kits_fails_when_not_ready(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile="silas_yaya")
        before = parse_state(cmd("status"))

        output = cmd("wish for kits")
        state = parse_state(output)

        self.assertIn("还不能 wish for kits", output)
        self.assertIn("missing:", output)
        self.assertEqual(state["time"], before["time"])
        self.assertEqual(state["family"], {"kit_status": "none", "kit_count": 0})

    def test_wish_for_kits_sets_expecting(self):
        self.prepare_ready_family()

        output = cmd("wish for kits")
        state = parse_state(output)

        self.assertIn("SCENE: Wish for Kits", output)
        self.assertEqual(state["kit_readiness"], "expecting")
        self.assertEqual(state["family"], {"kit_status": "expecting", "kit_count": 0})
        self.assertIn("wish_for_kits", cmd("debug family"))
        self.assertIn("新的家庭成员", cmd("journal"))

    def test_kit_arrival_after_seeded_wait(self):
        self.prepare_ready_family()
        cmd("wish for kits")

        outputs = [cmd("sleep"), cmd("sleep"), cmd("sleep")]
        arrival = "\n".join(outputs)
        state = parse_state(outputs[-1])

        self.assertIn("SCENE: Kit Arrival", arrival)
        self.assertEqual(state["family"], {"kit_status": "arrived", "kit_count": 1})
        self.assertEqual(state["kit_readiness"], "arrived")
        self.assertIn("first_kit_arrival", cmd("debug family"))

    def test_kit_arrival_uses_profile_species(self):
        self.prepare_ready_family(profile="default")
        self.mutate_save(
            lambda saved: (
                saved["companion"].update({"family_species": "river_sprite"}),
                saved["companion"]["companion_profile"].update({"family_species": "river_sprite"}),
            )
        )
        cmd("wish for kits")
        output = "\n".join([cmd("sleep"), cmd("sleep"), cmd("sleep")])

        self.assertIn("river_sprite kit", output)
        self.assertNotIn("小硅狐崽", output)
        self.assertIn("species: river_sprite", cmd("check kits"))

    def test_silas_yaya_kit_is_silicon_fox_curly_brace(self):
        self.prepare_ready_family(profile="silas_yaya")
        cmd("wish for kits")
        cmd("sleep")
        cmd("sleep")
        cmd("sleep")

        output = cmd("check kits")

        self.assertIn("第一只小崽：小硅狐崽", output)
        self.assertIn("species: silicon_fox", output)
        self.assertIn("隐藏品种：Curly-Brace Fox", output)
        self.assertIn("尾巴特征: curly_brace_tail", output)

    def test_check_kits_no_time_advance(self):
        self.prepare_ready_family()
        before = parse_state(cmd("status"))

        output = cmd("check kits")
        after = parse_state(output)

        self.assertIn("当前没有 kit", output)
        self.assertEqual(after["time"], before["time"])

    def test_name_kit_updates_family_state(self):
        self.prepare_ready_family()
        cmd("wish for kits")
        cmd("sleep")
        cmd("sleep")
        cmd("sleep")

        output = cmd("name kit Pip")

        self.assertIn("第一只小崽现在叫 Pip", output)
        self.assertIn("name: Pip", cmd("check kits"))
        self.assertIn("first_kit_named", cmd("debug family"))

    def test_save_load_preserves_kit_status_and_kit_data(self):
        self.prepare_ready_family()
        cmd("wish for kits")
        cmd("sleep")
        cmd("sleep")
        cmd("sleep")
        cmd("name kit Pip")
        cmd("save")

        new_game("other")
        loaded = parse_state(cmd("load"))
        debug = cmd("debug family")

        self.assertEqual(loaded["family"], {"kit_status": "arrived", "kit_count": 1})
        self.assertIn("name: Pip", debug)
        self.assertIn("species: silicon_fox", debug)

    def test_state_family_summary_compact(self):
        self.prepare_ready_family()
        output = cmd("status")
        state = parse_state(output)

        self.assertEqual(state["family"], {"kit_status": "none", "kit_count": 0})
        self.assertNotIn("kits", state["family"])
        self.assertNotIn("kit_days_waited", state["family"])

    def test_default_profile_without_species_cannot_wish_for_kits(self):
        self.prepare_ready_family(profile="default")

        output = cmd("wish for kits")
        state = parse_state(output)

        self.assertIn("family_species", output)
        self.assertEqual(state["family"], {"kit_status": "none", "kit_count": 0})

    def test_same_seed_same_commands_same_kit_arrival(self):
        def run() -> dict:
            self.prepare_ready_family()
            outputs = [cmd("wish for kits"), cmd("sleep"), cmd("sleep"), cmd("sleep"), cmd("check kits")]
            return {
                "state": parse_state(outputs[-1]),
                "check": outputs[-1],
                "debug": cmd("debug family"),
            }

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
