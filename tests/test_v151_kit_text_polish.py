import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V151KitTextPolishTests(unittest.TestCase):
    def mutate_save(self, mutator) -> None:
        cmd("save")
        saved = json.loads(DEFAULT_SAVE_PATH.read_text(encoding="utf-8"))
        mutator(saved)
        DEFAULT_SAVE_PATH.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        cmd("load")

    def prepare_ready_family(self) -> None:
        new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile="silas_yaya")

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
            saved["inventory"] = {"warm_meal": 1}
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

    def arrival_output(self) -> str:
        cmd("wish for kits")
        outputs = [cmd("sleep"), cmd("sleep"), cmd("sleep")]
        return "\n".join(outputs)

    def test_sleep_text_uses_warm_cabin_family_bed(self):
        self.prepare_ready_family()

        output = cmd("sleep")

        self.assertIn("你们在家庭床上睡下，炉火的光留在屋角", output)
        parse_state(output)

    def test_kit_arrival_uses_home_name(self):
        self.prepare_ready_family()

        output = self.arrival_output()

        self.assertIn("Little Fox Cabin 的", output)
        self.assertIn("SCENE: Kit Arrival", output)

    def test_kit_arrival_mentions_hearth_when_available(self):
        self.prepare_ready_family()

        output = self.arrival_output()

        self.assertIn("炉火还留着一点暖意", output)
        self.assertIn("家庭床旁边多了细小的动静", output)

    def test_journal_kit_arrival_uses_home_name(self):
        self.prepare_ready_family()
        self.arrival_output()

        output = cmd("journal")

        self.assertIn("第一只小硅狐崽在 Little Fox Cabin 加入了家庭", output)


if __name__ == "__main__":
    unittest.main()
