from pathlib import Path
import unittest

from fox_river_valley import cmd, new_game
from tests.test_commands import parse_state


class V153AICoplayProtocolTests(unittest.TestCase):
    def test_recap_no_time_advance(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("recap")
        after = parse_state(output)

        self.assertIn("共同游玩 recap", output)
        self.assertIn("当前状态", output)
        self.assertIn("最近日志", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_options_no_time_advance(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")
        before = parse_state(cmd("status"))

        output = cmd("options")
        after = parse_state(output)

        self.assertIn("可选下一步", output)
        self.assertEqual(after["day"], before["day"])
        self.assertEqual(after["time"], before["time"])

    def test_options_returns_relevant_choices(self):
        new_game("12071008", difficulty="normal", companion_name="Yaya")

        output = cmd("options")

        self.assertIn("1. gather", output)
        self.assertIn("2. fish", output)
        self.assertIn("3. check companion", output)
        self.assertIn("补 shelter 材料", output)
        self.assertIn("准备食物", output)

    def test_readme_mentions_co_play_protocol(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("AI Co-play", readme)
        self.assertIn("CO_PLAY_PROTOCOL.md", readme)
        self.assertIn("每回合最多执行 1-2 条命令", readme)

    def test_protocol_warns_against_speedrun(self):
        protocol = Path("CO_PLAY_PROTOCOL.md").read_text(encoding="utf-8")
        template = Path("PLAY_SESSION_TEMPLATE.md").read_text(encoding="utf-8")

        self.assertIn("不要一次性 speedrun", protocol)
        self.assertIn("除非人类明确说“你自己玩”", protocol)
        self.assertIn("每回合最多执行 1-2 条命令", protocol)
        self.assertIn("当前理解", protocol)
        self.assertIn("对人类玩家的选择提问", protocol)
        self.assertIn("不许一次性通关", template)


if __name__ == "__main__":
    unittest.main()
