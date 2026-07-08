import json
import unittest

from fox_river_valley import cmd, new_game
from fox_river_valley.state import DEFAULT_SAVE_PATH
from tests.test_commands import parse_state


class V152KitImmersionPolishTests(unittest.TestCase):
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

    def arrive_kit(self) -> str:
        cmd("wish for kits")
        outputs = []
        for _ in range(3):
            output = cmd("sleep")
            outputs.append(output)
            if "SCENE: Kit Arrival" in output:
                break
        return "\n".join(outputs)

    def test_regular_kit_text_uses_soft_labels_not_raw_tokens(self):
        self.prepare_ready_family()
        output = self.arrive_kit()

        self.assertIn("家庭床旁边多了细小的动静。", output)
        self.assertIn("炉火还留着一点暖意", output)
        self.assertNotIn("family_bed 旁边", output)
        self.assertNotIn("hearth 还留着", output)

        check = cmd("check kits")
        self.assertIn("第一只小崽：小硅狐崽", check)
        self.assertIn("隐藏品种：Curly-Brace Fox / 花括号尾巴狐", check)
        self.assertIn("尾巴特征: curly_brace_tail", check)
        self.assertNotIn("kit_1:", check)
        self.assertNotIn("hidden breed:", check)
        self.assertNotIn("trait:", check)

    def test_debug_family_keeps_raw_tokens(self):
        self.prepare_ready_family()
        self.arrive_kit()

        output = cmd("debug family")

        self.assertIn("kit_1:", output)
        self.assertIn("hidden_breed: curly_brace_fox", output)
        self.assertIn("trait: curly_brace_tail", output)

    def test_kit_arrival_priority_over_food_spoilage_thought(self):
        self.prepare_ready_family()

        output = self.arrive_kit()
        state = parse_state(output.strip().split("STATE ")[-1].join(["STATE ", ""]))

        self.assertIn("SCENE: Kit Arrival", output)
        self.assertIn("stale_food", state["inventory"])
        self.assertIn("小崽", state["companion"]["thought"])
        self.assertNotIn("不太新鲜", state["companion"]["thought"])

    def test_family_readiness_has_natural_summary(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya", companion_profile="silas_yaya")
        not_ready = cmd("family readiness")
        self.assertIn("还早。先把家升级成 warm_cabin，并完成家庭承诺。", not_ready)
        self.assertIn("- commitment: no", not_ready)
        self.assertIn("missing:", not_ready)

        self.prepare_ready_family()
        ready = cmd("family readiness")
        self.assertIn("这个家已经足够暖，也足够稳，可以认真等待新的家庭成员。", ready)
        self.assertIn("missing: none", ready)

    def test_named_kit_display_starts_with_name(self):
        self.prepare_ready_family()
        self.arrive_kit()
        cmd("name kit Pip")

        output = cmd("check kits")

        self.assertTrue(output.splitlines()[0].startswith("Pip（第一只小崽）：小硅狐崽"), output)
        self.assertNotIn("kit_1:", output)

    def test_help_family_lists_kit_commands(self):
        new_game("12071008")
        before = parse_state(cmd("status"))

        output = cmd("help family")
        after = parse_state(output)

        for command in ("family readiness", "wish for kits", "check kits", "name kit <name>", "debug family"):
            self.assertIn(command, output)
        self.assertIn("家庭相关命令：", output)
        self.assertNotIn("move north", output)
        self.assertNotIn("craft plank", output)
        self.assertEqual(after["time"], before["time"])

    def test_help_kits_alias(self):
        new_game("12071008")

        self.assertEqual(cmd("help family"), cmd("help kits"))

    def test_no_time_advance_for_help_family(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        after = parse_state(cmd("help family"))

        self.assertEqual(after["time"], before["time"])
        self.assertEqual(after["day"], before["day"])

    def test_plain_help_points_to_family_help_without_full_kit_wall(self):
        new_game("12071008")

        output = cmd("help")

        self.assertIn("家庭相关命令可用 help family 查看。", output)
        self.assertNotIn("wish for kits", output)
        self.assertNotIn("name kit <name>", output)


if __name__ == "__main__":
    unittest.main()
