import importlib
import json
import unittest
from pathlib import Path

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V16AIPlayabilityReleaseTests(unittest.TestCase):
    def mutate_save(self, mutator) -> dict:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")
        return saved

    def test_blind_entry_exports_only_new_game_cmd(self):
        blind = importlib.import_module("fox_river_valley_blind")

        public = sorted(name for name in dir(blind) if not name.startswith("_"))

        self.assertEqual(public, ["cmd", "new_game"])
        self.assertIs(blind.new_game, new_game)
        self.assertIs(blind.cmd, cmd)

    def test_tool_schema_exists_and_mentions_coplay(self):
        schema = json.loads(Path("tool-schema.json").read_text(encoding="utf-8"))
        names = {tool["name"] for tool in schema["tools"]}
        cmd_tool = next(tool for tool in schema["tools"] if tool["name"] == "cmd")
        description = cmd_tool["description"]

        self.assertEqual(names, {"new_game", "cmd"})
        self.assertIn("cozy survival / family sandbox", description)
        self.assertIn("每回合默认只执行 1 条命令", description)
        self.assertIn("STATE", description)
        self.assertIn("不要 speedrun", description)
        self.assertIn("milestone", description)
        self.assertIn("kit arrival", description)
        self.assertIn("recap", description)
        self.assertIn("options", description)

    def test_release_checklist_exists(self):
        checklist = Path("RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

        self.assertIn("unittest discover -v", checklist)
        self.assertIn("compileall", checklist)
        self.assertIn("POSIX", checklist)
        self.assertIn("blind play smoke test", checklist)
        self.assertIn("co-play smoke test", checklist)
        self.assertIn("save/load smoke test", checklist)
        self.assertIn("no private archive", checklist)
        self.assertIn("no LLM", checklist)
        self.assertIn("no UI", checklist)

    def test_readme_has_human_ai_developer_sections(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("## Human Quick Start", readme)
        self.assertIn("## AI Blind Play", readme)
        self.assertIn("## Developer / QA Mode", readme)
        self.assertIn("fox_river_valley_blind", readme)
        self.assertIn("不读源码表作弊", readme)

    def test_long_arc_smoke_segments(self):
        smoke = importlib.import_module("scripts.long_arc_smoke")

        result = smoke.run_long_arc_smoke()

        self.assertTrue(result["ok"], result)
        self.assertIn("simple_shelter", result["segments"]["day_one_home"])
        self.assertIn("campfire", result["segments"]["day_one_home"])
        self.assertIn("garden_plot", result["segments"]["garden"])
        self.assertIn("foxbell", result["segments"]["garden"])
        self.assertIn("little_cabin", result["segments"]["home_upgrade"])
        self.assertIn("married_family", result["segments"]["commitment"])
        self.assertIn("arrived", result["segments"]["kit"])

    def test_name_input_validation(self):
        with self.assertRaises(ValueError):
            new_game("12071008", companion_name="A" * 41)

        output = new_game("12071008", companion_name="Ya\x00ya")
        state = parse_state(output)
        self.assertEqual(state["companion"]["name"], "Yaya")
        self.assertNotIn("\x00", output)

    def test_name_home_rejects_newline(self):
        new_game("12071008", companion_name="Yaya")
        self.mutate_save(
            lambda saved: (
                saved.update(
                    {
                        "pos": [12, 12],
                        "base_pos": [12, 12],
                        "shelter_pos": [12, 12],
                        "home_name": None,
                        "builds": {"12,12": ["simple_shelter"]},
                    }
                )
            )
        )
        before = parse_state(cmd("status"))

        output = cmd("name home Little\nFox Cabin")
        after = parse_state(output)

        self.assertIn("名字不能包含换行", output)
        self.assertIsNone(after["home_name"])
        self.assertEqual(after["time"], before["time"])

    def test_name_kit_rejects_empty(self):
        new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")
        self.mutate_save(
            lambda saved: saved.update(
                {
                    "family": {
                        "kit_status": "arrived",
                        "kit_count": 1,
                        "kit_days_waited": 2,
                        "kit_arrival_wait_days": 2,
                        "expected_species": "silicon_fox",
                        "kits": [
                            {
                                "id": "kit_1",
                                "species": "silicon_fox",
                                "display_name": "小硅狐崽",
                                "hidden_breed": "curly_brace_fox",
                                "name": None,
                                "hunger": 6,
                                "warmth": 6,
                                "sleep": 6,
                                "security": 6,
                                "curiosity": 5,
                                "mischief": 3,
                                "favorite_place": "hearth",
                                "trait": "curly_brace_tail",
                            }
                        ],
                    }
                }
            )
        )
        before = cmd("debug family")

        output = cmd("name kit    ")
        after = cmd("debug family")

        self.assertIn("名字不能为空", output)
        self.assertIn("name: unnamed", after)
        self.assertEqual(after, before)

    def test_failed_name_does_not_mutate(self):
        new_game("12071008", companion_name="Yaya")
        self.mutate_save(
            lambda saved: saved.update(
                {
                    "pos": [12, 12],
                    "base_pos": [12, 12],
                    "shelter_pos": [12, 12],
                    "home_name": "Little Fox Cabin",
                    "builds": {"12,12": ["simple_shelter"]},
                }
            )
        )
        before = parse_state(cmd("status"))

        output = cmd("name home " + "Cabin" * 9)
        after = parse_state(output)

        self.assertIn("名字太长", output)
        self.assertEqual(after["home_name"], "Little Fox Cabin")
        self.assertEqual(after["time"], before["time"])

    def test_data_registry_guide_exists(self):
        guide = Path("DATA_REGISTRY_GUIDE.md").read_text(encoding="utf-8")

        for topic in (
            "flower variety",
            "companion profile",
            "commitment token",
            "family species",
            "hidden material",
            "recipe",
            "exploration event",
        ):
            self.assertIn(topic, guide)
        self.assertIn("Silas/Yaya profile 是示例", guide)
        self.assertIn("foxbell / silicon_fox", guide)

    def test_default_profile_not_forced_to_silas_yaya(self):
        new_game("12071008", companion_name="Ari")

        debug = cmd("debug companion")

        self.assertIn("profile id: default", debug)
        self.assertIn("family_species: none", debug)
        self.assertNotIn("silicon_fox", debug)


if __name__ == "__main__":
    unittest.main()
