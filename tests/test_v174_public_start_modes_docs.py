import json
import unittest
from pathlib import Path


class V174PublicStartModesDocsTests(unittest.TestCase):
    def test_readme_ai_blind_play_uses_three_start_modes(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn('默认：new_game("seed") 是 solo', readme)
        self.assertIn('自定义家庭：new_game("seed", companion_name="Alex", companion_profile="default")', readme)
        self.assertIn('示例家庭：new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")', readme)
        self.assertIn("Silas/Yaya demo profile，不是默认路线", readme)

    def test_ai_player_guide_requires_observer_before_new_game(self):
        guide = Path("AI_PLAYER_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn("先启动实时观战页，再开始 new_game", guide)
        self.assertIn("不要直接替玩家选择 Yaya", guide)
        self.assertIn("先询问玩家要 solo、自定义家庭、还是 Silas/Yaya demo", guide)

    def test_tool_schema_mentions_observer_first_and_yaya_not_default(self):
        schema = json.loads(Path("tool-schema.json").read_text(encoding="utf-8"))
        encoded = json.dumps(schema, ensure_ascii=False).replace('\\"', '"')

        self.assertIn("Before new_game", encoded)
        self.assertIn("new_game(\"seed\") is solo", encoded)
        self.assertIn("Yaya is not the default companion", encoded)
        self.assertIn("Silas/Yaya demo profile", encoded)

    def test_blind_entry_docstring_warns_against_default_yaya(self):
        text = Path("fox_river_valley_blind.py").read_text(encoding="utf-8")

        self.assertIn("Default start is solo", text)
        self.assertIn("Do not choose Yaya unless", text)
        self.assertIn("start or confirm the observer", text)

    def test_play_session_template_starts_with_mode_question(self):
        template = Path("PLAY_SESSION_TEMPLATE.md").read_text(encoding="utf-8")

        self.assertIn("先确认观战页已经打开", template)
        self.assertIn("你想用哪种开局", template)
        self.assertIn("solo", template)
        self.assertIn("自定义家庭", template)
        self.assertIn("Silas/Yaya demo", template)


if __name__ == "__main__":
    unittest.main()
