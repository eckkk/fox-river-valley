import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V14HomeUpgradeDecorationTests(unittest.TestCase):
    def mutate_save(self, mutator) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def add_inventory(self, items: dict[str, int]) -> None:
        def mutate(saved: dict) -> None:
            saved.setdefault("inventory", {}).update(items)

        self.mutate_save(mutate)

    def prepare_base(self) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        self.add_inventory({"wood": 4, "fiber": 1})
        cmd("build simple_shelter")

    def prepare_workshop_home(self) -> None:
        self.prepare_base()
        self.add_inventory({"plank": 4, "stick": 2})
        cmd("build workbench")
        cmd("build storage_box")

    def prepare_little_cabin(self) -> None:
        self.prepare_workshop_home()
        self.add_inventory({"plank": 4, "weathered_wood": 1, "river_clay": 1})
        cmd("upgrade home to little_cabin")

    def test_upgrade_home_to_little_cabin_requires_materials(self):
        self.prepare_workshop_home()
        before = parse_state(cmd("status"))

        failed = cmd("upgrade home to little_cabin")
        failed_state = parse_state(failed)

        self.assertIn("材料不够", failed)
        self.assertEqual(failed_state["time"], before["time"])
        self.assertEqual(failed_state["home_level"], "shelter")

        self.add_inventory({"plank": 4, "weathered_wood": 1, "river_clay": 1})
        upgraded = parse_state(cmd("upgrade home to little_cabin"))

        self.assertEqual(upgraded["home_level"], "little_cabin")
        self.assertGreaterEqual(upgraded["home_comfort"], 2)
        self.assertGreaterEqual(upgraded["home_security"], 1)
        self.assertIn("little_cabin", cmd("journal"))

    def test_upgrade_home_to_warm_cabin_requires_hidden_materials(self):
        self.prepare_little_cabin()
        self.add_inventory({"stone": 3, "stick": 2})
        cmd("build campfire")
        before = parse_state(cmd("status"))

        failed = cmd("upgrade home to warm_cabin")
        failed_state = parse_state(failed)

        self.assertIn("材料不够", failed)
        self.assertEqual(failed_state["time"], before["time"])
        self.assertEqual(failed_state["home_level"], "little_cabin")

        self.add_inventory({"river_glass": 1, "old_tile": 1, "moss_thread": 1, "foxbell_dye_material": 1})
        upgraded = parse_state(cmd("upgrade home to warm_cabin"))

        self.assertEqual(upgraded["home_level"], "warm_cabin")
        self.assertGreaterEqual(upgraded["companion"]["warmth"], 7)
        self.assertIn("home_warm_cabin", cmd("debug companion"))

    def test_home_level_saved_loaded(self):
        self.prepare_little_cabin()
        cmd("save")

        new_game("other")
        loaded = parse_state(cmd("load"))

        self.assertEqual(loaded["home_level"], "little_cabin")
        self.assertIn("home_level: little_cabin", cmd("home"))

    def test_build_simple_bed_at_base(self):
        self.prepare_workshop_home()
        self.add_inventory({"plank": 2, "cloth": 1, "fiber": 2})

        built = parse_state(cmd("build simple_bed"))

        self.assertIn("simple_bed", built["builds_here"])
        self.assertGreaterEqual(built["home_comfort"], 1)
        self.assertGreaterEqual(built["home_security"], 1)

    def test_build_family_bed_requires_little_cabin(self):
        self.prepare_workshop_home()
        self.add_inventory({"plank": 4, "moss_thread": 1, "cloth": 2})
        before = parse_state(cmd("status"))

        failed = cmd("build family_bed")
        failed_state = parse_state(failed)

        self.assertIn("little_cabin", failed)
        self.assertEqual(failed_state["time"], before["time"])
        self.assertNotIn("family_bed", failed_state["builds_here"])

        self.add_inventory({"plank": 4, "weathered_wood": 1, "river_clay": 1})
        cmd("upgrade home to little_cabin")
        self.add_inventory({"plank": 4, "moss_thread": 1, "cloth": 2})
        built = parse_state(cmd("build family_bed"))

        self.assertIn("family_bed", built["builds_here"])
        self.assertIn("first_family_bed", cmd("debug companion"))

    def test_build_flower_pot_uses_foxbell(self):
        self.prepare_base()
        self.add_inventory({"river_clay": 1, "foxbell": 1})

        built = parse_state(cmd("build flower_pot"))
        decor = cmd("decor")

        self.assertIn("flower_pot", built["builds_here"])
        self.assertNotIn("foxbell", built["inventory"])
        self.assertIn("flower_pot: foxbell", decor)
        self.assertGreaterEqual(built["companion"]["mood"], 7)

    def test_build_glass_window_uses_river_glass(self):
        self.prepare_little_cabin()
        self.mutate_save(lambda saved: saved["builds"]["12,12"].append("window_table"))
        self.add_inventory({"river_glass": 1, "plank": 1})

        built = parse_state(cmd("build glass_window"))

        self.assertIn("glass_window", built["builds_here"])
        self.assertNotIn("river_glass", built["inventory"])
        self.assertIn("窗边桌终于有了真正的光", cmd("journal"))

    def test_build_tile_floor_uses_old_tile(self):
        self.prepare_base()
        self.add_inventory({"old_tile": 1, "stone": 2})

        built = parse_state(cmd("build tile_floor"))

        self.assertIn("tile_floor", built["builds_here"])
        self.assertNotIn("old_tile", built["inventory"])
        self.assertIn("tile_floor", cmd("decor"))

    def test_build_hearth_sets_warmth_protection(self):
        self.prepare_base()
        self.add_inventory({"stone": 6, "river_clay": 1, "charcoal": 1})

        built = parse_state(cmd("build hearth"))
        home = cmd("home")

        self.assertIn("hearth", built["builds_here"])
        self.assertIn("warmth protection: hearth", home)

    def test_home_command_shows_level_comfort_security(self):
        self.prepare_little_cabin()

        output = cmd("home")

        self.assertIn("home_level: little_cabin", output)
        self.assertIn("comfort score:", output)
        self.assertIn("security score:", output)
        self.assertIn("family readiness hint:", output)

    def test_decor_command_no_time_advance(self):
        self.prepare_base()
        self.add_inventory({"old_tile": 1, "stone": 2})
        cmd("build tile_floor")
        before = parse_state(cmd("status"))

        output = cmd("decor")
        after = parse_state(output)

        self.assertIn("decor:", output)
        self.assertIn("tile_floor", output)
        self.assertEqual(before["time"], after["time"])

    def test_warm_cabin_adds_relationship_milestone(self):
        self.prepare_little_cabin()
        self.add_inventory({"stone": 3, "stick": 2})
        cmd("build campfire")
        self.add_inventory({"river_glass": 1, "old_tile": 1, "moss_thread": 1})

        before = parse_state(cmd("relationship"))
        upgraded = parse_state(cmd("upgrade home to warm_cabin"))
        debug = cmd("debug companion")

        self.assertEqual(upgraded["home_level"], "warm_cabin")
        self.assertIn("home_warm_cabin", debug)
        self.assertGreaterEqual(upgraded["relationship"]["bond"], before["relationship"]["bond"] + 1)

    def test_same_seed_same_commands_same_home_upgrade_state(self):
        sequence = [
            "build simple_shelter",
            "build workbench",
            "build storage_box",
            "upgrade home to little_cabin",
            "build flower_pot",
            "build glass_window",
            "decor",
            "home",
        ]

        def run() -> dict:
            new_game("12071008", difficulty="normal", companion_name="Yaya")
            self.add_inventory(
                {
                    "wood": 4,
                    "fiber": 1,
                    "plank": 11,
                    "stick": 2,
                    "weathered_wood": 1,
                    "river_clay": 2,
                    "foxbell": 1,
                    "river_glass": 1,
                }
            )
            state = {}
            outputs = []
            for command in sequence:
                output = cmd(command)
                outputs.append(output)
                state = parse_state(output)
            return {"state": state, "decor": cmd("decor"), "home": cmd("home")}

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
